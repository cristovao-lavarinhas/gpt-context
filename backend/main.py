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

import rag
import storage
from file_extraction import extract_text_from_upload

app = FastAPI(title="SportSphere API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
# Chat — streams the assistant's reply as Server-Sent Events
# ---------------------------------------------------------------------------

@app.post("/api/chat")
def chat(req: ChatRequest):
    messages = [m.dict() for m in req.messages]
    user_message = messages[-1]["content"] if messages else ""

    system_prompt, scoped_folders = rag.build_system_prompt(
        user_message, uploaded_file_content=req.uploaded_file_content
    )

    def event_stream():
        full_text = ""
        # Tell the frontend which local-docs scope is active for this turn,
        # so the UI can show e.g. "a consultar: soccer/"
        yield f"event: scope\ndata: {json.dumps({'folders': scoped_folders})}\n\n"

        for token in rag.stream_ollama_response(system_prompt, messages):
            full_text += token
            yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"

        final_messages = messages + [{"role": "assistant", "content": full_text}]
        saved_chat = storage.upsert_chat(req.chat_id, final_messages)
        yield f"event: done\ndata: {json.dumps({'chat_id': saved_chat['id'], 'title': saved_chat['title']})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
