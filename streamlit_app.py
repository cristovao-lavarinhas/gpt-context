"""
SportSphere – Streamlit Interface
Ported from the Next.js / TypeScript implementation.
Connects to a local Ollama instance for LLM inference.
"""

import base64
import math
import os
import re
import unicodedata
from pathlib import Path
import json
import time

import requests
import streamlit as st
import io

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None

try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PILImage = None
    PIL_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None
    TESSERACT_AVAILABLE = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
LOCAL_RAG_STRICT_ONLY = os.getenv("LOCAL_RAG_STRICT_ONLY", "true").lower() != "false"
LOCAL_DOCS_SUBFOLDERS = os.getenv("LOCAL_DOCS_SUBFOLDERS", "")
LOCAL_DOCS_PATH = os.getenv("LOCAL_DOCS_PATH", "local-docs")

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp",
}

SUPPORTED_EXTENSIONS = {
    ".txt", ".md", ".json", ".jsonl", ".csv", ".tsv",
    ".html", ".htm", ".xml", ".yaml", ".yml", ".rtf",
    ".pdf",
} | IMAGE_EXTENSIONS

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150

# ---------------------------------------------------------------------------
# Sports regulations
# ---------------------------------------------------------------------------

SPORTS_REGULATIONS: dict[str, list[str]] = {
    "Soccer": [
        "Cada equipa tem 11 jogadores em campo.",
        "Duração do jogo: 2 tempos de 45 minutos.",
        "A bola entra na baliza = golo (1 ponto).",
        "Regra do fora-de-jogo (offside): não há jogador atacante mais perto da linha de baliza que a bola e dois adversários.",
        "Cartão amarelo = aviso; cartão vermelho = expulsão.",
        "Faltas e contacto: o árbitro aplica penalidades (penáltis, livres indiretos/diretos).",
        "Sem contato de mão/braço na área (exceto guarda-redes).",
    ],
    "Basketball": [
        "Duas equipas de 5 jogadores cada.",
        "Duração: 4 períodos de 12 minutos (NBA) ou 10 minutos (FIBA).",
        "Cesto = 2 pontos; lançamento de 3 = 3 pontos; lançamento livre = 1 ponto.",
        "Regra de posse de bola: 24 segundos (NBA) ou 14 segundos (FIBA).",
        "Falta: máximo 6 faltas por jogador; 5ª falta = expulsão.",
        "Viagem (travel): avançar mais de 2 passos sem driblage = perda de posse.",
        "Zona restrita: não pode ficar más de 3 segundos na área defensiva sem bola.",
    ],
    "Football": [
        "Dois tempos de 15 minutos (NFL).",
        "Touchdown = 6 pontos; field goal = 3 pontos; safety = 2 pontos.",
        "Primeira descida (first down): avançar 10 jardas.",
        "Cada equipa tem 4 tentativas para conseguir primeira descida.",
        "Fora-de-jogo: linha de scrimmage.",
        "Fumble: bola cai = posse disputa.",
        "Sack: derrota do quarterback = perda de jardas.",
    ],
    "Tennis": [
        "Pontuação: 0 (love), 15, 30, 40, jogo.",
        "Set: primeiro a ganhar 6 games (com diferença de 2).",
        "Match: melhor de 3 ou 5 sets.",
        "Deuce: 40-40; precisa vencer 2 pontos seguidos (advantage + game).",
        "Saque: 2 tentativas; falha = ponto para adversário.",
        "Net: se bola toca a rede mas cai do outro lado = joga ponto.",
        "Let: saque toca a rede mas cai válido = repete saque.",
    ],
    "Cricket": [
        "Batsman vs Bowler (lançador).",
        "Wicket: 3 paus de madeira; derrubar = derrotar batsman.",
        "Runs: correr entre wickets; cada corrida = 1 ponto.",
        "Over: 6 lançamentos = completa 1 over.",
        "Innings: turno de batida (batsman + suportes).",
        "LBW (leg before wicket): corpo bloqueia bola que iria atingir wicket.",
        "Boundary: bola cruza limite sem bater = 4 ou 6 runs automáticos.",
    ],
}

SOURCES_REFERENCES: dict[str, str] = {
    "Soccer":     "FIFA (Federação Internacional de Futebol); Regulamentos Oficiais 2024-2025",
    "Basketball": "NBA (National Basketball Association) & FIBA (Federação Internacional de Basquete)",
    "Football":   "NFL (National Football League) Official Rulebook; 2024 Season Edition",
    "Tennis":     "ITF (International Tennis Federation) Rules of Tennis; ATP Professional Tour",
    "Cricket":    "ICC (International Cricket Council) Laws of Cricket 2024; Official Handbook",
}

# ---------------------------------------------------------------------------
# Sport keywords — used for detection AND folder auto-scoping
# ---------------------------------------------------------------------------

SPORT_KEYWORDS: list[dict] = [
    {
        "name": "Soccer",
        "keywords": [
            "soccer", "football", "futebol", "champions league", "premier league",
            "la liga", "serie a", "mundial", "world cup", "copa", "fifa", "fwc",
            "campeonato do mundo", "copa do mundo",
        ],
    },
    {
        "name": "Basketball",
        "keywords": ["basketball", "nba", "basquetebol", "basquete", "fiba"],
    },
    {
        "name": "Football",
        "keywords": [
            "american football", "nfl", "football americano", "touchdown", "superbowl",
        ],
    },
    {
        "name": "Tennis",
        "keywords": [
            "tennis", "atp", "wta", "tenis", "grand slam", "wimbledon", "roland garros",
        ],
    },
    {
        "name": "Cricket",
        "keywords": ["cricket", "ipl"],
    },
    {
        "name": "Formula1",
        "keywords": ["formula 1", "formula1", "f1", "fia", "grand prix", "gp", "formula um"],
    },
    {
        "name": "Olympics",
        "keywords": [
            "olympics", "atletismo", "athletics", "olimpiadas", "jogos olimpicos",
            "usain bolt", "sprint", "maratona",
        ],
    },
]

# Maps sport name → local-docs subfolder name
SPORT_FOLDER_MAP: dict[str, str] = {
    "Soccer":     "soccer",
    "Basketball": "basketball",
    "Football":   "nfl",
    "Tennis":     "tennis",
    "Cricket":    "cricket",
    "Formula1":   "formula1",
    "Olympics":   "olympics",
}

# ---------------------------------------------------------------------------
# Local RAG
# ---------------------------------------------------------------------------

def _normalize_text(value: str) -> str:
    """Lowercase, strip accents, keep only alphanum + spaces."""
    value = value.lower()
    value = unicodedata.normalize("NFD", value)
    value = re.sub(r"[\u0300-\u036f]", " ", value)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _tokenize(value: str) -> set[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return set()
    return {w for w in normalized.split(" ") if len(w) >= 2 or any(char.isdigit() for char in w)}


def _to_bigrams(tokens: list[str]) -> set[str]:
    return {f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)}


def _chunk_text(text: str) -> list[str]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    output: list[str] = []
    cursor = 0
    while cursor < len(clean):
        end = min(len(clean), cursor + CHUNK_SIZE)
        chunk = clean[cursor:end].strip()
        if chunk:
            output.append(chunk)
        if end >= len(clean):
            break
        cursor = max(0, end - CHUNK_OVERLAP)
    return output


def _list_files_recursive(root: Path) -> list[Path]:
    files: list[Path] = []
    if not root.is_dir():
        return files
    for entry in root.rglob("*"):
        if entry.is_file():
            files.append(entry)
    return files


def _read_file_as_text(filepath: Path) -> str:
    if filepath.suffix.lower() == ".pdf":
        if pypdf is None:
            return ""
        try:
            reader = pypdf.PdfReader(str(filepath))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""
    try:
        return filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _index_local_docs(docs_root: Path) -> list[dict]:
    all_files = _list_files_recursive(docs_root)
    local_files = [f for f in all_files if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    chunks: list[dict] = []
    for filepath in local_files:
        if filepath.stat().st_size > MAX_FILE_SIZE_BYTES:
            continue
        content = _read_file_as_text(filepath)
        file_chunks = _chunk_text(content)
        relative = filepath.relative_to(docs_root).as_posix()
        for text in file_chunks:
            tokens = _tokenize(text)
            if not tokens:
                continue
            chunks.append({
                "source": relative,
                "text": text,
                "tokens": tokens,
                "source_tokens": _tokenize(relative),
            })
    return chunks


def _score_chunk(
    query_text: str,
    query_tokens: set[str],
    chunk_tokens: set[str],
    source_tokens: set[str],
) -> float:
    if not query_tokens or not chunk_tokens:
        return 0.0
    overlaps = len(query_tokens & chunk_tokens)
    coverage = overlaps / len(query_tokens)
    if coverage == 0:
        return 0.0
    lexical_score = overlaps / math.sqrt(len(query_tokens) * len(chunk_tokens))
    query_bigrams = _to_bigrams(list(query_tokens))
    chunk_bigrams = _to_bigrams(list(chunk_tokens))
    bigram_hits = len(query_bigrams & chunk_bigrams)
    bigram_score = bigram_hits / len(query_bigrams) if query_bigrams else 0.0
    source_hits = len(query_tokens & source_tokens)
    source_score = source_hits / max(len(query_tokens), 1)
    normalized_query = _normalize_text(query_text)
    exact_bonus = 0.1 if normalized_query in " ".join(sorted(chunk_tokens)) else 0.0
    return (
        lexical_score * 0.65
        + coverage * 0.15
        + bigram_score * 0.15
        + source_score * 0.05
        + exact_bonus
    )


@st.cache_data(ttl=60, show_spinner=False)
def _get_indexed_chunks(docs_path_str: str) -> list[dict]:
    """Index the local documents. Cached with 60s TTL."""
    docs_path = Path(docs_path_str)
    if not docs_path.is_dir():
        return []
    
    # Primeiro crias a variável
    indexed = _index_local_docs(docs_path)
    
    # SÓ DEPOIS podes fazer o print
    print(f"DEBUG: Foram carregados {len(indexed)} pedaços de texto.") 
    
    return indexed


def _sanitize_subfolder(value: str) -> str:
    return value.strip().replace("\\", "/").strip("/").lower()


def _file_matches_subfolders(relative_path: str, subfolders: list[str]) -> bool:
    if not subfolders:
        return True
    src = relative_path.lower()
    return any(src == sf or src.startswith(sf + "/") for sf in subfolders)


def get_local_rag_context(
    user_message: str,
    max_chunks: int = 10,  # Aumentado para 10 para dar mais margem a docs bilingues
    subfolders: list[str] | None = None,
) -> list[dict]:
    # 1. Configuração de caminhos (inalterado)
    configured = LOCAL_DOCS_PATH
    if not os.path.isabs(configured):
        configured = os.path.join(os.path.dirname(os.path.abspath(__file__)), configured)
    
    indexed = _get_indexed_chunks(configured)
    if not indexed:
        return []

    # 2. Expansão Bilingue da Query
    # Obtemos a versão inglesa da pergunta
    translated_query = translate_query_for_rag(user_message)
    
    # Geramos os tokens de ambos os idiomas
    query_tokens_pt = _tokenize(user_message)
    query_tokens_en = _tokenize(translated_query) if translated_query else set()
    
    # UNIMOS os tokens: a busca agora vai encontrar "futebol" E "football"
    combined_tokens = query_tokens_pt | query_tokens_en
    
    # 3. Filtragem de Subpastas (inalterado)
    clean_subfolders = [_sanitize_subfolder(s) for s in (subfolders or []) if s.strip()]
    scoped = [c for c in indexed if _file_matches_subfolders(c["source"], clean_subfolders)]
    
    # 4. Ranking com Pontuação Cruzada
    ranked = []
    for chunk in scoped:
        # Usamos os tokens combinados para pontuar contra o texto do chunk
        score = _score_chunk(
            user_message, 
            combined_tokens, 
            chunk["tokens"], 
            chunk["source_tokens"]
        )
        
        if score > 0:
            ranked.append({
                "source": chunk["source"], 
                "text": chunk["text"], 
                "score": score
            })
    # Ordenar por maior relevância
    ranked.sort(key=lambda x: x["score"], reverse=True)
    
    return ranked[:max_chunks]
# ---------------------------------------------------------------------------
# File Parsing (User Uploads)
# ---------------------------------------------------------------------------

def extract_text_from_image(image_bytes: bytes, filename: str) -> str:
    """Extract text from an image using pytesseract OCR or Ollama vision fallback."""
    ext = Path(filename).suffix.lower().lstrip(".")
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    # ── Priority 1: Tesseract OCR (offline, local, fastest) ──────────────────
    if TESSERACT_AVAILABLE and PIL_AVAILABLE and PILImage is not None:
        try:
            img = PILImage.open(io.BytesIO(image_bytes))
            
            # Resize if too large
            max_size = 2000
            if img.width > max_size or img.height > max_size:
                ratio = min(max_size / img.width, max_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, PILImage.Resampling.LANCZOS)
            
            # Try with language optimization for sports documents
            text = pytesseract.image_to_string(img, lang="por+eng")
            
            if text.strip():
                clean_text = text.strip()
                return f"[OCR via Tesseract — {filename}]\n{clean_text}"
        except Exception as e:
            print(f"Tesseract OCR failed: {e}")
            pass  # fall through to Ollama vision

    # ── Priority 2: Ollama vision model ──────────────────────────────────────
    if OLLAMA_MODEL:
        try:
            img_b64 = base64.b64encode(image_bytes).decode("utf-8")
            resp = requests.post(
                f"{OLLAMA_BASE_URL}/v1/chat/completions",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": (
                                "Transcribe EVERY visible text in this image exactly as written. "
                                "Maintain formatting, line breaks, and structure. "
                                "Output ONLY the extracted text, nothing else."
                            )},
                            {"type": "image_url", "image_url": {
                                "url": f"data:{mime};base64,{img_b64}"
                            }},
                        ],
                    }],
                    "temperature": 0,
                    "max_tokens": 2048,
                },
                timeout=60,
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip()
                if content and len(content) > 5:  # Avoid empty/trivial responses
                    return f"[OCR via Vision Model (Ollama) — {filename}]\n{content}"
        except Exception as e:
            print(f"Ollama vision OCR failed: {e}")
            pass

    # ── Priority 3: Graceful failure with helpful instructions ───────────────
    return (
        f"⚠️ Não foi possível extrair texto da imagem '{filename}'.\n\n"
        "**Soluções:**\n"
        "1. **Instala o Tesseract OCR** (recomendado):\n"
        "   - Download: https://github.com/UB-Mannheim/tesseract/wiki\n"
        "   - Depois: `pip install pytesseract`\n\n"
        "2. **Usa um modelo Ollama com visão** (ex: `llava`):\n"
        "   - `ollama pull llava`\n"
        "   - Configura `OLLAMA_MODEL=llava` no `.env`"
    )


def extract_text_from_upload(uploaded_file) -> str:
    """Extract text from various file formats uploaded by the user."""
    if not uploaded_file:
        return ""
    
    ext = Path(uploaded_file.name).suffix.lower()
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    
    # Check file size
    if file_size_mb > 5:
        return f"❌ Ficheiro muito grande: {file_size_mb:.1f}MB. Máximo permitido: 5MB."
    
    try:
        if ext == ".pdf":
            if pypdf is None:
                return "❌ Erro: pypdf não instalado. Não posso ler PDFs. Execute: `pip install pypdf`"
            pdf_reader = pypdf.PdfReader(io.BytesIO(uploaded_file.getvalue()))
            if not pdf_reader.pages:
                return "⚠️ PDF vazio ou corrompido."
            text = ""
            for i, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"[Página {i+1}]\n{page_text}\n"
            return text if text.strip() else "⚠️ Nenhum texto extraído do PDF."
        
        elif ext == ".docx":
            if docx is None:
                return "❌ Erro: python-docx não instalado. Não posso ler ficheiros Word. Execute: `pip install python-docx`"
            doc = docx.Document(io.BytesIO(uploaded_file.getvalue()))
            text_parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)
            text = "\n".join(text_parts)
            return text if text.strip() else "⚠️ Nenhum texto extraído do documento Word."
        
        elif ext in [".txt", ".md", ".csv", ".json", ".jsonl"]:
            text = uploaded_file.getvalue().decode("utf-8", errors="ignore")
            return text if text.strip() else "⚠️ Ficheiro de texto vazio."
        
        elif ext in IMAGE_EXTENSIONS:
            return extract_text_from_image(uploaded_file.getvalue(), uploaded_file.name)
        
        else:
            return f"❌ Formato de ficheiro não suportado: {ext}. Formatos aceitos: PDF, DOCX, TXT, MD, CSV, JSON, PNG, JPG, GIF, BMP, TIFF."
    
    except Exception as e:
        return f"❌ Erro ao processar ficheiro: {str(e)}"


# ---------------------------------------------------------------------------
# Sport detection
# ---------------------------------------------------------------------------

def _detect_sport(user_message: str) -> dict | None:
    lower = user_message.lower()
    for sport in SPORT_KEYWORDS:
        if any(kw in lower for kw in sport["keywords"]):
            return sport
    return None


def _parse_folders_from_message(user_message: str) -> list[str]:
    results: set[str] = set()
    bracket = re.search(r"\[folders?:([^\]]+)\]", user_message, re.IGNORECASE)
    inline = re.search(r"(?:pasta|folder):\s*([a-zA-Z0-9_\-/, ]+)", user_message, re.IGNORECASE)
    for match in [bracket, inline]:
        if match:
            for part in match.group(1).split(","):
                part = part.strip().replace("\\", "/")
                if part:
                    results.add(part)
    return list(results)


def _parse_folders_from_env() -> list[str]:
    return [s.strip().replace("\\", "/") for s in LOCAL_DOCS_SUBFOLDERS.split(",") if s.strip()]


def _trim_text(value: str, max_len: int = 450) -> str:
    return value[:max_len] + "..." if len(value) > max_len else value


# ---------------------------------------------------------------------------
# Translation for RAG query expansion
# ---------------------------------------------------------------------------

def translate_query_for_rag(user_query: str) -> str:
    """Traduz a query para inglês via Ollama para expandir a busca no RAG."""
    translation_prompt = f"Translate the following sports query to English. Output ONLY the translation: {user_query}"
    
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/v1/chat/completions",
            json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": f"Translate to English: {user_query}"}],
                "temperature": 0,
                "max_tokens": 50,
                "options": {
                    "stop": ["\n", "Translation:", "Aqui está"]
                }
            },
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except:
        pass
    return "" # Falha silenciosa

# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

def build_system_prompt(user_message: str, all_messages: list[dict]) -> str:
    league = _detect_sport(user_message)
    regulations = SPORTS_REGULATIONS.get(league["name"], []) if league else []

    # Folder scoping: message override > env var > auto-detect from sport keyword
    requested_folders = _parse_folders_from_message(user_message)
    configured_folders = _parse_folders_from_env()
    auto_folder = (
        [SPORT_FOLDER_MAP[league["name"]]]
        if league and league["name"] in SPORT_FOLDER_MAP
        else []
    )
    scoped_folders = requested_folders or configured_folders or auto_folder

    # RAG retrieval — 6 chunks to cover large PDFs
    rag_chunks = get_local_rag_context(
        user_message,
        max_chunks=10,
        subfolders=scoped_folders,
    )

    # RAG block
    if rag_chunks:
        rag_block = "\n\nLOCAL DOCUMENT CONTEXT (RAG):\n" + "\n".join(
            f"{i+1}. {_trim_text(c['text'], 700)}"
            for i, c in enumerate(rag_chunks)
        )
    else:
        rag_block = (
            "\n\nLOCAL DOCUMENT CONTEXT (RAG):\n"
            "- No matching local documents found for this question."
        )

    # Uploaded file block
    upload_block = ""
    if st.session_state.get("uploaded_file_content"):
        upload_block = (
            "\n\nUSER UPLOADED FILE CONTEXT:\n"
            "The user uploaded a file with the following content. "
            "Use it if relevant to the query:\n"
            f"---\n{_trim_text(st.session_state.uploaded_file_content, 8000)}\n---"
        )

    # Hardcoded regulations — only used as a last resort when RAG found nothing
    reg_snippet = ""
    if regulations and not rag_chunks:
        reg_snippet = (
            f"\n\nOFFICIAL REGULATIONS — FALLBACK ({league['name']}):\n"
            + "\n".join(f"{i+1}. {r}" for i, r in enumerate(regulations[:3]))
        )

    # Strict vs open mode
    if LOCAL_RAG_STRICT_ONLY:
        strict_note = (
            "\n\nMODE: STRICT — answer only from the LOCAL DOCUMENT CONTEXT or "
            "USER UPLOADED FILE CONTEXT above. If the answer is not there, "
            'reply exactly: "Não encontrei essa informação nos meus ficheiros locais."'
        )
    else:
        strict_note = (
            "\n\nMODE: OPEN — prefer local context, but you may use general "
            "knowledge when local context is insufficient."
        )

    scope_note = (
        "\n\nACTIVE FOLDER SCOPE: "
        + (", ".join(scoped_folders) if scoped_folders else "all")
    )

    return f"""You are SportSphere, an AI sports assistant. You answer questions based on the documents provided below.

RULES:
1. Use ONLY the facts in LOCAL DOCUMENT CONTEXT or USER UPLOADED FILE CONTEXT to answer.
2. If the answer is not present, reply exactly: "Não encontrei essa informação nos meus ficheiros locais."
3. Be concise, direct, and clear.
4. Do NOT mention file names, file paths, chunk numbers, or internal variables.
5. Do NOT say "According to the local documents" or "Based on the files" — give the answer naturally.
6. Do NOT invent or guess information not found in the provided context.
7. Answer in the same language the user wrote in (Portuguese if they write in Portuguese).
{strict_note}{scope_note}

CONTEXT DATA:
{rag_block}{upload_block}{reg_snippet}"""


# ---------------------------------------------------------------------------
# Ollama streaming call
# ---------------------------------------------------------------------------

def stream_ollama_response(system_prompt: str, messages: list[dict]):
    """Generator that yields text chunks from Ollama streaming response."""
    ollama_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        ollama_messages.append({"role": msg["role"], "content": msg["content"]})

    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/v1/chat/completions",
            json={
                "model": OLLAMA_MODEL,
                "messages": ollama_messages,
                "stream": True,
                "temperature": 0 if LOCAL_RAG_STRICT_ONLY else 0.7,
                "max_tokens": 512,
            },
            stream=True,
            timeout=300,
        )
        resp.raise_for_status()

        for line_bytes in resp.iter_lines():
            if not line_bytes:
                continue
            line = line_bytes.decode("utf-8", errors="replace")
            if line.startswith("data: "):
                line = line[6:]
            if line.strip() == "[DONE]":
                break
            try:
                data = json.loads(line)
                delta = data.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content
            except Exception:
                continue

    except requests.exceptions.ConnectionError:
        yield "⚠️ Não foi possível conectar ao Ollama. Certifica-te de que o Ollama está a correr em `http://127.0.0.1:11434`."
    except requests.exceptions.ReadTimeout:
        yield "⚠️ O Ollama excedeu o limite de tempo (Timeout de 5 minutos). O teu computador pode estar a demorar muito a ler os ficheiros."
    except Exception as e:
        yield f"⚠️ Erro ao comunicar com o Ollama: {e}"


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def load_logo_as_base64() -> str | None:
    logo_path = Path(__file__).parent / "public" / "SportSphere.png"
    if logo_path.exists():
        data = logo_path.read_bytes()
        return base64.b64encode(data).decode("utf-8")
    return None


def render_architecture_tab():
    """Render the system architecture view with a visual diagram using Markdown."""
    
    st.markdown("# ⚙️ Arquitetura do Sistema")
    st.markdown("**SportSphere** — Assistente Desportivo com RAG Local")
    st.divider()
    
    # Layer 1
    st.markdown("## 📱 Interface do Utilizador")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 💬 Chat Interface")
        st.write("• Input de texto com streaming  \n• Histórico persistente em JSON  \n• Sugestões contextuais inteligentes")
    with col2:
        st.markdown("### 📎 Upload de Ficheiros")
        st.write("• PDF, DOCX, TXT, CSV, JSON  \n• Imagens (PNG, JPG, GIF, TIFF)  \n• OCR integrado automático")
    
    st.divider()
    
    # Layer 2
    st.markdown("## 🔄 Pipeline de Processamento")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 🔍 Deteção de Desporto")
        st.write("Keywords em PT/EN detetam o desporto e filtram a pasta correta de documentos.")
    with col2:
        st.markdown("### 🔠 OCR Engine")
        st.write("**Prioridade:**  \n1. Tesseract (offline, rápido)  \n2. Ollama Vision (local)  \n3. Mensagem de erro com instruções")
    with col3:
        st.markdown("### 📄 Parser Documentos")
        st.write("pypdf para PDFs • python-docx para Word • Leitura direta para texto/CSV")
    
    st.divider()
    
    # Layer 3
    st.markdown("## 🧠 RAG — Retrieval-Augmented Generation")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### ✂️ Chunking")
        st.write("Texto dividido em blocos de 900 caracteres com 150 de sobreposição para contexto otimizado.")
    with col2:
        st.markdown("### 🏷️ Tokenização + Scoring")
        st.write("Normalização Unicode, bigrams, cobertura léxica cruzada entre português ↔ inglês.")
    with col3:
        st.markdown("### 🌍 Tradução Bilingue")
        st.write("Query traduzida PT→EN via Ollama para expandir tokens de busca em docs ingleses.")
    
    st.divider()
    
    # Layer 4
    st.markdown("## 🤖 Geração de Resposta")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🤖 Ollama LLM (Local)")
        st.write("""
- Modelo: qwen2.5:3b (ou outro configurado)
- System prompt dinâmico com contexto RAG
- Regulamentos desportivos como fallback
- Streaming via SSE para UX fluida
""")
    with col2:
        st.markdown("### 📂 local-docs/")
        st.write("""
- soccer/ — Regras e eventos de futebol
- formula1/ — F1, pneus, estratégias
- basketball/ — NBA, FIBA, regulamentos
- tennis/ — Grand Slams, rankings
- olympics/ — Atletismo e eventos
- Indexados com cache de 60s
""")
    
    st.divider()
    
    # Tech Stack
    st.markdown("## 🛠️ Tech Stack")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.write("**Backend:**  \nPython 3.11+  \nStreamlit  \nOllama")
    with col2:
        st.write("**Document Parsing:**  \npypdf  \npython-docx  \nPillow")
    with col3:
        st.write("**OCR:**  \nTesseract  \npytesseract  \nOllama Vision")
    with col4:
        st.write("**Storage:**  \nJSON (chat history)  \nLocal-docs (offline)")
    
    st.divider()
    
    # Legend
    st.markdown("## 📌 Notas de Arquitetura")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🔒 100% Offline**  \nNenhum dado sai do computador. Tudo corre localmente via Ollama.")
        st.markdown("**📊 RAG Scoring**  \n65% similaridade léxica • 15% cobertura • 15% bigrams • 5% fonte")
    with col2:
        st.markdown("**🔠 OCR Cascata**  \nTesseract → Ollama Vision → mensagem de erro com instruções")
        st.markdown("**💾 Persistência**  \nHistórico guardado em `chat_history.json` entre sessões")


def check_model_status() -> bool:
    """Check if the Ollama model is reachable. Returns True if online."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            base_name = OLLAMA_MODEL.split(":")[0]
            return any(OLLAMA_MODEL in m or base_name in m for m in models)
        return False
    except Exception:
        return False


def main():
    st.set_page_config(
        page_title="SportSphere",
        page_icon="⚽",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        .stApp {
            background-color: #ffffff;
            font-family: "Segoe UI", "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif;
        }

        /* Use wide layout — sidebar sits beside content */
        [data-testid="stAppViewContainer"] {
            width: 100%;
            max-width: none;
            padding: 0 !important;
        }

        /* Main content block: centered within the available space */
        .block-container {
            max-width: 860px !important;
            width: 100% !important;
            margin-left: auto !important;
            margin-right: auto !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }

        /* Center tab content */
        [role="tabpanel"] {
            width: 100%;
            max-width: 100%;
            margin: 0 auto !important;
        }

        /* ── Sidebar ── */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f8f8f8 0%, #f4f4f4 100%);
            border-right: 1px solid #e8e8e8;
            width: 260px !important;
            min-width: 260px !important;
            max-width: 260px !important;
        }

        /* Collapsed sidebar: keep collapse/expand button visible and in the right place */
        section[data-testid="stSidebar"][aria-expanded="false"] {
            width: 0px !important;
            min-width: 0px !important;
            overflow: visible !important;
        }

        /* Sidebar toggle button — always pinned to left edge */
        [data-testid="stSidebarCollapsedControl"] {
            position: fixed !important;
            left: 0.5rem !important;
            top: 0.75rem !important;
            z-index: 999999 !important;
        }

        /* ═══════════════════════════════════════════════════════════
           SIDEBAR BUTTONS — base class
           Estilo comum a TODOS os botões da sidebar (todos os
           containers cuja key comece por "sb_"). Para mudar algo em
           todos de uma vez, edita aqui. Cada variante abaixo só
           define o que a torna diferente das outras.
           ═══════════════════════════════════════════════════════════ */
        section[data-testid="stSidebar"] [class*="st-key-sb_"] button {
            border-radius: 10px !important;
            cursor: pointer !important;
            transition: background 0.18s, box-shadow 0.18s, color 0.15s !important;
            box-shadow: none !important;
        }

        /* ── New Chat button ── */
        section[data-testid="stSidebar"] [class*="st-key-sb_new_chat"] button {
            border: 1px solid #e0e0e0 !important;
            background: white !important;
            color: #1a1a1a !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
            padding: 10px 16px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
        }

        section[data-testid="stSidebar"] [class*="st-key-sb_new_chat"] button:hover {
            background: #f7f7f7 !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1) !important;
        }

        /* ── Arch button ── */
        [class*="st-key-sb_arch"] button {
            border: 1px solid #e8e8e8 !important;
            background: #fafafa !important;
            color: #555 !important;
            font-size: 0.8rem !important;
            font-weight: 500 !important;
            padding: 8px 16px !important;
        }

        [class*="st-key-sb_arch"] button:hover {
            background: #f0f0f0 !important;
            color: #333 !important;
        }

        /* ── History label ── */
        .history-label {
            font-size: 0.68rem;
            font-weight: 700;
            color: #b8b8b8;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }

        /* ── Load chat button (inactive + active) ── */
        [class*="st-key-sb_loadinact_"] button,
        [class*="st-key-sb_loadact_"] button {
            width: 100% !important;
            text-align: left !important;
            border: none !important;
            border-radius: 7px !important;
            padding: 7px 10px !important;
            background: transparent !important;
            color: #4a4a4a !important;
            font-size: 0.82rem !important;
            font-weight: 400 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            line-height: 1.35 !important;
        }

        [class*="st-key-sb_loadinact_"] button:hover { background: #f0f0f0 !important; }

        [class*="st-key-sb_loadact_"] button {
            background: #e8e8e8 !important;
            color: #111 !important;
            font-weight: 600 !important;
        }

        [class*="st-key-sb_loadact_"] button:hover { background: #e2e2e2 !important; }

        /* ── Delete button ── */
        [class*="st-key-sb_del_"] button {
            background: transparent !important;
            border: none !important;
            border-radius: 5px !important;
            color: #d0d0d0 !important;
            font-size: 0.7rem !important;
            padding: 6px 4px !important;
            min-width: 0 !important;
            width: 100% !important;
        }

        [class*="st-key-sb_del_"] button:hover {
            color: #ef4444 !important;
            background: rgba(239,68,68,0.07) !important;
        }

        /* ── Remove gap between columns in sidebar history rows ── */
        section[data-testid="stSidebar"] [data-testid="column"] {
            padding-left: 0 !important;
            padding-right: 0 !important;
        }

        section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
            gap: 0 !important;
            margin-bottom: 1px !important;
        }

        .overview-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 3rem 1rem 1.5rem;
            margin-left: auto;
            margin-right: auto;
            width: 100%;
            max-width: 680px;
        }

        .overview-container img {
            max-width: 510px;
            height: auto;
            margin-bottom: 1.2rem;
            filter: drop-shadow(0 4px 12px rgba(79,70,229,0.12));
        }

        .overview-text {
            text-align: center;
            color: #666;
            font-size: 0.95rem;
            line-height: 1.65;
            max-width: 500px;
            margin: 0 auto;
        }

        .overview-text p { margin-bottom: 0.6rem; }

        /* Center suggestion buttons container */
        [data-testid="column"] {
            width: 100%;
        }
        
        .stColumn {
            text-align: center;
        }

        /* ═══════════════════════════════════════════════════════════
           CENTER PANEL BUTTONS — base class
           Estilo comum a TODOS os botões do painel central.
           Para mudar algo em todos de uma vez, edita aqui.
           As variantes (ex: .suggestion-btn) só definem o que as
           torna diferentes umas das outras.
           ═══════════════════════════════════════════════════════════ */
        /* ═══════════════════════════════════════════════════════════
           CENTER PANEL BUTTONS — base class
           Estilo comum a TODOS os botões do painel central (todos
           os containers cuja key comece por "cb_"). Para mudar algo
           em todos de uma vez, edita aqui. As variantes (ex:
           "cb_suggestion_") só definem o que as torna diferentes.
           ═══════════════════════════════════════════════════════════ */
        [class*="st-key-cb_"] button {
            border-radius: 14px !important;
            cursor: pointer !important;
            transition: all 0.18s ease !important;
        }

        [class*="st-key-cb_suggestion_"] button {
            width: 100%;
            text-align: left !important;
            border: 1px solid #ebebeb !important;
            padding: 16px 18px !important;
            background: white !important;
            color: #222 !important;
            font-size: 0.875rem !important;
            height: auto !important;
            min-height: 68px !important;
            margin: 5px 0 !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
            line-height: 1.4 !important;
        }

        [class*="st-key-cb_suggestion_"] button:hover {
            background: #fafafe !important;
            border-color: #c5c3f5 !important;
            box-shadow: 0 3px 12px rgba(79,70,229,0.1) !important;
            transform: translateY(-1px) !important;
        }

        [class*="st-key-cb_suggestion_"] button p {
            margin: 0 !important;
            text-align: left !important;
        }

        .stChatMessage {
            max-width: 860px; 
            margin: 0 auto; 
            width: 100%;
        }

        .stChatInput {
            max-width: 860px;
            margin: 0 auto !important;
            padding-bottom: 1rem;
            width: 100% !important;
            display: flex;
            justify-content: center;
        }

        [data-testid="stChatInputContainer"] {
            max-width: 860px;
            margin: 0 auto !important;
            width: 100% !important;
        }

        [data-testid="stChatInput"] {
            border-radius: 24px !important;
            border: 1px solid #e5e5e5 !important;
            background: #ffffff !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06) !important;
            padding: 6px 8px !important;
            transition: border-color 0.2s, box-shadow 0.2s !important;
        }

        [data-testid="stChatInput"]:focus-within {
            border-color: #4f46e5 !important;
            box-shadow: 0 4px 24px rgba(79, 70, 229, 0.15) !important;
        }

        .stChatInput textarea {
            border: none !important;
            background: transparent !important;
            font-size: 1rem !important;
            color: #333 !important;
            padding-top: 8px !important;
            padding-bottom: 8px !important;
            padding-left: 8px !important;
            outline: none !important;
            box-shadow: none !important;
        }

        .stChatInput textarea:focus {
            outline: none !important;
            box-shadow: none !important;
            border: none !important;
        }

        [data-testid="stChatInput"]:focus-visible,
        [data-testid="stChatInput"] *:focus-visible {
            outline: none !important;
            box-shadow: none !important;
        }

        .stChatInput button {
            background-color: #4f46e5 !important;
            color: white !important;
            border-radius: 50% !important;
            width: 36px !important;
            height: 36px !important;
            padding: 0 !important;
            margin-right: 4px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: background-color 0.2s, transform 0.1s !important;
            border: none !important;
        }

        .stChatInput button:hover {
            background-color: #4338ca !important;
            transform: scale(1.05) !important;
        }

        /* Model status badge — top right */
        .model-status-badge {
            position: fixed;
            bottom: 1rem;
            right: 1rem;
            z-index: 9999999;
            display: flex;
            align-items: center;
            gap: 6px;
            background: rgba(255,255,255,0.92);
            border: 1px solid #e5e5e5;
            border-radius: 20px;
            padding: 4px 12px 4px 8px;
            font-size: 0.78rem;
            font-weight: 500;
            color: #444;
            backdrop-filter: blur(6px);
            box-shadow: 0 1px 6px rgba(0,0,0,0.08);
            pointer-events: none;
            user-select: none;
        }

        .model-status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            flex-shrink: 0;
        }

        .model-status-dot.online  { background: #22c55e; box-shadow: 0 0 0 2px rgba(34,197,94,0.25); }
        .model-status-dot.offline { background: #ef4444; box-shadow: 0 0 0 2px rgba(239,68,68,0.25); }


    </style>
    """, unsafe_allow_html=True)

    # ---- Model status badge (top-right) ----
    model_online = check_model_status()
    dot_class = "online" if model_online else "offline"
    status_label = f"{OLLAMA_MODEL} — disponível" if model_online else f"{OLLAMA_MODEL} — indisponível"
    st.markdown(
        f'<div class="model-status-badge">'
        f'<span class="model-status-dot {dot_class}"></span>'
        f'{status_label}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ---- Persistent Memory ----
    CHAT_HISTORY_FILE = Path("chat_history.json")

    def _load_history_from_disk() -> list[dict]:
        if CHAT_HISTORY_FILE.exists():
            try:
                with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_history_to_disk(history: list[dict]):
        try:
            with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---- Session state ----
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = _load_history_from_disk()
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "uploaded_file_content" not in st.session_state:
        st.session_state.uploaded_file_content = ""
    if "uploaded_file_name" not in st.session_state:
        st.session_state.uploaded_file_name = ""

    def _get_chat_title(messages: list[dict]) -> str:
        for msg in messages:
            if msg["role"] == "user":
                text = msg["content"][:40]
                return text + ("..." if len(msg["content"]) > 40 else "")
        return "New Chat"

    def _save_current_chat():
        if not st.session_state.messages:
            return
        chat_id = st.session_state.current_chat_id
        if chat_id is not None:
            for chat in st.session_state.chat_history:
                if chat["id"] == chat_id:
                    chat["messages"] = list(st.session_state.messages)
                    chat["title"] = _get_chat_title(st.session_state.messages)
                    _save_history_to_disk(st.session_state.chat_history)
                    return
        new_id = int(time.time() * 1000)
        st.session_state.chat_history.insert(0, {
            "id": new_id,
            "title": _get_chat_title(st.session_state.messages),
            "messages": list(st.session_state.messages),
        })
        st.session_state.current_chat_id = new_id
        # Keep only the 10 most recent chats
        st.session_state.chat_history = st.session_state.chat_history[:10]
        _save_history_to_disk(st.session_state.chat_history)

    def _delete_chat(chat_id: int):
        st.session_state.chat_history = [
            c for c in st.session_state.chat_history if c["id"] != chat_id
        ]
        _save_history_to_disk(st.session_state.chat_history)
        if st.session_state.current_chat_id == chat_id:
            st.session_state.messages = []
            st.session_state.current_chat_id = None

    # ---- Sidebar ----
    # Track architecture view in session state
    if "show_architecture" not in st.session_state:
        st.session_state.show_architecture = False

    with st.sidebar:
        with st.container(key="sb_new_chat"):
            if st.button("＋ New Chat", key="new_chat_btn", use_container_width=True):
                _save_current_chat()
                st.session_state.messages = []
                st.session_state.current_chat_id = None
                st.session_state.show_architecture = False
                st.rerun()

        with st.container(key="sb_arch"):
            if st.button("⚙️ Arquitetura", key="arch_btn", use_container_width=True):
                st.session_state.show_architecture = not st.session_state.show_architecture
                st.rerun()

        recent_chats = st.session_state.chat_history[:10]
        if recent_chats:
            st.markdown('<div class="history-label" style="margin-top:1.2rem;margin-bottom:4px;">Histórico</div>', unsafe_allow_html=True)
            for chat in recent_chats:
                is_active = chat["id"] == st.session_state.current_chat_id
                # Wrap each row in a real container so the CSS selectors below
                # (which target descendant buttons) actually nest correctly.
                with st.container(key=f"sb_row_{chat['id']}"):
                    col_t, col_d = st.columns([10, 1], gap="small")
                    with col_t:
                        load_key = f"sb_loadact_{chat['id']}" if is_active else f"sb_loadinact_{chat['id']}"
                        with st.container(key=load_key):
                            if st.button(chat["title"], key=f"chat_hist_{chat['id']}", use_container_width=True):
                                _save_current_chat()
                                st.session_state.messages = list(chat["messages"])
                                st.session_state.current_chat_id = chat["id"]
                                st.session_state.show_architecture = False
                                st.rerun()
                    with col_d:
                        with st.container(key=f"sb_del_{chat['id']}"):
                            if st.button("✕", key=f"del_{chat['id']}"):
                                _delete_chat(chat["id"])
                                st.rerun()


    # ---- Main content (no tabs) ----
    if st.session_state.get("show_architecture"):
        render_architecture_tab()
    else:
        col_left, col_center, col_right = st.columns([0.5, 2, 0.5])
        with col_center:
            if not st.session_state.messages:
                logo_b64 = load_logo_as_base64()
                if logo_b64:
                    st.markdown(
                        f"""
                        <div class="overview-container">
                            <img src="data:image/png;base64,{logo_b64}" alt="SportSphere" />
                            <div class="overview-text">
                                <p>Analise eventos desportivos com confiança usando um assistente especializado em estatísticas, regulamentos e logística.</p>
                                <p>Pergunte diretamente no chat sobre os desportos suportados (Basquetebol, Ténis, Atletismo, Fórmula 1), e o assistente responderá com base nos documentos locais.</p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown("## ⚽ SportSphere")
                    st.write("Analise eventos desportivos com confiança usando um assistente especializado em estatísticas, regulamentos e logística.")

                st.markdown("<br>", unsafe_allow_html=True)

                suggested_actions = [
                    {"title": "Regras da NBA", "label": "e detalhes da FIBA", "action": "Quais são as principais regras do basquetebol na NBA e na FIBA?"},
                    {"title": "Torneios Grand Slam", "label": "como funcionam", "action": "Podes explicar-me como funcionam os torneios de Grand Slam no Ténis?"},
                    {"title": "Atletismo Olímpico", "label": "recordes mundiais", "action": "Mostra-me alguns dos recordes mundiais atuais no atletismo olímpico."},
                    {"title": "Fórmula 1", "label": "pneus e bandeiras", "action": "Explica o significado das bandeiras e os tipos de pneus usados na Fórmula 1."},
                ]

                col1, col2 = st.columns(2)
                for i, action in enumerate(suggested_actions):
                    target_col = col1 if i % 2 == 0 else col2
                    with target_col:
                        with st.container(key=f"cb_suggestion_{i}"):
                            if st.button(
                                f"**{action['title']}**\n\n{action['label']}",
                                key=f"suggestion_{i}",
                                use_container_width=True,
                            ):
                                st.session_state.messages.append({"role": "user", "content": action["action"]})
                                st.rerun()

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            if st.session_state.uploaded_file_name:
                colA, colB = st.columns([8, 2])
                colA.info(f"📎 Contexto ativo: **{st.session_state.uploaded_file_name}**")
                if colB.button("Remover", key="remove_ctx_btn"):
                    st.session_state.uploaded_file_content = ""
                    st.session_state.uploaded_file_name = ""
                    st.rerun()

            if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                user_text = st.session_state.messages[-1]["content"]
                system_prompt = build_system_prompt(user_text, st.session_state.messages)

                with st.chat_message("assistant"):
                    response_placeholder = st.empty()
                    full_response = ""
                    for chunk in stream_ollama_response(system_prompt, st.session_state.messages):
                        full_response += chunk
                        response_placeholder.markdown(full_response + "▌")
                    response_placeholder.markdown(full_response)

                st.session_state.messages.append({"role": "assistant", "content": full_response})
                _save_current_chat()

        user_input_obj = st.bottom.chat_input(
            "Pergunte sobre eventos, estatísticas, regulamentos...",
            accept_file=True,
            file_type=["pdf", "docx", "txt", "md", "csv", "png", "jpg", "jpeg", "gif", "bmp", "tiff"],
        )
    
        if user_input_obj:
            user_text = user_input_obj.text if user_input_obj.text else ""
    
            if getattr(user_input_obj, "files", None):
                uploaded_file = user_input_obj.files[0]
                extracted = extract_text_from_upload(uploaded_file)
                st.session_state.uploaded_file_content = extracted
                st.session_state.uploaded_file_name = uploaded_file.name
                st.success(f"Ficheiro '{uploaded_file.name}' anexado ao contexto!")
                if not user_text:
                    user_text = "Acabei de anexar um ficheiro. Por favor, lê e confirma se está tudo bem."
    
            if user_text:
                st.session_state.messages.append({"role": "user", "content": user_text})
                st.rerun()
    

if __name__ == "__main__":
    main()