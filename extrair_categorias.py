import time
import json
import os
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from browser_utils import criar_driver




def detectar_total_e_paginas_v2(driver):
    """
  
    - Contar páginas no select
    - Se há paginação: total = páginas × 50 (assumindo 50 por página padrão)
    - Se NÃO há paginação: total = itens visíveis
    
    IMPORTANTE: A última página pode ter menos itens, mas não conseguimos
    detectar sem clicar nela. Logo, usamos 50 como padrão.
    """
    
    resultado = {
        "total_itens": 0,
        "num_paginas": 0,
        "tem_paginacao": False,
        "metodo_calculo": ""
    }
    
    try:
        print("   🔍 Analisando estrutura de paginação...")
        
        # Contar itens visíveis na página 1
        resenha_section = driver.find_element(By.ID, "resenha")
        links = resenha_section.find_elements(By.TAG_NAME, "a")
        itens_pagina1 = len(links)
        
        print(f"   📊 Itens visíveis na página 1: {itens_pagina1}")
        
        # Verificar se há paginação
        try:
            page_select = Select(driver.find_element(By.ID, "fieldPage"))
            num_pages = len(page_select.options)
            
            print(f"   📄 Páginas encontradas: {num_pages}")
            
            if num_pages > 1:
                # ✅ COM PAGINAÇÃO: 
                # Total APROXIMADO = (num_pages - 1) × 50 + itens_página1
                # Porque a última página pode ter menos de 50 itens
                resultado["tem_paginacao"] = True
                resultado["num_paginas"] = num_pages
                resultado["metodo_calculo"] = "paginado (50 + 50 + ... + X)"
                
                # Se primeira página tem 50, assume padrão
                if itens_pagina1 == 50:
                    # Total = (páginas - 1) × 50 + última_página (desconhecida)
                    # Assumir: última página tem entre 1 e 50 itens
                    # Melhor estimativa: (páginas - 1) × 50 + 50 = páginas × 50
                    # MAS pode ser menos. Então vamos processar página a página
                    
                    total = num_pages * 50  # Estimativa conservadora
                    resultado["total_itens"] = total
                    
                    print(f"   ✓ Total estimado: {total} itens")
                    print(f"   ⚠️  Nota: Última página pode ter menos de 50 itens")
                else:
                    # Primeira página tem menos de 50
                    total = itens_pagina1 * num_pages
                    resultado["total_itens"] = total
                    print(f"   ✓ Total estimado: {total} itens")
            else:
                # SEM PAGINAÇÃO
                resultado["tem_paginacao"] = False
                resultado["num_paginas"] = 1
                resultado["total_itens"] = itens_pagina1
                resultado["metodo_calculo"] = "sem paginação"
                
                print(f"   ✓ Sem paginação, total: {itens_pagina1} itens")
                
        except NoSuchElementException:
            resultado["tem_paginacao"] = False
            resultado["num_paginas"] = 1
            resultado["total_itens"] = itens_pagina1
            resultado["metodo_calculo"] = "sem paginação"
            
            print(f"   ✓ Sem paginação, total: {itens_pagina1} itens")
        
        return resultado
        
    except Exception as e:
        print(f"   ❌ Erro ao detectar: {e}")
        return resultado

# ===== FUNÇÃO: EXTRAIR RESENHAS PÁGINA POR PÁGINA =====

def extrair_resenhas_pagina_atual(driver):
    """
    Extrai resenhas da página atual.
    Retorna lista com dados extraídos.
    """
    resenhas = []
    
    try:
        resenha_section = driver.find_element(By.ID, "resenha")
        links = resenha_section.find_elements(By.TAG_NAME, "a")
        
        for link in links:
            try:
                titulo = link.text.strip()
                href = link.get_attribute("href")
                
                if titulo and href and len(titulo) > 5:
                    resenhas.append({
                        "numero": len(resenhas) + 1,
                        "titulo": titulo,
                        "href": href
                    })
            except Exception:
                continue
        
    except Exception as e:
        print(f"      ❌ Erro ao extrair: {e}")
    
    return resenhas

# ===== FUNÇÃO: EXTRAIR TODAS AS RESENHAS =====

def extrair_resenhas_otimizado_v2(driver):
    """
    Versão 2 corrigida: Processa página por página e conta real.
    NÃO tenta detectar última página antecipadamente.
    """
    resenhas = []
    
    try:
        print("   ⏳ Aguardando carregamento da seção resenha...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "resenha"))
        )
        time.sleep(1)
        
        # Detectar estrutura
        info = detectar_total_e_paginas_v2(driver)
        
        num_paginas = info["num_paginas"]
        tem_paginacao = info["tem_paginacao"]
        
        if not tem_paginacao:
            # SEM PAGINAÇÃO
            print(f"\n   📥 Extraindo itens...")
            resenhas = extrair_resenhas_pagina_atual(driver)
            
        else:
            # COM PAGINAÇÃO: processar página a página
            print(f"\n   📥 Extraindo de {num_paginas} páginas...\n")
            
            for page_num in range(1, num_paginas + 1):
                try:
                    print(f"   🔄 Página {page_num}/{num_paginas}...")
                    
                    # Selecionar página
                    page_select = Select(driver.find_element(By.ID, "fieldPage"))
                    page_select.select_by_value(str(page_num))
                    time.sleep(1)
                    
                    # Aguardar
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "section#resenha a"))
                    )
                    time.sleep(1)
                    
                    # Extrair
                    page_resenhas = extrair_resenhas_pagina_atual(driver)
                    resenhas.extend(page_resenhas)
                    
                    print(f"      ✓ {len(page_resenhas)} itens (Total: {len(resenhas)})")
                    
                except Exception as e:
                    print(f"      ❌ Erro: {str(e)[:50]}")
                    continue
        
        # Remover duplicatas
        hrefs_unicos = set()
        resenhas_unicas = []
        
        for res in resenhas:
            if res['href'] not in hrefs_unicos:
                hrefs_unicos.add(res['href'])
                resenhas_unicas.append(res)
        
        # Renumerar
        for i, res in enumerate(resenhas_unicas, 1):
            res['numero'] = i
        
        print(f"\n   ✓ Total final: {len(resenhas_unicas)} resenhas\n")
        
        return resenhas_unicas
        
    except Exception as e:
        print(f"   ❌ Erro geral: {e}")
    
    return resenhas

# ===== SUAS OUTRAS FUNÇÕES =====

def carregar_categorias_json(nome_arquivo='data/json/atos_categorias.json'):
    try:
        if not os.path.exists(nome_arquivo):
            print(f"❌ Arquivo '{nome_arquivo}' não encontrado.")
            return None
        
        print(f"\n📂 Carregando '{nome_arquivo}'...\n")
        with open(nome_arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        print(f"✓ Arquivo carregado!")
        print(f"  📋 Total de categorias: {len(dados.get('categorias', []))}\n")
        
        return dados
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return None

def extrair_conteudo_categorias(driver, abas_json):
    dados_categorias = []
    total_abas = len(abas_json)
    
    print(f"📊 Iniciando extração de {total_abas} categorias...\n")
    print("=" * 100)
    
    for idx, aba in enumerate(abas_json, 1):
        try:
            titulo_aba = aba.get('titulo', 'SEM TÍTULO')
            href_aba = aba.get('href', '')
            
            print(f"\n🔗 Categoria [{idx:2d}/{total_abas}]: {titulo_aba}")
            
            if not href_aba:
                print(f"   ⚠️  Sem href disponível")
                dados_categorias.append({
                    "numero": idx,
                    "titulo": titulo_aba,
                    "href": href_aba,
                    "total_resenhas": 0,
                    "resenhas": []
                })
                continue
            
            print(f"   Navegando...")
            driver.get(href_aba)
            time.sleep(2)
            
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                print("   ⚠️  Timeout")
            
            # ✅ USAR FUNÇÃO v2
            resenhas = extrair_resenhas_otimizado_v2(driver)
            
            dados_categorias.append({
                "numero": idx,
                "titulo": titulo_aba,
                "href": href_aba,
                "total_resenhas": len(resenhas),
                "resenhas": resenhas
            })
            
            print(f"   ✓ Categoria processada!")
            
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            dados_categorias.append({
                "numero": idx,
                "titulo": aba.get('titulo', ''),
                "href": aba.get('href', ''),
                "total_resenhas": 0,
                "resenhas": []
            })
    
    print("\n" + "=" * 100)
    total_resenhas = sum(c['total_resenhas'] for c in dados_categorias)
    print(f"\n✓ Extração concluída!")
    print(f"  Total de categorias: {len(dados_categorias)}")
    print(f"  Total de resenhas: {total_resenhas}\n")
    
    return dados_categorias

def salvar_categorias_json(dados_categorias, nome_arquivo='data/json/atos_categorias.json'):
    try:
        data_extracao = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        dados_completos = {
            "data_extracao": data_extracao,
            "total_categorias": len(dados_categorias),
            "total_resenhas": sum(c['total_resenhas'] for c in dados_categorias),
            "categorias": dados_categorias
        }
        
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados_completos, f, indent=2, ensure_ascii=False)
        
        caminho = os.path.abspath(nome_arquivo)
        
        print("✅ JSON SALVO COM SUCESSO!")
        print("=" * 100)
        print(f"📄 Arquivo: {caminho}")
        print(f"📋 Categorias: {len(dados_categorias)}")
        print(f"📚 Resenhas: {sum(c['total_resenhas'] for c in dados_categorias)}")
        print("=" * 100 + "\n")
        
    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")

def executar_scraping():
   
    driver = criar_driver()
    
    try:
        abas = carregar_categorias_json('data/json/abas.json')
        
        if not abas:
            return
        
        dados_categorias = extrair_conteudo_categorias(driver, abas.get('abas', []))
        
        if dados_categorias:
            salvar_categorias_json(dados_categorias, 'data/json/atos_categorias.json')
        
        print("\n✓ Firefox aberto. Feche manualmente quando terminar.")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        driver.quit()
        pass

if __name__ == "__main__":
    executar_scraping()