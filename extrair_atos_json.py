"""
atos.py
=======
Script FINAL para extrair conteúdo completo de atos da ANVISA.
Baseado no HTML real com div class="ato"
"""

import json
import logging
import os
import time
import datetime
import random
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# ✅ IMPORTAR DO MÓDULO COMPARTILHADO
from browser_utils import criar_driver
driver = criar_driver()

# ===== CONFIGURAR LOGGING =====
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/atos_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== FUNÇÕES AUXILIARES =====

def extrair_tipo_ato(href):
    """Extrai tipo do ato do href"""
    href_lower = href.lower()
    if 'tipo=rdc' in href_lower:
        return 'RDC'
    elif 'tipo=inm' in href_lower:
        return 'INM'
    elif 'portaria' in href_lower:
        return 'PORTARIA'
    else:
        return 'OUTRO'

def extrair_numero_ato(href):
    """Extrai número do ato do href"""
    try:
        if 'numeroAto=' in href:
            inicio = href.find('numeroAto=') + 10
            numero = href[inicio:inicio+8].split('&')[0]
            return numero.lstrip('0') or '0'
    except:
        pass
    return 'N/A'

def extrair_ano_ato(href):
    """Extrai ano do ato do href"""
    try:
        if 'valorAno=' in href:
            inicio = href.find('valorAno=') + 9
            ano = href[inicio:inicio+4]
            return ano
    except:
        pass
    return 'N/A'

# ===== FUNÇÃO PRINCIPAL: EXTRAIR CONTEÚDO (VERSÃO FINAL) =====

def extrair_conteudo_completo_ato(driver, href):
    """
   Extrai conteúdo de div.ato APENAS.
  
    """
    
    try:
        logger.info(f"Acessando: {href}")
        driver.get(href)
        time.sleep(1)
        
        # Aguardar div.ato
        logger.info("Aguardando carregamento de div.ato...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='ato']"))
        )
        time.sleep(1)
        
        # ✅ EXTRAIR APENAS div.ato (não body!)
        try:
            elemento_ato = driver.find_element(By.XPATH, "//div[@class='ato']")
            conteudo_texto = elemento_ato.text.strip()
            seletor_usado = "//div[@class='ato']"
            logger.info(f"✓ Conteúdo extraído de div.ato - {len(conteudo_texto)} caracteres")
            
        except NoSuchElementException:
            logger.error("❌ div.ato não encontrado!")
            return {
                "tipo_ato": extrair_tipo_ato(href),
                "numero_ato": extrair_numero_ato(href),
                "ano_ato": extrair_ano_ato(href),
                "tipo_conteudo": "erro",
                "tamanho_caracteres": 0,
                "status": "sem_conteudo",
                "conteudo_texto": "",
                "seletor_usado": "nenhum"
            }
        
        # ✅ Limpar conteúdo (remover quebras de linha extras)
        conteudo_texto = re.sub(r'\n+', '\n', conteudo_texto)
        
        tipo_ato = extrair_tipo_ato(href)
        numero_ato = extrair_numero_ato(href)
        ano_ato = extrair_ano_ato(href)
        tamanho = len(conteudo_texto)
        
        logger.info(f"✓ {tipo_ato} {numero_ato}/{ano_ato} - {tamanho} caracteres")
        
        return {
            "tipo_ato": tipo_ato,
            "numero_ato": numero_ato,
            "ano_ato": ano_ato,
            "tipo_conteudo": "ato_completo",
            "tamanho_caracteres": tamanho,
            "status": "sucesso",
            "conteudo_texto": conteudo_texto,
            "seletor_usado": seletor_usado
        }
        
    except TimeoutException:
        logger.error(f"❌ Timeout ao carregar {href}")
        return {
            "tipo_ato": extrair_tipo_ato(href),
            "numero_ato": extrair_numero_ato(href),
            "ano_ato": extrair_ano_ato(href),
            "tipo_conteudo": "erro",
            "tamanho_caracteres": 0,
            "status": "timeout",
            "conteudo_texto": "",
            "seletor_usado": "nenhum"
        }
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return {
            "tipo_ato": extrair_tipo_ato(href),
            "numero_ato": extrair_numero_ato(href),
            "ano_ato": extrair_ano_ato(href),
            "tipo_conteudo": "erro",
            "tamanho_caracteres": 0,
            "status": f"erro: {str(e)[:50]}",
            "conteudo_texto": "",
            "seletor_usado": "nenhum"
        }

# ===== CARREGAR CATEGORIAS =====

def carregar_categorias_json(nome_arquivo='data/json/categorias.json'):
    """Carrega categorias do JSON"""
    try:
        if not os.path.exists(nome_arquivo):
            logger.error(f"Arquivo '{nome_arquivo}' não encontrado.")
            return None
        
        logger.info(f"Carregando '{nome_arquivo}'...")
        with open(nome_arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        total_atos = sum(len(cat.get('resenhas', [])) for cat in dados.get('categorias', []))
        logger.info(f"✓ {len(dados.get('categorias', []))} categorias, {total_atos} atos")
        
        return dados
        
    except Exception as e:
        logger.error(f"Erro ao carregar: {e}")
        return None

# ===== PROCESSAR TODOS OS ATOS =====

def processar_todos_atos(driver, dados_categorias):
    """Processa TODOS os atos"""
    
    total_atos = sum(len(cat.get('resenhas', [])) for cat in dados_categorias.get('categorias', []))
    
    dados_finais = {
        "data_extracao": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "total_atos": total_atos,
        "total_atos_processados": 0,
        "total_sucesso": 0,
        "total_erro": 0,
        "categorias": []
    }
    
    numero_sequencial = 0
    categorias = dados_categorias.get('categorias', [])
    
    logger.info(f"Iniciando processamento de {total_atos} atos\n")
    print("=" * 120)
    
    for cat_idx, categoria in enumerate(categorias, 1):
        cat_dados = {
            "numero": cat_idx,
            "titulo": categoria.get('titulo', ''),
            "total_atos_categoria": len(categoria.get('resenhas', [])),
            "atos_processados": 0,
            "atos": []
        }
        
        resenhas = categoria.get('resenhas', [])
        
        if not resenhas:
            logger.info(f"Categoria {cat_idx}: {cat_dados['titulo']} - Sem atos")
            dados_finais["categorias"].append(cat_dados)
            continue
        
        print(f"\n🔗 [{cat_idx}/{len(categorias)}] {cat_dados['titulo']} ({len(resenhas)} atos)")
        
        for ato_idx, ato in enumerate(resenhas, 1):
            numero_sequencial += 1
            
            titulo_curto = ato.get('titulo', '')[:50] + "..."
            print(f"   [{numero_sequencial:4d}/{total_atos}] {titulo_curto}")
            
            try:
                href = ato.get('href', '')
                if not href:
                    continue
                
                # ✅ Extrair conteúdo COM A FUNÇÃO FINAL
                conteudo = extrair_conteudo_completo_ato(driver, href)
                
                ato_dados = {
                    "numero_sequencial": numero_sequencial,
                    "numero_ato_categoria": ato_idx,
                    "tipo_ato": conteudo['tipo_ato'],
                    "numero_ato": conteudo['numero_ato'],
                    "ano_ato": conteudo['ano_ato'],
                    "titulo": ato.get('titulo', '')[:100],
                    "tipo_conteudo": conteudo['tipo_conteudo'],
                    "tamanho_caracteres": conteudo['tamanho_caracteres'],
                    "status": conteudo['status'],
                    "conteudo_texto": conteudo['conteudo_texto']
                }
                
                cat_dados["atos"].append(ato_dados)
                cat_dados["atos_processados"] += 1
                dados_finais["total_atos_processados"] += 1
                
                if conteudo['status'] == 'sucesso':
                    dados_finais["total_sucesso"] += 1
                else:
                    dados_finais["total_erro"] += 1
                
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                logger.error(f"Erro ao processar ato {ato_idx}: {e}")
                continue
        
        dados_finais["categorias"].append(cat_dados)
        print(f"   ✓ {cat_dados['atos_processados']}/{len(resenhas)} processados")
        
        # Salvar parcialmente
        if numero_sequencial % 200 == 0:
            salvar_atos_json(dados_finais, 'data/json/atos_completos_parcial.json')
            logger.info(f"💾 Salvamento parcial: {numero_sequencial} atos")
    
    print("\n" + "=" * 120)
    logger.info(f"\n✓ Processamento concluído!")
    logger.info(f"  Processados: {dados_finais['total_atos_processados']}")
    logger.info(f"  Sucesso: {dados_finais['total_sucesso']}")
    logger.info(f"  Erro: {dados_finais['total_erro']}\n")
    
    return dados_finais

# ===== SALVAR EM JSON =====

def salvar_atos_json(dados, nome_arquivo='data/json/atos_completos.json'):
    """Salva dados em JSON"""
    try:
        os.makedirs(os.path.dirname(nome_arquivo), exist_ok=True)
        
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        
        caminho = os.path.abspath(nome_arquivo)
        tamanho = os.path.getsize(nome_arquivo)
        
        logger.info(f"✅ Arquivo salvo: {caminho} ({tamanho / (1024*1024):.2f} MB)")
        
    except Exception as e:
        logger.error(f"Erro ao salvar: {e}")

# ===== FUNÇÃO PRINCIPAL =====

def executar_scraping ():
    """Função principal"""
    
    logger.info("=" * 120)
    logger.info("🚀 EXTRATOR DE ATOS ANVISA - VERSÃO FINAL")
    logger.info("=" * 120)
    
 
    try:
        dados_categorias = carregar_categorias_json('data/json/categorias.json')
        
        if not dados_categorias:
            return
        
        dados_processados = processar_todos_atos(driver, dados_categorias)
        
        salvar_atos_json(dados_processados, 'data/atos_completos.json')
        
        logger.info("✓ Processo finalizado. Firefox pode ser fechado.")
        
    except Exception as e:
        logger.error(f"Erro: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    executar_scraping ()