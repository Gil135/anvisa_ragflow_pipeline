"""
config.py
=========
Carrega configurações do arquivo .env
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ===== CARREGAR .env =====
# Procura por .env na raiz do projeto
env_path = Path(__file__).parent / '.env'

if not env_path.exists():
    raise FileNotFoundError(
        f"❌ Arquivo '.env' não encontrado em {env_path}\n"
        f"   Copie '.env.example' para '.env' e configure suas credenciais"
    )

load_dotenv(env_path)

# ===== RAGFLOW CONFIGURATION =====
RAGFLOW_BASE_URL = os.getenv('RAGFLOW_BASE_URL', 'http://localhost:9380')
RAGFLOW_API_KEY = os.getenv('RAGFLOW_API_KEY', '')
DATASET_ID = os.getenv('DATASET_ID', '')

# Validar credenciais
if not RAGFLOW_API_KEY:
    raise ValueError("❌ RAGFLOW_API_KEY não configurada no .env")
if not DATASET_ID:
    raise ValueError("❌ DATASET_ID não configurada no .env")

# ===== DOWNLOAD CONFIGURATION =====
PASTA_PDFS = os.getenv('PASTA_PDFS', 'data/pdf')
ARQUIVO_PROGRESSO = os.getenv('ARQUIVO_PROGRESSO', 'data/progresso_ragflow.json')
PASTA_DOWNLOADS = os.path.expanduser(os.getenv('PASTA_DOWNLOADS', '~/Downloads'))

# ===== RETRY CONFIGURATION =====
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_DELAY = int(os.getenv('RETRY_DELAY', '2'))
TIMEOUT = int(os.getenv('TIMEOUT', '60'))

# ===== LOGGING CONFIGURATION =====
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_DIR = os.getenv('LOG_DIR', 'logs')

# Criar diretório de logs se não existir
os.makedirs(LOG_DIR, exist_ok=True)

# ===== EXECUTION CONFIGURATION =====
EXECUTAR_ETAPA_1 = os.getenv('EXECUTAR_ETAPA_1', 'True').lower() == 'true'
EXECUTAR_ETAPA_2 = os.getenv('EXECUTAR_ETAPA_2', 'True').lower() == 'true'
EXECUTAR_ETAPA_3 = os.getenv('EXECUTAR_ETAPA_3', 'True').lower() == 'true'
EXECUTAR_ETAPA_4 = os.getenv('EXECUTAR_ETAPA_4', 'True').lower() == 'true'
DELAY_ENTRE_ETAPAS = int(os.getenv('DELAY_ENTRE_ETAPAS', '5'))
MODO_VERBOSE = os.getenv('MODO_VERBOSE', 'True').lower() == 'true'

# ===== EXIBIR CONFIGURAÇÕES (DEBUG) =====
if MODO_VERBOSE:
    print("\n" + "="*70)
    print("⚙️  CONFIGURAÇÕES CARREGADAS DO .env")
    print("="*70)
    print(f"RAGFlow URL: {RAGFLOW_BASE_URL}")
    print(f"Dataset ID: {DATASET_ID}")
    print(f"Pasta PDFs: {PASTA_PDFS}")
    print(f"Max Retries: {MAX_RETRIES}")
    print(f"Timeout: {TIMEOUT}s")
    print(f"Log Level: {LOG_LEVEL}")
    print("="*70 + "\n")