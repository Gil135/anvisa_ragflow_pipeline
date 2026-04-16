"""
==========================
Script para fazer download de PDFs da ANVISA.
Captura nova aba aberta ao clicar no botão PDF.
"""

import json
import logging
import os
import time
import datetime
import random
import re
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from browser_utils import criar_driver
driver = criar_driver()

# ===== CONFIGURAR LOGGING =====
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/download_pdfs_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== CONFIGURAÇÕES =====
PASTA_DESTINO = 'data/pdf'
ARQUIVO_PROGRESSO = 'data/json/progresso_downloads.json'

# ===== FUNÇÕES AUXILIARES =====

def limpar_nome_arquivo(titulo):
    """Remove caracteres inválidos do título"""
    titulo = titulo.replace('\n', ' ').strip()
    titulo = re.sub(r'[<>:"/\|?*]', '', titulo)
    titulo = re.sub(r'\s+', ' ', titulo)
    titulo = titulo[:180]
    return titulo.strip()

def carregar_progresso():
    """Carrega progresso anterior"""
    if os.path.exists(ARQUIVO_PROGRESSO):
        try:
            with open(ARQUIVO_PROGRESSO, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"ultimo_numero_sequencial": 0, "processados": []}

def salvar_progresso(progresso):
    """Salva progresso atual"""
    os.makedirs(os.path.dirname(ARQUIVO_PROGRESSO), exist_ok=True)
    with open(ARQUIVO_PROGRESSO, 'w', encoding='utf-8') as f:
        json.dump(progresso, f, indent=2, ensure_ascii=False)

def capturar_url_pdf_nova_aba(driver):
    """
    Captura a URL do PDF da nova aba aberta.
    Retorna a URL e fecha a aba.
    """
    try:
        # Aguardar nova aba ser aberta
        time.sleep(2)
        
        # Obter todas as abas
        abas = driver.window_handles
        logger.info(f"Total de abas: {len(abas)}")
        
        if len(abas) < 2:
            logger.warning("⚠️ Nenhuma nova aba foi aberta")
            return None
        
        # Mudar para a última aba (a nova)
        aba_nova = abas[-1]
        driver.switch_to.window(aba_nova)
        time.sleep(2)
        
        # Capturar URL da aba
        url_pdf = driver.current_url
        logger.info(f"✓ URL capturada da nova aba: {url_pdf[:100]}...")
        
        # Fechar a aba
        driver.close()
        
        # Voltar para a aba original
        driver.switch_to.window(abas[0])
        time.sleep(1)
        
        return url_pdf
        
    except Exception as e:
        logger.error(f"❌ Erro ao capturar URL da nova aba: {e}")
        try:
            # Tentar voltar para aba original
            abas = driver.window_handles
            if abas:
                driver.switch_to.window(abas[0])
        except:
            pass
        return None

def baixar_pdf(url_pdf, caminho_destino, timeout=30):
    """Faz download do PDF usando requests"""
    try:
        logger.info(f"Iniciando download: {url_pdf[:80]}...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url_pdf, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(caminho_destino), exist_ok=True)
        
        tamanho_total = 0
        with open(caminho_destino, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    tamanho_total += len(chunk)
        
        tamanho_mb = tamanho_total / (1024 * 1024)
        logger.info(f"✅ PDF salvo: {caminho_destino} ({tamanho_mb:.2f} MB)")
        
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erro ao baixar PDF: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro ao salvar PDF: {e}")
        return False

def encontrar_e_clicar_botao_pdf(driver, url_pagina):
    """Encontra e clica no botão PDF"""
    try:
        logger.info(f"Acessando: {url_pagina[:80]}...")
        driver.get(url_pagina)
        time.sleep(2)
        
        # Procurar botão PDF
        try:
            botao_pdf = driver.find_element(By.XPATH, "//a[contains(@onclick, 'pdf()')]")
            logger.info("✓ Botão PDF encontrado, clicando...")
            botao_pdf.click()
            return True
        except NoSuchElementException:
            logger.warning("⚠️ Botão PDF não encontrado")
            return False
        
    except TimeoutException:
        logger.error(f"❌ Timeout ao carregar página")
        return False
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return False

def carregar_categorias_json(nome_arquivo='data/json/categorias.json'):# para teste trocar para atos_categorias.json
    """Carrega categorias do JSON"""
    try:
        if not os.path.exists(nome_arquivo):
            logger.error(f"Arquivo '{nome_arquivo}' não encontrado.")
            return None
        
        logger.info(f"Carregando '{nome_arquivo}'...")
        with open(nome_arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        total_resenhas = sum(len(cat.get('resenhas', [])) for cat in dados.get('categorias', []))
        logger.info(f"✓ {len(dados.get('categorias', []))} categorias, {total_resenhas} resenhas\n")
        
        return dados
        
    except Exception as e:
        logger.error(f"Erro ao carregar: {e}")
        return None

def processar_categorias(driver, dados_categorias):
    """Processa todas as categorias e resenhas"""
    
    progresso = carregar_progresso()
    processados = set(progresso.get('processados', []))
    numero_sequencial = progresso.get('ultimo_numero_sequencial', 0)
    
    total_resenhas = sum(len(cat.get('resenhas', [])) for cat in dados_categorias.get('categorias', []))
    
    resultado = {
        "data_extracao": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "total_categorias": len(dados_categorias.get('categorias', [])),
        "total_resenhas": total_resenhas,
        "total_processados": 0,
        "total_sucesso": 0,
        "total_erro": 0,
        "categorias": []
    }
    
    categorias = dados_categorias.get('categorias', [])
    
    if processados:
        logger.info(f"⏸️  Retomando de {len(processados)} resenhas já processadas\n")
    
    logger.info(f"Iniciando processamento de {total_resenhas} resenhas\n")
    print("=" * 120)
    
    for cat_idx, categoria in enumerate(categorias, 1):
        cat_resultado = {
            "numero": cat_idx,
            "titulo": categoria.get('titulo', ''),
            "total_resenhas": len(categoria.get('resenhas', [])),
            "resenhas_sucesso": 0,
            "resenhas_erro": 0,
            "downloads": []
        }
        
        resenhas = categoria.get('resenhas', [])
        
        if not resenhas:
            resultado["categorias"].append(cat_resultado)
            continue
        
        print(f"\n📁 [{cat_idx}/{len(categorias)}] {cat_resultado['titulo']} ({len(resenhas)} resenhas)")
        print("─" * 120)
        
        for res_idx, resenha in enumerate(resenhas, 1):
            numero_sequencial += 1
            
            # Verificar se já foi processado
            id_resenha = f"{cat_idx}_{res_idx}"
            if id_resenha in processados:
                logger.info(f"[{numero_sequencial}] Já processado, pulando...")
                continue
            
            titulo = resenha.get('titulo', f'documento_{numero_sequencial}')
            href = resenha.get('href', '')
            
            titulo_curto = titulo[:60] + "..." if len(titulo) > 60 else titulo
            print(f"  [{numero_sequencial:5d}/{total_resenhas}] {titulo_curto}", end=" ", flush=True)
            
            try:
                if not href:
                    logger.warning(f"[{numero_sequencial}] URL vazia")
                    print("❌ (URL vazia)")
                    cat_resultado["resenhas_erro"] += 1
                    resultado["total_erro"] += 1
                    resultado["total_processados"] += 1
                    continue
                
                # Clicar no botão PDF
                if not encontrar_e_clicar_botao_pdf(driver, href):
                    print("❌ (botão não encontrado)")
                    cat_resultado["resenhas_erro"] += 1
                    resultado["total_erro"] += 1
                    resultado["total_processados"] += 1
                    time.sleep(random.uniform(1, 2))
                    continue
                
                # Capturar URL da nova aba
                url_pdf = capturar_url_pdf_nova_aba(driver)
                
                if not url_pdf:
                    logger.error(f"[{numero_sequencial}] URL do PDF não capturada")
                    print("❌ (URL não capturada)")
                    cat_resultado["resenhas_erro"] += 1
                    resultado["total_erro"] += 1
                    resultado["total_processados"] += 1
                    time.sleep(random.uniform(1, 2))
                    continue
                
                # Fazer download do PDF
                titulo_limpo = limpar_nome_arquivo(titulo)
                caminho_pdf = f"{PASTA_DESTINO}/{numero_sequencial:05d}_{titulo_limpo}.pdf"
                
                if baixar_pdf(url_pdf, caminho_pdf):
                    print("✅")
                    cat_resultado["downloads"].append({
                        "numero_sequencial": numero_sequencial,
                        "numero_resenha": res_idx,
                        "titulo": titulo[:100],
                        "status": "sucesso",
                        "caminho": caminho_pdf,
                        "url_pdf": url_pdf[:100]
                    })
                    cat_resultado["resenhas_sucesso"] += 1
                    resultado["total_sucesso"] += 1
                    processados.add(id_resenha)
                else:
                    print("❌ (erro download)")
                    cat_resultado["downloads"].append({
                        "numero_sequencial": numero_sequencial,
                        "numero_resenha": res_idx,
                        "titulo": titulo[:100],
                        "status": "erro_download",
                        "caminho": ""
                    })
                    cat_resultado["resenhas_erro"] += 1
                    resultado["total_erro"] += 1
                
                resultado["total_processados"] += 1
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                logger.error(f"[{numero_sequencial}] Erro: {e}")
                print(f"❌ (erro: {str(e)[:30]})")
                cat_resultado["resenhas_erro"] += 1
                resultado["total_erro"] += 1
                resultado["total_processados"] += 1
                continue
        
        resultado["categorias"].append(cat_resultado)
        print(f"  ✓ {cat_resultado['resenhas_sucesso']}/{len(resenhas)} processados com sucesso")
        
        # Salvar progresso
        progresso["ultimo_numero_sequencial"] = numero_sequencial
        progresso["processados"] = list(processados)
        salvar_progresso(progresso)
        
        if numero_sequencial % 50 == 0:
            salvar_resultado_json(resultado, 'data/json/resultado_downloads_parcial.json')
            logger.info(f"💾 Salvamento parcial: {numero_sequencial} resenhas processadas")
    
    print("\n" + "=" * 120)
    logger.info(f"\n✓ Processamento concluído!")
    logger.info(f"  Total processados: {resultado['total_processados']}")
    logger.info(f"  Sucesso: {resultado['total_sucesso']}")
    logger.info(f"  Erro: {resultado['total_erro']}\n")
    
    return resultado

def salvar_resultado_json(dados, nome_arquivo='data/json/resultado_downloads.json'):
    """Salva resultado do processamento em JSON"""
    try:
        os.makedirs(os.path.dirname(nome_arquivo), exist_ok=True)
        
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        
        caminho = os.path.abspath(nome_arquivo)
        logger.info(f"✅ Resultado salvo: {caminho}")
        
    except Exception as e:
        logger.error(f"Erro ao salvar resultado: {e}")

def executar_download_pdfs():
    """Função principal"""
    
    logger.info("=" * 120)
    logger.info("🚀 DOWNLOAD DE PDFs ANVISA - VERSÃO 4 (CAPTURA DE NOVA ABA)")
    logger.info("=" * 120)
    

    try:
        dados_categorias = carregar_categorias_json('data/json/categorias.json') #provisorio para teste 'data/json/atos_categorias.json'
        
        if not dados_categorias:
            logger.error("Não foi possível carregar o arquivo de categorias.")
            return
        
        resultado = processar_categorias(driver, dados_categorias)
        
        salvar_resultado_json(resultado, 'data/json/resultado_downloads.json')
        
        logger.info("✓ Processo finalizado. Firefox pode ser fechado.")
        
    except KeyboardInterrupt:
        logger.info("⏸️  Processo pausado pelo usuário. Você pode retomar depois.")
    except Exception as e:
        logger.error(f"Erro: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    executar_download_pdfs()