# SportSphere — React + Python

Mesma lógica (RAG sobre `local-docs/`, deteção de desporto, chamadas ao Ollama)
que tinhas no `streamlit_app.py`, agora dividida em:

- **`backend/`** — FastAPI. Toda a lógica de Python (RAG, scoring, histórico,
  extração de ficheiros) foi portada quase 1:1 de `streamlit_app.py`.
- **`frontend/`** — React (Vite). UI nova, com streaming em tempo real.
- **`local-docs/`** — os teus documentos locais (mesma estrutura de sempre:
  `soccer/`, `basketball/`, `nfl/`, `tennis/`, `cricket/`, `formula1/`, `olympics/`).

## 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # ajusta OLLAMA_MODEL / LOCAL_DOCS_PATH se preciso

uvicorn main:app --reload --port 8000
```

Confirma que está no ar: `http://127.0.0.1:8000/api/health`

## 2. Frontend

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173`.

## 3. Garantir que o Ollama está a correr

```bash
ollama serve
ollama pull qwen2.5:3b
```

## Estrutura

```
sportsphere/
├── backend/
│   ├── main.py            # endpoints FastAPI (chat SSE, histórico, upload, health)
│   ├── rag.py              # RAG, scoring, system prompt, streaming Ollama
│   ├── file_extraction.py  # PDF / DOCX / OCR de imagens (uploads do utilizador)
│   ├── storage.py          # histórico de conversas em chat_history.json
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── api.js                 # fetch + parsing do streaming SSE
│       └── components/
│           ├── Sidebar.jsx/css     # nova conversa, histórico, apagar
│           ├── Welcome.jsx/css     # cartões de sugestão
│           └── ChatPanel.jsx/css   # mensagens, "scope chip", input
└── local-docs/             # os teus documentos (mesma estrutura de sempre)
```

## Notas

- O streaming usa **Server-Sent Events** (`text/event-stream`) — o texto
  aparece token a token, como no Streamlit.
- A "scope chip" (barra por cima do input) mostra em tempo real qual a
  pasta de `local-docs` ativa para a pergunta (auto-detetada pelo desporto,
  ou via `[folders: soccer]` na mensagem).
- O histórico continua a ser guardado em `backend/chat_history.json`
  (mesmo formato de antes).
- CORS já está configurado no backend para aceitar `http://localhost:5173`.
