📋 Resumo Executivo - Pipeline ANVISA → RAGFlow  

🎯 ObjetivoAutomatizar coleta, processamento e envio de documentos ANVISA para RAGFlow em 4 etapas.  

Passo 1: Setup (5 minutos)
```
# Clonar/preparar projeto
cd anvisa_ragflow_pipeline

# Criar ambiente virtual (recomendado)
python3 -m venv .venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências

pip install selenium requests python-dotenv webdriver-manager
# Ou usar requirements.txt
pip install -r requirements.txt

# Configurar credenciais
cp .env.example .env
# Editar .env com suas chaves
```
Passo 2: Validar (2 minutos)  
```
python diagnostico_ragflow.py
# Deve retornar: ✅ Tudo OK 
```

Passo 3: Executar (2-5 horas)
 ```
 python orquestrador.py
# Executa todas as 4 etapas automaticamente
```

✅ Checklist de Execução  
    Ambiente virtual criado  
    Dependências instaladas  
    .env configurado com credenciais  
    Conexão RAGFlow testada  
    Orquestrador executado  
    Logs monitorados  
    PDFs verificados em RAGFlow  


📞 Próximos Passos

Agora: Executar python orquestrador.py  
Monitorar: tail -f logs/orquestrador.log  
Verificar: Acessar http://localhost:9380 → Datasets → Documentos  

Status: ✅ Pronto para Execução  
Tempo Total: ~2-5 horas  
Complexidade: Média  
Suporte: Verifique logs/ em caso de erro