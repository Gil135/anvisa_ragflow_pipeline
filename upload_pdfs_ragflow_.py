"""
upload_pdfs_ragflow.py
======================
Script para fazer upload de PDFs da pasta data/pdf para RAGFlow.
Versão otimizada com validação, retry automático e progresso salvo.
"""

import json
import requests
import logging
import os
import time
from pathlib import Path
from typing import List, Dict
import PyPDF2

# ===== CONFIGURAÇÕES =====
RAGFLOW_BASE_URL = 'http://localhost:9380'
RAGFLOW_API_KEY = 'ragflow-fydunjb9dODPUM2YZioZVtaFsHGSqP9_rVb1yT5jwsc'
DATASET_ID = 'b8fe1b8238cf11f19fbaa967cd1ae4ee'
MAX_RETRIES = 3
RETRY_DELAY = 2
PASTA_PDFS = 'data/pdf'
ARQUIVO_PROGRESSO = 'data/progresso_ragflow.json'

# ===== CONFIGURAR LOGGING =====
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/ragflow_upload_{time.strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== CLASSE PRINCIPAL =====

class RAGFlowPDFUploader:
    """Faz upload de PDFs para RAGFlow"""
    
    def __init__(self):
        self.uploaded_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {RAGFLOW_API_KEY}'})
        self.progresso = self._carregar_progresso()
    
    def _carregar_progresso(self) -> Dict:
        """Carrega progresso anterior"""
        if os.path.exists(ARQUIVO_PROGRESSO):
            try:
                with open(ARQUIVO_PROGRESSO, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"uploadados": [], "falhados": []}
    
    def _salvar_progresso(self):
        """Salva progresso atual"""
        os.makedirs(os.path.dirname(ARQUIVO_PROGRESSO), exist_ok=True)
        with open(ARQUIVO_PROGRESSO, 'w', encoding='utf-8') as f:
            json.dump(self.progresso, f, indent=2, ensure_ascii=False)
    
    def _validar_pdf(self, caminho_pdf: str) -> bool:
        """Valida se o PDF é válido"""
        try:
            with open(caminho_pdf, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                num_paginas = len(pdf_reader.pages)
                
                if num_paginas == 0:
                    logger.warning(f"⚠️  PDF vazio: {caminho_pdf}")
                    return False
                
                logger.info(f"  ✓ PDF válido ({num_paginas} páginas)")
                return True
        except Exception as e:
            logger.error(f"  ✗ PDF inválido: {e}")
            return False
    
    def _obter_tamanho_arquivo(self, caminho_pdf: str) -> str:
        """Obtém tamanho do arquivo em formato legível"""
        tamanho_bytes = os.path.getsize(caminho_pdf)
        for unidade in ['B', 'KB', 'MB', 'GB']:
            if tamanho_bytes < 1024:
                return f"{tamanho_bytes:.2f} {unidade}"
            tamanho_bytes /= 1024
        return f"{tamanho_bytes:.2f} TB"
    
    def _extrair_numero_sequencial(self, nome_arquivo: str) -> int:
        """Extrai número sequencial do nome do arquivo"""
        try:
            return int(nome_arquivo.split('_')[0])
        except:
            return 0
    
    def listar_pdfs(self) -> List[str]:
        """Lista todos os PDFs na pasta data/pdf"""
        if not os.path.exists(PASTA_PDFS):
            logger.error(f"Pasta '{PASTA_PDFS}' não encontrada")
            return []
        
        pdfs = sorted(
            [os.path.join(PASTA_PDFS, f) for f in os.listdir(PASTA_PDFS) if f.lower().endswith('.pdf')],
            key=lambda x: self._extrair_numero_sequencial(os.path.basename(x))
        )
        
        logger.info(f"✓ {len(pdfs)} PDFs encontrados em '{PASTA_PDFS}'")
        return pdfs
    
    def upload_pdf(self, caminho_pdf: str) -> bool:
        """Faz upload de um PDF para RAGFlow"""
        
        nome_arquivo = os.path.basename(caminho_pdf)
        
        # Verificar se já foi uploadado
        if nome_arquivo in self.progresso['uploadados']:
            logger.info(f"⏭️  Já uploadado: {nome_arquivo}")
            self.skipped_count += 1
            return True
        
        # Verificar se falhou antes
        if nome_arquivo in self.progresso['falhados']:
            logger.info(f"🔄 Retentando: {nome_arquivo}")
        
        logger.info(f"Validando PDF...")
        if not self._validar_pdf(caminho_pdf):
            self.progresso['falhados'].append(nome_arquivo)
            self.failed_count += 1
            return False
        
        tamanho = self._obter_tamanho_arquivo(caminho_pdf)
        logger.info(f"  Tamanho: {tamanho}")
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"  Enviando para RAGFlow (tentativa {attempt + 1}/{MAX_RETRIES})...")
                
                with open(caminho_pdf, 'rb') as f:
                    files = {'file': (nome_arquivo, f, 'application/pdf')}
                    url = f"{RAGFLOW_BASE_URL}/api/v1/datasets/{DATASET_ID}/documents"
                    
                    response = self.session.post(url, files=files, timeout=60)
                
                if response.status_code in [200, 201]:
                    logger.info(f"✅ Upload bem-sucedido: {nome_arquivo}")
                    self.progresso['uploadados'].append(nome_arquivo)
                    if nome_arquivo in self.progresso['falhados']:
                        self.progresso['falhados'].remove(nome_arquivo)
                    self.uploaded_count += 1
                    return True
                
                elif response.status_code == 429:
                    wait_time = int(response.headers.get('Retry-After', RETRY_DELAY))
                    logger.warning(f"⚠️  Rate limit. Aguardando {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                elif response.status_code == 413:
                    logger.error(f"❌ Arquivo muito grande (máx 100MB)")
                    self.progresso['falhados'].append(nome_arquivo)
                    self.failed_count += 1
                    return False
                
                else:
                    try:
                        error_detail = response.json().get('message', response.text)
                    except:
                        error_detail = response.text
                    
                    logger.error(f"❌ Erro {response.status_code}: {error_detail}")
                    
                    if attempt < MAX_RETRIES - 1:
                        wait = RETRY_DELAY * (attempt + 1)
                        logger.info(f"  Aguardando {wait}s antes de retentativa...")
                        time.sleep(wait)
                    else:
                        self.progresso['falhados'].append(nome_arquivo)
                        self.failed_count += 1
                        return False
            
            except requests.exceptions.Timeout:
                logger.warning(f"⚠️  Timeout (tentativa {attempt + 1}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_DELAY * (attempt + 1)
                    time.sleep(wait)
                else:
                    self.progresso['falhados'].append(nome_arquivo)
                    self.failed_count += 1
                    return False
            
            except Exception as e:
                logger.error(f"❌ Erro: {e}")
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_DELAY * (attempt + 1)
                    time.sleep(wait)
                else:
                    self.progresso['falhados'].append(nome_arquivo)
                    self.failed_count += 1
                    return False
        
        return False
    
    def run(self):
        """Executa o upload de todos os PDFs"""
        
        logger.info("=" * 120)
        logger.info("🚀 UPLOAD DE PDFs PARA RAGFLOW")
        logger.info("=" * 120)
        logger.info(f"RAGFlow URL: {RAGFLOW_BASE_URL}")
        logger.info(f"Dataset ID: {DATASET_ID}")
        logger.info(f"Pasta de PDFs: {PASTA_PDFS}\n")
        
        pdfs = self.listar_pdfs()
        
        if not pdfs:
            logger.error("Nenhum PDF encontrado para upload")
            return
        
        total = len(pdfs)
        logger.info(f"Total de PDFs para processar: {total}\n")
        print("=" * 120)
        
        for idx, caminho_pdf in enumerate(pdfs, 1):
            nome_arquivo = os.path.basename(caminho_pdf)
            print(f"\n[{idx}/{total}] {nome_arquivo}")
            print("─" * 120)
            
            try:
                self.upload_pdf(caminho_pdf)
            except KeyboardInterrupt:
                logger.info("⏸️  Processo pausado pelo usuário")
                break
            except Exception as e:
                logger.error(f"Erro inesperado: {e}")
                continue
            
            # Salvar progresso a cada PDF
            self._salvar_progresso()
        
        print("\n" + "=" * 120)
        logger.info("\n✓ RESUMO DO UPLOAD")
        logger.info(f"  ✅ Uploadados: {self.uploaded_count}")
        logger.info(f"  ⏭️  Pulados: {self.skipped_count}")
        logger.info(f"  ❌ Falhados: {self.failed_count}")
        
        if total > 0:
            taxa_sucesso = ((self.uploaded_count + self.skipped_count) / total) * 100
            logger.info(f"  Taxa de sucesso: {taxa_sucesso:.1f}%")
        
        logger.info("=" * 120)
        
        # Salvar progresso final
        self._salvar_progresso()
        
        if self.failed_count > 0:
            logger.warning(f"\n⚠️  {self.failed_count} PDFs falharam. Execute novamente para retentativa.")

if __name__ == '__main__':
    uploader = RAGFlowPDFUploader()
    uploader.run()