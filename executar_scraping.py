import logging
import sys

from extrair_abas import executar_scraping as executar_abas
from extrair_categorias import executar_scraping as executar_categorias
from extrair_atos_json import executar_scraping as executar_atos
from upload_pdfs_ragflow import RAGFlowPDFUploader as executar_uploader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/orquestrador.log'),
        logging.StreamHandler()
    ]
)

def main():
    """
    Função principal que orquestra a execução sequencial dos scrapings.
    """
    try:
        logging.info("Iniciando extração de abas...")
        result_abas = executar_abas()
        logging.info("Extração de abas concluída com sucesso.")
    except Exception as e:
        logging.error(f"Erro na extração de abas: {str(e)}")
        sys.exit(1)

    try:
        logging.info("Iniciando extração de categorias...")
        result_categorias = executar_categorias()
        logging.info("Extração de categorias concluída com sucesso.")
    except Exception as e:
        logging.error(f"Erro na extração de categorias: {str(e)}")
        sys.exit(1)

    try:
        logging.info("Iniciando extração de atos...")
        result_atos = executar_atos()
        logging.info("Extração de atos concluída com sucesso.")
    except Exception as e:
        logging.error(f"Erro na extração de atos: {str(e)}")
        sys.exit(1)
        
    try:
        logging.info("Iniciando upload de PDFs...")
        uploader = executar_uploader()
        uploader.upload_pdfs()
        logging.info("Upload de PDFs concluído com sucesso.")
    except Exception as e:
        logging.error(f"Erro no upload de PDFs: {str(e)}")
        sys.exit(1)
        
        

    # Geração do relatório final
    logging.info("Gerando relatório final...")
    report = {
        "abas": result_abas,
        "categorias": result_categorias,
        "atos": result_atos
    }
    print("Relatório final:", report)
    logging.info("Processo concluído com sucesso.")

if __name__ == "__main__":
    main()
