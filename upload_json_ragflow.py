import json
import requests
import tempfile
import logging
import os
import time
from typing import List, Dict

# Configurações
RAGFLOW_BASE_URL = 'http://localhost:9380'
RAGFLOW_API_KEY = 'ragflow-fydunjb9dODPUM2YZioZVtaFsHGSqP9_rVb1yT5jwsc'
DATASET_ID = 'b8fe1b8238cf11f19fbaa967cd1ae4ee'
MAX_RETRIES = 3
RETRY_DELAY = 2

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/ragflow_upload.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class RAGFlowUploader:
    def __init__(self):
        self.uploaded_count = 0
        self.failed_count = 0
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {RAGFLOW_API_KEY}'})

    def load_data(self) -> List[Dict]:
        """Carrega JSON e normaliza para lista de atos"""
        try:
            with open('data/atos_completos.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"✓ JSON carregado com sucesso")
            
            # Cenário 1: JSON é um array direto (COSMÉTICOS)
            if isinstance(data, list):
                logger.info(f"  Formato: Array com {len(data)} documentos")
                return self._normalizar_array(data)
            
            # Cenário 2: JSON é objeto com categorias (AGROTÓXICOS)
            elif isinstance(data, dict) and 'categorias' in data:
                logger.info(f"  Formato: Objeto com categorias")
                return self._normalizar_categorias(data)
            
            # Cenário 3: JSON é objeto simples
            elif isinstance(data, dict):
                logger.info(f"  Formato: Objeto simples")
                return [data]
            
            else:
                raise ValueError(f"Estrutura JSON não reconhecida: {type(data)}")
        
        except json.JSONDecodeError as e:
            logger.error(f"✗ JSON inválido na linha {e.lineno}, coluna {e.colno}: {e.msg}")
            raise
        except Exception as e:
            logger.error(f"✗ Erro ao carregar JSON: {e}")
            raise

    def _normalizar_array(self, data: List[Dict]) -> List[Dict]:
        """Converte array de documentos para formato padrão"""
        atos = []
        for idx, doc in enumerate(data, 1):
            ato = {
                'numero_sequencial': idx,
                'numero_ato_categoria': idx,
                'tipo_ato': doc.get('metadata', {}).get('tipo', 'DOC'),
                'numero_ato': doc.get('metadata', {}).get('numero', ''),
                'ano_ato': doc.get('metadata', {}).get('ano', ''),
                'titulo': doc.get('title', ''),
                'tipo_conteudo': 'ato_completo',
                'tamanho_caracteres': len(doc.get('content', '')),
                'status': 'sucesso',
                'conteudo_texto': doc.get('content', '')
            }
            atos.append(ato)
        logger.info(f"  Normalizados {len(atos)} documentos do array")
        return atos

    def _normalizar_categorias(self, data: Dict) -> List[Dict]:
        """Extrai atos de estrutura com categorias"""
        atos = []
        for categoria in data.get('categorias', []):
            atos.extend(categoria.get('atos', []))
        logger.info(f"  Normalizados {len(atos)} atos de {len(data.get('categorias', []))} categorias")
        return atos

    def upload_ato(self, ato: Dict) -> bool:
        """Faz upload de um ato para RAGFlow"""
        tipo_ato = ato.get('tipo_ato', '')
        numero_ato = ato.get('numero_ato', '')
        ano_ato = ato.get('ano_ato', '')
        titulo = ato.get('titulo', '')
        conteudo_texto = ato.get('conteudo_texto', '')

        if not conteudo_texto:
            logger.warning(f"⚠ Conteúdo vazio: {tipo_ato} {numero_ato}/{ano_ato}")
            self.failed_count += 1
            return False

        conteudo_completo = f"""TIPO: {tipo_ato}
NÚMERO: {numero_ato}/{ano_ato}
TÍTULO: {titulo}
---
{conteudo_texto}"""

        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(conteudo_completo)
                temp_file_path = temp_file.name

            for attempt in range(MAX_RETRIES):
                try:
                    with open(temp_file_path, 'rb') as f:
                        files = {'file': (f"{tipo_ato}_{numero_ato}_{ano_ato}.txt", f, 'text/plain')}
                        url = f"{RAGFLOW_BASE_URL}/api/v1/datasets/{DATASET_ID}/documents"
                        response = self.session.post(url, files=files, timeout=30)

                    if response.status_code in [200, 201]:
                        logger.info(f"✓ {tipo_ato} {numero_ato}/{ano_ato}")
                        self.uploaded_count += 1
                        return True
                    
                    elif response.status_code == 429:
                        wait_time = int(response.headers.get('Retry-After', RETRY_DELAY))
                        logger.warning(f"⚠ Rate limit. Aguardando {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    
                    elif response.status_code == 413:
                        logger.error(f"✗ {tipo_ato} {numero_ato}/{ano_ato}: Arquivo muito grande")
                        self.failed_count += 1
                        return False
                    
                    else:
                        try:
                            error_detail = response.json().get('message', response.text)
                        except:
                            error_detail = response.text
                        logger.error(f"✗ {tipo_ato} {numero_ato}/{ano_ato}: {response.status_code} - {error_detail}")
                        
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(RETRY_DELAY * (attempt + 1))
                        else:
                            self.failed_count += 1
                            return False

                except requests.exceptions.Timeout:
                    logger.warning(f"⚠ Timeout (tentativa {attempt + 1}/{MAX_RETRIES})")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY * (attempt + 1))
                    else:
                        self.failed_count += 1
                        return False

        except Exception as e:
            logger.error(f"✗ Erro: {tipo_ato} {numero_ato}/{ano_ato}: {e}")
            self.failed_count += 1
            return False
        
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def run(self):
        """Executa o upload de todos os atos"""
        logger.info("=" * 70)
        logger.info("ANVISA → RAGFlow Upload")
        logger.info("=" * 70)

        try:
            atos = self.load_data()
        except Exception as e:
            logger.error(f"Falha ao carregar dados: {e}")
            return

        total = len(atos)
        logger.info(f"Total de atos para processar: {total}\n")
        
        for idx, ato in enumerate(atos, 1):
            logger.info(f"[{idx}/{total}] Processando...")
            self.upload_ato(ato)

        logger.info("\n" + "=" * 70)
        logger.info(f"✓ Sucesso: {self.uploaded_count}")
        logger.info(f"✗ Erro: {self.failed_count}")
        if total > 0:
            logger.info(f"Taxa de sucesso: {(self.uploaded_count/total*100):.1f}%")
        logger.info("=" * 70)

if __name__ == '__main__':
    uploader = RAGFlowUploader()
    uploader.run()