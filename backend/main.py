"""
SportSphere — FastAPI backend.
Run with:  uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import json

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, HTTPException
import docs_manager

import rag
import storage
from file_extraction import extract_text_from_upload

app = FastAPI(title="SportSphere API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]          # full conversation so far, including the new user message
    chat_id: int | None = None       # None = new chat
    uploaded_file_content: str = ""


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"ollama_available": rag.check_model_status(), "model": rag.OLLAMA_MODEL}


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

@app.get("/api/history")
def get_history():
    return storage.list_history()


@app.delete("/api/history/{chat_id}")
def delete_history(chat_id: int):
    return storage.delete_chat(chat_id)


# ---------------------------------------------------------------------------
# File upload
# ---------------------------------------------------------------------------

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    content_bytes = await file.read()
    extracted = extract_text_from_upload(file.filename, content_bytes)
    return {"filename": file.filename, "content": extracted}


# ---------------------------------------------------------------------------
# Document library — manage local-docs/ from the UI
# ---------------------------------------------------------------------------

@app.get("/api/docs")
def get_docs_library():
    return docs_manager.list_library()


@app.post("/api/docs/folders")
def create_doc_folder(payload: dict):
    name = payload.get("name", "")
    try:
        folder = docs_manager.create_folder(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return folder


@app.delete("/api/docs/folders/{folder}")
def delete_doc_folder(folder: str):
    try:
        docs_manager.delete_folder(folder)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"deleted": True}


@app.post("/api/docs/{folder}/upload")
async def upload_doc(folder: str, file: UploadFile = File(...)):
    content = await file.read()
    try:
        saved = docs_manager.save_file(folder, file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return saved


@app.delete("/api/docs/{folder}/{filename}")
def delete_doc(folder: str, filename: str):
    try:
        docs_manager.delete_file(folder, filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"deleted": True}

# ---------------------------------------------------------------------------
# Chat — streams the assistant's reply as Server-Sent Events
# ---------------------------------------------------------------------------

@app.post("/api/chat")
def chat(req: ChatRequest):
    messages = [m.dict() for m in req.messages]
    user_message = messages[-1]["content"] if messages else ""

    system_prompt, scoped_folders, used_sources, source_excerpts = rag.build_system_prompt(
        user_message, uploaded_file_content=req.uploaded_file_content
    )

    def event_stream():
        full_text = ""
        yield f"event: scope\ndata: {json.dumps({'folders': scoped_folders, 'sources': used_sources, 'excerpts': source_excerpts})}\n\n"

        try:
            for token in rag.stream_ollama_response(system_prompt, messages):
                full_text += token
                yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
        finally:
            # Guarda sempre que houver texto gerado, mesmo que o cliente
            # tenha interrompido (botão "Parar") ou a ligação tenha caído.
            if full_text:
                final_messages = messages + [{"role": "assistant", "content": full_text}]
                saved_chat = storage.upsert_chat(req.chat_id, final_messages)
                try:
                    yield f"event: done\ndata: {json.dumps({'chat_id': saved_chat['id'], 'title': saved_chat['title']})}\n\n"
                except Exception:
                    pass

    return StreamingResponse(event_stream(), media_type="text/event-stream")