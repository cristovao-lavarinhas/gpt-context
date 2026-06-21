"""
Teste rápido: confirma qual pasta (scope) e quais ficheiros o RAG escolhe
para um conjunto de perguntas, sem precisar do frontend nem do Ollama.

Como usar (dentro da pasta backend/, com o venv ativo):
    python test_scope.py
"""

import rag

perguntas = [
    "quais as regras do futebol?",
    "quantos jogadores tem uma equipa de basquetebol?",
    "quantos pontos vale um cesto de 3?",      # sem palavra-chave óbvia
    "explica o offside no futebol americano",
    "quais as regras do ténis?",
    "o que é um wicket no cricket?",
]

for pergunta in perguntas:
    system_prompt, scoped_folders, used_sources = rag.build_system_prompt(pergunta)
    print("=" * 70)
    print(f"PERGUNTA: {pergunta}")
    print(f"PASTA(S) DETETADA(S): {scoped_folders or '(nenhuma -> pesquisa em todas)'}")
    print(f"FICHEIROS USADOS: {used_sources or '(nenhum encontrado)'}")