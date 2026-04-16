"""
browser_utils.py
================
Módulo para suportar múltiplos navegadores (Firefox, Chrome, Edge, Safari).

Uso:
    from browser_utils import criar_driver
    
    driver = criar_driver(navegador='firefox')
"""

import subprocess
import sys
import platform
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

# ===== DETECTAR SISTEMA =====
SISTEMA = platform.system()  # 'Linux', 'Darwin', 'Windows'

# ===== CONFIGURAÇÕES POR NAVEGADOR =====
NAVEGADORES = {
    'firefox': {
        'driver_cmd': 'geckodriver',
        'package': 'webdriver-manager',
        'options_class': FirefoxOptions,
        'webdriver_class': webdriver.Firefox,
        'plataformas': ['Linux', 'Darwin', 'Windows'],
        'browser_cmd': 'firefox'
    },
    'chrome': {
        'driver_cmd': 'chromedriver',
        'package': 'webdriver-manager',
        'options_class': ChromeOptions,
        'webdriver_class': webdriver.Chrome,
        'plataformas': ['Linux', 'Darwin', 'Windows'],
        'browser_cmd': 'google-chrome'
    },
    'edge': {
        'driver_cmd': 'msedgedriver',
        'package': 'webdriver-manager',
        'options_class': EdgeOptions,
        'webdriver_class': webdriver.Edge,
        'plataformas': ['Windows', 'Darwin'],
        'browser_cmd': 'msedge'
    },
    'safari': {
        'driver_cmd': 'safaridriver',
        'package': None,
        'options_class': None,
        'webdriver_class': webdriver.Safari,
        'plataformas': ['Darwin'],
        'browser_cmd': 'safari'
    }
}

# ===== FUNÇÕES AUXILIARES =====

def verificar_navegador_instalado(navegador='firefox'):
    """Verifica se o navegador está instalado no sistema"""
    
    navegador = navegador.lower()
    
    if navegador not in NAVEGADORES:
        return False
    
    config = NAVEGADORES[navegador]
    browser_cmd = config['browser_cmd']
    
    try:
        subprocess.run([browser_cmd, '--version'], check=True, capture_output=True, timeout=5)
        print(f"✓ {navegador} está instalado")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print(f"❌ {navegador} não está instalado ou não está no PATH")
        return False

def verificar_driver_no_path(driver_cmd):
    """Verifica se o driver está no PATH do sistema"""
    
    try:
        result = subprocess.run([driver_cmd, '--version'], check=True, capture_output=True, timeout=5)
        print(f"✓ {driver_cmd} está no PATH")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print(f"⚠️  {driver_cmd} não está no PATH")
        return False

def instalar_driver(navegador='firefox'):
    """Instala driver do navegador se necessário"""
    
    navegador = navegador.lower()
    
    if navegador not in NAVEGADORES:
        print(f"❌ Navegador '{navegador}' não suportado")
        print(f"   Disponíveis: {', '.join(NAVEGADORES.keys())}")
        return False
    
    config = NAVEGADORES[navegador]
    
    # Verificar plataforma
    if SISTEMA not in config['plataformas']:
        print(f"❌ {navegador} não suporta {SISTEMA}")
        return False
    
    # Verificar se navegador está instalado
    if not verificar_navegador_instalado(navegador):
        print(f"❌ Instale {navegador} no seu sistema primeiro")
        return False
    
    # Safari vem com macOS
    if navegador == 'safari':
        print("✓ Safari já está disponível no macOS")
        return True
    
    # Verificar se driver está no PATH
    if verificar_driver_no_path(config['driver_cmd']):
        return True
    
    # Instalar webdriver-manager
    print(f"\n🔧 Instalando {config['driver_cmd']} via webdriver-manager...")
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--upgrade', config['package']],
            check=True,
            timeout=60
        )
        print(f"✓ webdriver-manager instalado com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar: {e}")
        return False
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout ao instalar")
        return False

def configurar_navegador(navegador='firefox'):
    """Configura opções do navegador para web scraping"""
    
    navegador = navegador.lower()
    
    if navegador not in NAVEGADORES:
        print(f"❌ Navegador '{navegador}' não suportado")
        return None
    
    # Firefox
    if navegador == 'firefox':
        options = FirefoxOptions()
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference('useAutomationExtension', False)
        return options
    
    # Chrome
    elif navegador == 'chrome':
        options = ChromeOptions()
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        return options
    
    # Edge
    elif navegador == 'edge':
        options = EdgeOptions()
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        return options
    
    # Safari
    elif navegador == 'safari':
        print("⚠️  Safari tem suporte limitado a opções")
        return None
    
    return None

def detectar_navegador():
    """Detecta qual navegador está disponível (Chrome > Firefox > Edge > Safari)"""
    
    ordem = ['chrome', 'firefox', 'edge', 'safari']
    
    for nav in ordem:
        config = NAVEGADORES[nav]
        
        if SISTEMA not in config['plataformas']:
            continue
        
        if verificar_navegador_instalado(nav):
            print(f"✓ Navegador detectado: {nav}")
            return nav
    
    return None

def criar_driver(navegador=None):
    """
    Cria instância do WebDriver.
    
    Args:
        navegador (str): 'firefox', 'chrome', 'edge', 'safari'
                        Se None, detecta automaticamente
    
    Returns:
        WebDriver: Instância do driver ou None
    """
    
    print("\n" + "="*70)
    print("🌐 INICIALIZANDO DRIVER")
    print("="*70)
    
    # Detectar automaticamente se não especificado
    if navegador is None:
        print("\n🔍 Detectando navegador disponível...")
        navegador = detectar_navegador()
        if navegador is None:
            print("❌ Nenhum navegador disponível")
            print("   Instale: Firefox, Chrome, Edge ou Safari")
            print("="*70 + "\n")
            return None
    
    navegador = navegador.lower()
    
    if navegador not in NAVEGADORES:
        print(f"❌ Navegador '{navegador}' não suportado")
        print("="*70 + "\n")
        return None
    
    config = NAVEGADORES[navegador]
    
    # Verificar plataforma
    if SISTEMA not in config['plataformas']:
        print(f"❌ {navegador} não suporta {SISTEMA}")
        print("="*70 + "\n")
        return None
    
    # Instalar/verificar driver
    print(f"\n📦 Verificando driver para {navegador}...")
    if not instalar_driver(navegador):
        print("="*70 + "\n")
        return None
    
    # Configurar opções
    print(f"\n⚙️  Configurando {navegador}...")
    options = configurar_navegador(navegador)
    
    # Criar driver
    try:
        print(f"\n🚀 Criando driver {navegador}...")
        
        if navegador == 'firefox':
            from webdriver_manager.firefox import GeckoDriverManager
            from selenium.webdriver.firefox.service import Service
            
            # Usar webdriver-manager para gerenciar o driver
            service = Service(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
        
        elif navegador == 'chrome':
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        
        elif navegador == 'edge':
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            from selenium.webdriver.edge.service import Service
            
            service = Service(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=service, options=options)
        
        elif navegador == 'safari':
            driver = webdriver.Safari()
        
        print(f"✓ Driver {navegador} criado com sucesso!")
        print("="*70 + "\n")
        return driver
    
    except Exception as e:
        print(f"❌ Erro ao criar driver: {e}")
        print(f"\n💡 Dicas de troubleshooting:")
        print(f"   1. Verifique se {navegador} está instalado")
        print(f"   2. Tente: {config['browser_cmd']} --version")
        print(f"   3. Reinstale webdriver-manager: pip install --upgrade webdriver-manager")
        print(f"   4. Limpe cache: rm -rf ~/.wdm/")
        print("="*70 + "\n")
        return None

# ===== COMPATIBILIDADE COM CÓDIGO ANTIGO =====

def instalar_geckodriver():
    """Compatibilidade com firefox_utils.py"""
    return instalar_driver('firefox')

def configurar_firefox():
    """Compatibilidade com firefox_utils.py"""
    return configurar_navegador('firefox')

# ===== TESTE =====

if __name__ == '__main__':
    print("\n" + "="*70)
    print("📊 INFORMAÇÕES DO SISTEMA")
    print("="*70)
    print(f"Sistema: {SISTEMA}")
    print(f"Python: {sys.version.split()[0]}")
    print("="*70)
    
    driver = criar_driver()
    
    if driver:
        print("✓ Teste bem-sucedido!")
        driver.quit()
    else:
        print("❌ Falha no teste")