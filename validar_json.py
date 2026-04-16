# Teste rápido
import json

with open('data/atos_completos.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    
print(f"Total de atos: {data['total_atos']}")
print(f"Categorias: {len(data['categorias'])}")

for cat in data['categorias']:
    print(f"  - {cat['titulo']}: {len(cat['atos'])} atos")
    for ato in cat['atos'][:1]:  # Verifica primeiro ato
        print(f"    Tamanho do conteúdo: {len(ato.get('conteudo_texto', ''))} caracteres")