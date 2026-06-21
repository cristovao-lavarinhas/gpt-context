"""
Testa as 4 perguntas das caixas de sugestão do Welcome.jsx contra os
documentos REAIS em local-docs/, mostrando não só a pasta detetada
mas também um excerto do melhor chunk encontrado — para confirmar se
a pergunta tem mesmo resposta nos ficheiros que existem.

Correr dentro de backend/:
    python test_welcome_prompts.py
"""

import rag

prompts = [
    "Quais são as principais regras do basquetebol da NBA e da FIBA?",
    "Explica como funcionam os torneios Grand Slam de ténis.",
    "Quais são os recordes mundiais de atletismo mais recentes?",
    "Explica o significado das bandeiras e os tipos de pneus na Fórmula 1.",
]

for p in prompts:
    print("=" * 70)
    print(f"PERGUNTA: {p}")
    system_prompt, scoped_folders, used_sources = rag.build_system_prompt(p)
    print(f"PASTA(S): {scoped_folders}")
    print(f"FICHEIROS: {used_sources}")

    chunks = rag.get_local_rag_context(p, max_chunks=2, subfolders=scoped_folders)
    if not chunks:
        print("⚠️  NENHUM CHUNK RELEVANTE ENCONTRADO — esta pergunta provavelmente",
              "vai resultar em 'Não encontrei essa informação nos meus ficheiros locais.'")
    else:
        for c in chunks:
            print(f"\n  [score={c['score']:.3f}] {c['source']}")
            print(f"  {c['text'][:300]}...")