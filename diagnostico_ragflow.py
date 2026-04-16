import os
import chardet
import shutil
from pathlib import Path

def verificar_integridade_arquivo(caminho_arquivo):
    """Verifica se o arquivo existe e não está corrompido."""
    if not os.path.exists(caminho_arquivo):
        return False, "Arquivo não encontrado."
    try:
        with open(caminho_arquivo, 'rb') as f:
            f.read(1024)  # Tenta ler um pouco
        return True, "Arquivo íntegro."
    except Exception as e:
        return False, f"Arquivo corrompido: {str(e)}"

def validar_encoding(caminho_arquivo):
    """Valida se o arquivo está em UTF-8."""
    with open(caminho_arquivo, 'rb') as f:
        raw_data = f.read()
    detected = chardet.detect(raw_data)
    if detected['encoding'] == 'utf-8':
        return True, "Encoding UTF-8 válido."
    else:
        return False, f"Encoding detectado: {detected['encoding']}. Recomenda-se converter para UTF-8."

def dividir_arquivo_grande(caminho_arquivo, tamanho_max=10*1024*1024):  # 10MB
    """Divide arquivos grandes em partes menores."""
    tamanho = os.path.getsize(caminho_arquivo)
    if tamanho <= tamanho_max:
        return [caminho_arquivo], "Arquivo não precisa ser dividido."
    
    partes = []
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Dividir por linhas, aproximadamente
    linhas = conteudo.split('\n')
    parte_atual = []
    tamanho_parte = 0
    num_parte = 1
    
    for linha in linhas:
        parte_atual.append(linha)
        tamanho_parte += len(linha.encode('utf-8'))
        if tamanho_parte >= tamanho_max:
            parte_caminho = f"{caminho_arquivo}_parte_{num_parte}.txt"
            with open(parte_caminho, 'w', encoding='utf-8') as pf:
                pf.write('\n'.join(parte_atual))
            partes.append(parte_caminho)
            parte_atual = []
            tamanho_parte = 0
            num_parte += 1
    
    if parte_atual:
        parte_caminho = f"{caminho_arquivo}_parte_{num_parte}.txt"
        with open(parte_caminho, 'w', encoding='utf-8') as pf:
            pf.write('\n'.join(parte_atual))
        partes.append(parte_caminho)
    
    return partes, f"Arquivo dividido em {len(partes)} partes."

def testar_upload_simulado(caminho_arquivo):
    """Simula teste de upload com diferentes configurações (mock)."""
    # Simulação: assume erro se página > 100000000
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            linhas = f.readlines()
        num_paginas = len(linhas)  # Simulação simplificada
        if num_paginas > 100000000:
            return False, f"Erro simulado: Página {num_paginas} excede limite."
        return True, "Upload simulado bem-sucedido."
    except Exception as e:
        return False, f"Erro no upload simulado: {str(e)}"

def gerar_relatorio(caminho_arquivo):
    """Gera relatório de diagnóstico completo."""
    relatorio = f"Relatório de Diagnóstico para {caminho_arquivo}\n\n"
    
    # Verificar integridade
    ok, msg = verificar_integridade_arquivo(caminho_arquivo)
    relatorio += f"Integridade: {msg}\n"
    if not ok:
        return relatorio + "\nCorreção sugerida: Verifique o arquivo e tente novamente.\n"
    
    # Validar encoding
    ok, msg = validar_encoding(caminho_arquivo)
    relatorio += f"Encoding: {msg}\n"
    if not ok:
        relatorio += "Correção sugerida: Converta o arquivo para UTF-8 usando ferramentas como iconv.\n"
    
    # Dividir se grande
    partes, msg = dividir_arquivo_grande(caminho_arquivo)
    relatorio += f"Divisão: {msg}\n"
    if len(partes) > 1:
        relatorio += "Correção sugerida: Use as partes divididas para upload.\n"
    
    # Testar upload
    for parte in partes:
        ok, msg = testar_upload_simulado(parte)
        relatorio += f"Teste de upload para {parte}: {msg}\n"
        if not ok:
            relatorio += "Correção sugerida: Reduza o tamanho do arquivo ou ajuste configurações de chunking no RAGFlow.\n"
    
    relatorio += "\nPossíveis causas do erro no RAGFlow:\n"
    relatorio += "1. Arquivo corrompido: Verificado acima.\n"
    relatorio += "2. Encoding incorreto: Verificado acima.\n"
    relatorio += "3. Arquivo muito grande: Dividido se necessário.\n"
    relatorio += "4. Configuração de chunking: Teste com partes menores.\n"
    relatorio += "5. Falta de dependências: Verifique instalação do RAGFlow v0.24.0.\n"
    
    return relatorio

# Exemplo de uso
if __name__ == "__main__":
    caminho = input("Digite o caminho do arquivo: ")
    print(gerar_relatorio(caminho))