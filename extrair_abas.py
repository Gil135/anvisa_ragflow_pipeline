import time
import logging
import json
import datetime
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from browser_utils import criar_driver

driver = criar_driver()


# ===== CONFIGURAÇÃO DE LOGGING =====

logging.basicConfig(
    level=logging.INFO,
    filename='logs/scraping.log',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ===== SALVAR ABAS EM JSON =====

def salvar_abas_json(abas, url_origem, nome_arquivo='data/json/abas.json'):
    """
    Salva a lista de abas em um arquivo JSON bem formatado.
    
    Args:
        abas: Lista de dicionários com dados das abas
        url_origem: URL de origem dos dados
        nome_arquivo: Nome do arquivo JSON (padrão: abas.json)
    """
    try:
        # Gerar timestamp
        data_extracao = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Estrutura completa do JSON
        dados_completos = {
            "data_extracao": data_extracao,
            "url_origem": url_origem,
            "total_abas": len(abas),
            "abas": abas
        }
        
        # Salvar em JSON com indentação e encoding UTF-8
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados_completos, f, indent=2, ensure_ascii=False)
        
        # Exibir confirmação
        caminho_completo = os.path.abspath(nome_arquivo)
        tamanho_arquivo = os.path.getsize(nome_arquivo)
        
        print("\n✅ JSON SALVO COM SUCESSO!")
        print("=" * 100)
        print(f"📄 Arquivo: {caminho_completo}")
        print(f"📊 Tamanho: {tamanho_arquivo} bytes")
        print(f"📋 Total de abas: {len(abas)}")
        print("=" * 100 + "\n")
        
        # Log
        logging.info(f"Abas salvas em JSON: {caminho_completo}")
        
    except Exception as e:
        print(f"\n❌ Erro ao salvar JSON: {e}")
        logging.error(f"Erro ao salvar abas em JSON: {e}")

# ===== FUNÇÃO EXTRAIR LISTA ABAS =====

def extrair_lista_abas(driver, url):
    """Extrai href e título da lista de abas"""
    try:
        # Acessar a página
        print(f"\n📍 Acessando: {url}\n")
        driver.get(url)
        time.sleep(2)  # Delay de estabilidade
        
        # Aguardar carregamento da lista
        print("⏳ Aguardando carregamento da lista...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "ul.nav.nav-tabs.nav-justified")
            )
        )
        print("✓ Lista carregada!\n")
        time.sleep(1)  # Delay adicional
        
        # Encontrar a <ul> e todos os <li>
        ul = driver.find_element(By.CSS_SELECTOR, "ul.nav.nav-tabs.nav-justified")
        lis = ul.find_elements(By.TAG_NAME, "li")
        
        print(f"📊 Total de itens encontrados: {len(lis)}\n")
        print("=" * 100)
        
        # Armazenar dados
        abas = []
        
        # Processar cada <li>
        for i, li in enumerate(lis, start=1):
            try:
                # Extrair link <a>
                a_tag = li.find_element(By.TAG_NAME, "a")
                href = a_tag.get_attribute("href")
                
                # Extrair título da tag <b>
                b_tag = a_tag.find_element(By.TAG_NAME, "b")
                titulo = b_tag.text.strip()
                
                # Armazenar
                abas.append({
                    "numero": i,
                    "titulo": titulo,
                    "href": href
                })
                
                # Exibir de forma clara
                print(f"{i}. {titulo}")
                print(f"   └─ {href}\n")
                
            except NoSuchElementException as e:
                print(f"❌ Erro ao extrair item {i}: {e}\n")
        
        print("=" * 100)
        print(f"✓ Extração concluída! Total: {len(abas)} itens\n")
        
        return abas
        
    except TimeoutException:
        print("❌ Erro: Tempo limite excedido ao aguardar a lista.")
        logging.error("Timeout ao aguardar carregamento da lista.")
        return []
    except NoSuchElementException:
        print("❌ Erro: Elemento não encontrado.")
        logging.error("Elemento da lista não encontrado.")
        return []
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        logging.error(f"Erro ao extrair lista de abas: {e}")
        return []

# ===== FUNÇÃO PRINCIPAL =====

def executar_scraping():
    """Função principal que coordena tudo"""

    try:
        # URL da página com a lista
        url = "https://anvisalegis.datalegis.net/action/ActionDatalegis.php?acao=recuperarTematicasCollapse&cod_modulo=310&cod_menu=9431&letra=AGROT%D3XICOS&co_tematica=24954850"
        
        # Extrair dados
        abas = extrair_lista_abas(driver, url)
        
        # Exibir resumo
        if abas:
            print("\n📋 RESUMO DOS DADOS EXTRAÍDOS:")
            print("-" * 100)
            for aba in abas:
                print(f"  {aba['numero']}. {aba['titulo']}")
            print("-" * 100)
            
            # NOVO: Salvar em JSON
            salvar_abas_json(abas, url, nome_arquivo='data/json/abas.json')
        else:
            print("⚠️  Nenhum dado foi extraído.")
        
        # Firefox permanece aberto para verificação
        print("\n✓ Firefox aberto. Feche manualmente quando terminar.")
        
    except Exception as e:
        print(f"❌ Erro durante execução: {e}")
        logging.error(f"Erro durante execução do scraping: {e}")
    
    finally:
        # Comentar a próxima linha se quiser manter Firefox aberto
        driver.quit()
        pass

# ===== EXECUTAR =====

if __name__ == "__main__":
    executar_scraping()