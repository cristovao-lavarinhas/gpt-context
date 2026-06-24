# Documentos Locais (RAG Offline)

Coloca aqui os teus ficheiros para que o chatbot possa responder com base
neles, sem aceder à internet.

## Tipos de ficheiro suportados

- `.pdf`
- `.docx`
- `.txt`, `.md`
- `.csv`, `.tsv`
- `.json`, `.jsonl`
- `.html`, `.htm`
- `.xml`
- `.yaml`, `.yml`
- `.rtf`
- Imagens (`.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`) — via OCR

## Estrutura de pastas

A pasta está organizada por desporto. O backend deteta automaticamente
qual a pasta a consultar com base no desporto mencionado na pergunta:

```
local-docs/
├── basketball/
├── formula1/
├── nfl/
├── olympics/
├── soccer/
├── tennis/
└── voleibol/
```

Podes criar pastas adicionais diretamente pela UI da app (página "Documentos").
As 7 pastas originais não podem ser apagadas — estão ligadas à deteção
automática de desporto.

## Exemplos de conteúdo útil

- Regulamentos oficiais em PDF
- Livros de regras exportados como HTML ou XML
- Tabelas de referência em CSV ou TSV
- Notas e resumos em Markdown

## Notas

- Se tiveres ficheiros Word (`.docx`), podes colocá-los diretamente — são
  suportados. Não precisas de exportar para PDF.
- Os ficheiros enviados pelo chat (uploads) são processados separadamente
  e não ficam guardados nesta pasta.
- Nenhum pedido de rede é feito por esta camada de RAG — tudo é local.
- Limite de 5MB por ficheiro nos uploads via chat.