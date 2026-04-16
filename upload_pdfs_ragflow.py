"""
upload_pdfs_ragflow.py
======================
Script para enviar PDFs baixados para RAGFlow.
Usa configurações do arquivo .env
"""

import json
import requests
import logging
import os
import time
import datetime
from pathlib import Path
from typing import List, Dict, Tuple

# ===== IMPORTAR CONFIGURAÇÕES DO .env =====
from config import (
    RAGFLOW_BASE_URL,
    RAGFLOW_API_KEY,
    DATASET_ID,
    PASTA_PDFS,
    ARQUIVO_PROGRESSO,
    MAX_RETRIES,
    RETRY_DELAY,
    TIMEOUT,
    LOG_LEVEL,
    LOG_DIR
)

# ===== CONFIGURAR LOGGING =====
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{LOG_DIR}/ragflow_upload_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== CLASSE PRINCIPAL =====

class RAGFlowPDFUploader:
    """Classe para fazer upload de PDFs para RAGFlow"""
    
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
        return {"processados": [], "data_inicio": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    def _salvar_progresso(self):
        """Salva progresso atual"""
        os.makedirs(os.path.dirname(ARQUIVO_PROGRESSO), exist_ok=True)
        with open(ARQUIVO_PROGRESSO, 'w', encoding='utf-8') as f:
            json.dump(self.progresso, f, indent=2, ensure_ascii=False)
    
    def _obter_pdfs(self) -> List[Tuple[str, str]]:
        """Obtém lista de PDFs da pasta"""
        if not os.path.exists(PASTA_PDFS):
            logger.error(f"Pasta '{PASTA_PDFS}' não encontrada")
            return []
        
        pdfs = []
        for arquivo in sorted(os.listdir(PASTA_PDFS)):
            if arquivo.lower().endswith('.pdf'):
                caminho = os.path.join(PASTA_PDFS, arquivo)
                pdfs.append((arquivo, caminho))
        
        logger.info(f"✓ {len(pdfs)} PDFs encontrados em '{PASTA_PDFS}'")
        return pdfs
    
    def _validar_pdf(self, caminho: str) -> Tuple[bool, str]:
        """Valida se o PDF é válido"""
        try:
            tamanho = os.path.getsize(caminho)
            
            # Verificar tamanho mínimo (100 bytes)
            if tamanho < 100:
                return False, f"Arquivo muito pequeno ({tamanho} bytes)"
            
            # Verificar se é um PDF válido
            with open(caminho, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    return False, "Não é um PDF válido (header inválido)"
            
            return True, f"{tamanho / (1024*1024):.2f} MB"
            
        except Exception as e:
            return False, str(e)
    
    def _extrair_metadados(self, nome_arquivo: str) -> Dict:
        """Extrai metadados do nome do arquivo"""
        # Formato: 00001_Título_do_Documento.pdf
        partes = nome_arquivo.replace('.pdf', '').split('_', 1)
        
        numero = partes[0] if partes else '0'
        titulo = partes[1].replace('_', ' ') if len(partes) > 1 else nome_arquivo
        
        return {
            'numero': numero,
            'titulo': titulo,
            'nome_arquivo': nome_arquivo
        }
    
    def upload_pdf(self, nome_arquivo: str, caminho_pdf: str) -> bool:
        """Faz upload de um PDF para RAGFlow"""
        
        # Validar PDF
        valido, mensagem = self._validar_pdf(caminho_pdf)
        if not valido:
            logger.error(f"✗ PDF inválido: {nome_arquivo} - {mensagem}")
            self.failed_count += 1
            return False
        
        metadados = self._extrair_metadados(nome_arquivo)
        
        for tentativa in range(MAX_RETRIES):
            try:
                logger.info(f"Enviando: {nome_arquivo} ({mensagem})")
                
                with open(caminho_pdf, 'rb') as f:
                    files = {'file': (nome_arquivo, f, 'application/pdf')}
                    
                    url = f"{RAGFLOW_BASE_URL}/api/v1/datasets/{DATASET_ID}/documents"
                    
                    response = self.session.post(
                        url,
                        files=files,
                        timeout=TIMEOUT,
                        data={'name': metadados['titulo']}
                    )
                
                # Sucesso
                if response.status_code in [200, 201]:
                    logger.info(f"✅ {nome_arquivo}")
                    self.uploaded_count += 1
                    self.progresso['processados'].append(nome_arquivo)
                    self._salvar_progresso()
                    return True
                
                # Rate limit
                elif response.status_code == 429:
                    wait_time = int(response.headers.get('Retry-After', RETRY_DELAY))
                    logger.warning(f"⚠️  Rate limit. Aguardando {wait_time}s... (tentativa {tentativa + 1}/{MAX_RETRIES})")
                    time.sleep(wait_time)
                    continue
                
                # Arquivo muito grande
                elif response.status_code == 413:
                    logger.error(f"✗ {nome_arquivo}: Arquivo muito grande para RAGFlow")
                    self.failed_count += 1
                    return False
                
                # Outros erros
                else:
                    try:
                        erro = response.json().get('message', response.text)
                    except:
                        erro = response.text
                    
                    logger.error(f"✗ {nome_arquivo}: {response.status_code} - {erro}")
                    
                    if tentativa < MAX_RETRIES - 1:
                        espera = RETRY_DELAY * (tentativa + 1)
                        logger.info(f"  Tentando novamente em {espera}s...")
                        time.sleep(espera)
                    else:
                        self.failed_count += 1
                        return False
            
            except requests.exceptions.Timeout:
                logger.warning(f"⚠️  Timeout (tentativa {tentativa + 1}/{MAX_RETRIES})")
                if tentativa < MAX_RETRIES - 1:
                    espera = RETRY_DELAY * (tentativa + 1)
                    time.sleep(espera)
                else:
                    self.failed_count += 1
                    return False
            
            except requests.exceptions.ConnectionError:
                logger.error(f"✗ {nome_arquivo}: Erro de conexão com RAGFlow")
                logger.error(f"  Verifique se RAGFlow está rodando em {RAGFLOW_BASE_URL}")
                self.failed_count += 1
                return False
            
            except Exception as e:
                logger.error(f"✗ {nome_arquivo}: Erro inesperado - {e}")
                self.failed_count += 1
                return False
        
        return False
    
    def executar(self):
        """Executa o upload de todos os PDFs"""
        
        logger.info("=" * 100)
        logger.info("🚀 UPLOAD DE PDFs PARA RAGFlow")
        logger.info("=" * 100)
        logger.info(f"RAGFlow URL: {RAGFLOW_BASE_URL}")
        logger.info(f"Dataset ID: {DATASET_ID}")
        logger.info(f"Pasta de PDFs: {PASTA_PDFS}\n")
        
        # Obter lista de PDFs
        pdfs = self._obter_pdfs()
        
        if not pdfs:
            logger.error("Nenhum PDF encontrado para processar")
            return
        
        # Filtrar PDFs já processados
        pdfs_pendentes = [
            (nome, caminho) for nome, caminho in pdfs
            if nome not in self.progresso['processados']
        ]
        
        if len(pdfs_pendentes) < len(pdfs):
            self.skipped_count = len(pdfs) - len(pdfs_pendentes)
            logger.info(f"⏸️  {self.skipped_count} PDFs já foram processados anteriormente\n")
        
        total = len(pdfs_pendentes)
        
        if total == 0:
            logger.info("✓ Todos os PDFs já foram processados!")
            return
        
        logger.info(f"Total de PDFs para processar: {total}\n")
        print("=" * 100)
        
        # Processar cada PDF
        for idx, (nome_arquivo, caminho_pdf) in enumerate(pdfs_pendentes, 1):
            print(f"[{idx:4d}/{total}] ", end="", flush=True)
            self.upload_pdf(nome_arquivo, caminho_pdf)
            time.sleep(1)  # Pequeno delay entre uploads
        
        # Relatório final
        print("\n" + "=" * 100)
        logger.info("\n✓ PROCESSAMENTO CONCLUÍDO!")
        logger.info(f"  ✅ Sucesso: {self.uploaded_count}")
        logger.info(f"  ❌ Erro: {self.failed_count}")
        logger.info(f"  ⏭️  Pulados: {self.skipped_count}")
        
        total_geral = self.uploaded_count + self.failed_count + self.skipped_count
        if total_geral > 0:
            taxa_sucesso = (self.uploaded_count / total_geral * 100)
            logger.info(f"  📊 Taxa de sucesso: {taxa_sucesso:.1f}%")
        
        logger.info("=" * 100)
        
        # Salvar relatório final
        self._salvar_relatorio_final()
    
    def _salvar_relatorio_final(self):
        """Salva relatório final em JSON"""
        relatorio = {
            "data_execucao": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_processados": self.uploaded_count + self.failed_count,
            "sucesso": self.uploaded_count,
            "erro": self.failed_count,
            "pulados": self.skipped_count,
            "taxa_sucesso": f"{(self.uploaded_count / (self.uploaded_count + self.failed_count) * 100) if (self.uploaded_count + self.failed_count) > 0 else 0:.1f}%",
            "ragflow_url": RAGFLOW_BASE_URL,
            "dataset_id": DATASET_ID
        }
        
        try:
            os.makedirs('data/json', exist_ok=True)
            with open('data/json/relatorio_ragflow.json', 'w', encoding='utf-8') as f:
                json.dump(relatorio, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Relatório salvo em: data/json/relatorio_ragflow.json")
        except Exception as e:
            logger.error(f"Erro ao salvar relatório: {e}")

# ===== FUNÇÃO PRINCIPAL =====

def main():
    """Função principal"""
    try:
        uploader = RAGFlowPDFUploader()
        uploader.executar()
    except KeyboardInterrupt:
        logger.info("\n⏸️  Processo pausado pelo usuário. Você pode retomar depois.")
    except Exception as e:
        logger.error(f"Erro fatal: {e}")

if __name__ == '__main__':
    main()