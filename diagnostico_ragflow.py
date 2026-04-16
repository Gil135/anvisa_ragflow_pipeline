import requests
import json
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# ===== IMPORTAR CONFIGURAÇÕES DO .env =====
from config import (
    RAGFLOW_BASE_URL,
    RAGFLOW_API_KEY,
    DATASET_ID,
  
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("=" * 60)
print("🔍 DIAGNÓSTICO RAGFlow")
print("=" * 60)

print(f"\n✓ Configurações carregadas:")
print(f"  - URL: {RAGFLOW_BASE_URL}")
print(f"  - API_KEY: {RAGFLOW_API_KEY[:20]}...")
print(f"  - DATASET_ID: {DATASET_ID}")

# Teste 1: Conexão
print("\n[1/4] Testando conexão...")
try:
    response = requests.get(f"{RAGFLOW_BASE_URL}/health", timeout=5)
    print(f"  ✓ Conexão OK (Status: {response.status_code})")
except Exception as e:
    print(f"  ✗ ERRO: {e}")
    print(f"  → RAGFlow não está respondendo em {RAGFLOW_BASE_URL}")
    exit(1)

# Teste 2: Autenticação
print("\n[2/4] Testando autenticação...")
headers = {'Authorization': f'Bearer {RAGFLOW_API_KEY}'}
try:
    response = requests.get(
        f"{RAGFLOW_BASE_URL}/api/v1/datasets",
        headers=headers,
        timeout=5
    )
    if response.status_code == 200:
        print(f"  ✓ Autenticação OK")
    else:
        print(f"  ✗ ERRO: Status {response.status_code}")
        print(f"  → Resposta: {response.text[:200]}")
except Exception as e:
    print(f"  ✗ ERRO: {e}")

# Teste 3: Dataset existe
print("\n[3/4] Verificando dataset...")
try:
    response = requests.get(
        f"{RAGFLOW_BASE_URL}/api/v1/datasets/{DATASET_ID}",
        headers=headers,
        timeout=5
    )
    if response.status_code == 200:
        print(f"  ✓ Dataset existe")
        data = response.json()
        print(f"    Documentos no dataset: {data.get('data', {}).get('doc_count', '?')}")
    else:
        print(f"  ✗ ERRO: Status {response.status_code}")
        print(f"  → Dataset não encontrado ou erro na API")
except Exception as e:
    print(f"  ✗ ERRO: {e}")

# Teste 4: Upload teste
print("\n[4/4] Testando upload de documento...")
try:
    # Criar documento de teste
    doc_test = {
        'name': 'TESTE INM 999/2099',
        'content': 'Este é um documento de teste para verificar se o RAGFlow está recebendo uploads.',
        'metadata': {'tipo': 'TEST', 'categoria': 'TESTE'}
    }
    
    response = requests.post(
        f"{RAGFLOW_BASE_URL}/api/v1/datasets/{DATASET_ID}/documents",
        headers={'Authorization': f'Bearer {RAGFLOW_API_KEY}', 'Content-Type': 'application/json'},
        json={'documents': [doc_test]},
        timeout=10
    )
    
    if response.status_code in [200, 201]:
        print(f"  ✓ Upload OK!")
        print(f"    Resposta: {response.json()}")
    else:
        print(f"  ✗ ERRO: Status {response.status_code}")
        print(f"    Resposta: {response.text[:500]}")
except Exception as e:
    print(f"  ✗ ERRO: {e}")

print("\n" + "=" * 60)
print("✅ Diagnóstico concluído")
print("=" * 60)
