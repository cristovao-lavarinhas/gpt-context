# Local Documents (Offline RAG)

Put your local files in this folder so the chatbot can retrieve context without using the internet.

Supported file types:

- `.txt`
- `.md`
- `.json`
- `.jsonl`
- `.pdf` (if `pdf-parse` is available in dependencies)
- `.csv`
- `.tsv`
- `.html`
- `.htm`
- `.xml`
- `.yaml`
- `.yml`
- `.rtf`

Examples:

- Competition regulations PDFs
- Official rulebooks exported as HTML or XML
- Event operation checklists in text or Markdown files
- Structured reference tables in CSV or TSV

Recommended structure:

- `local-docs/f1/` for Formula 1 documents
- `local-docs/futebol/` for football documents
- `local-docs/tenis/` for tennis documents
- `local-docs/eventos/` for event operations

This folder is read only from local disk by the backend.
No network request is performed by this RAG layer.

If you have Word files, export them to PDF, TXT, HTML, or XML before placing them here.

Uploaded files from the chat are handled separately from this folder, but they follow the same local-only rules.
