#!/usr/bin/env python3
import subprocess
import sys

def run_command(cmd, description):
    print(f"\n▶ {description}...")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌ Erro ao executar: {description}")
        sys.exit(1)
    print(f"✅ {description} concluída")
    

if __name__ == "__main__":
    print("=" * 60)
    print("ANVISA SCRAPER → RAGFlow PIPELINE")
    print("=" * 60)
    
    run_command("python3 extrair_abas.py", "Fase 1: Extração de Abas")
    run_command("python3 extrair_categorias.py", "Fase 2: Extração de Categorias")
    run_command("python3 extrair_atos_pdfs.py", "Fase 3: Extração de Atos PDFs")
    run_command("python3 upload_pdfs_ragflow.py", "Fase 4: Upload para RAGFlow")
    
    print("\n" + "=" * 60)
    print("✅ PIPELINE CONCLUÍDA COM SUCESSO!")
    print("=" * 60)
    print("\n📊 Dados disponíveis em: http://localhost:9222")
    print("🔑 Dataset ID: b8fe1b8238cf11f19fbaa967cd1ae4ee")