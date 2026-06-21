"""
SportSphere - RAG + sports-domain logic.
Ported 1:1 from the original Streamlit prototype, with every
st.* dependency removed so it can be called from FastAPI (or anywhere else).
"""

from __future__ import annotations

import math
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from time import time as _now

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import pypdf
except ImportError:
    pypdf = None

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
LOCAL_RAG_STRICT_ONLY = os.getenv("LOCAL_RAG_STRICT_ONLY", "true").lower() != "false"
LOCAL_DOCS_SUBFOLDERS = os.getenv("LOCAL_DOCS_SUBFOLDERS", "")
LOCAL_DOCS_PATH = os.getenv("LOCAL_DOCS_PATH", "local-docs")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp"}

SUPPORTED_EXTENSIONS = {
    ".txt", ".md", ".json", ".jsonl", ".csv", ".tsv",
    ".html", ".htm", ".xml", ".yaml", ".yml", ".rtf",
    ".pdf", ".docx",
} | IMAGE_EXTENSIONS

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150

# ---------------------------------------------------------------------------
# Sports regulations (fallback only — used when RAG finds nothing)
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

SPORT_KEYWORDS: list[dict] = [
    # Football (NFL) tem de vir ANTES de Soccer: "futebol americano" contém
    # "futebol", que também é keyword do Soccer — o primeiro match na lista
    # ganha, por isso a entrada mais específica deve vir primeiro.
    {
        "name": "Football",
        "keywords": [
            "american football", "nfl", "futebol americano", "football americano",
            "touchdown", "superbowl", "super bowl", "quarterback",
        ],
    },
    {
        "name": "Soccer",
        "keywords": [
            "soccer", "futebol", "champions league", "premier league",
            "la liga", "serie a", "mundial", "world cup", "copa", "fifa", "fwc",
            "campeonato do mundo", "copa do mundo",
        ],
    },
    {
        "name": "Basketball",
        "keywords": [
            "basketball", "nba", "basquetebol", "basquete", "fiba",
            "cesto", "cestos", "ressalto", "rebound", "lancamento livre",
        ],
    },
    {
        "name": "Tennis",
        "keywords": ["tennis", "tenis", "atp", "wta", "grand slam", "wimbledon", "roland garros"],
    },
    {"name": "Cricket", "keywords": ["cricket", "ipl"]},
    {"name": "Formula1", "keywords": ["formula 1", "formula1", "f1", "fia", "grand prix", "gp", "formula um"]},
    {
        "name": "Olympics",
        "keywords": [
            "olympics", "atletismo", "athletics", "olimpiadas", "jogos olimpicos",
            "usain bolt", "sprint", "maratona",
        ],
    },
]

SPORT_FOLDER_MAP: dict[str, str] = {
    "Soccer": "soccer",
    "Basketball": "basketball",
    "Football": "nfl",
    "Tennis": "tennis",
    "Cricket": "cricket",
    "Formula1": "formula1",
    "Olympics": "olympics",
}

# ---------------------------------------------------------------------------
# Local RAG
# ---------------------------------------------------------------------------


def _normalize_text(value: str) -> str:
    value = value.lower()
    value = unicodedata.normalize("NFD", value)
    # Remove diacritics outright (do NOT replace with a space, or "ténis"
    # becomes "te nis" and substring keyword matches like "tenis" break).
    value = re.sub(r"[\u0300-\u036f]", "", value)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _tokenize(value: str) -> set[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return set()
    return {w for w in normalized.split(" ") if len(w) >= 2 or any(c.isdigit() for c in w)}


def _to_bigrams(tokens: list[str]) -> set[str]:
    return {f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1)}


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
    suffix = filepath.suffix.lower()
    if suffix == ".pdf":
        if pypdf is None:
            return ""
        try:
            reader = pypdf.PdfReader(str(filepath))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""
    if suffix == ".docx":
        try:
            import docx  # python-docx
            doc = docx.Document(str(filepath))
            return "\n".join(p.text for p in doc.paragraphs)
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


def _score_chunk(query_text: str, query_tokens: set[str], chunk_tokens: set[str], source_tokens: set[str]) -> float:
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


# Tiny manual TTL cache (60s) — keeps the same behaviour as st.cache_data(ttl=60)
# without depending on Streamlit.
_INDEX_CACHE: dict[str, tuple[float, list[dict]]] = {}
_INDEX_TTL_SECONDS = 60


def _get_indexed_chunks(docs_path_str: str) -> list[dict]:
    cached = _INDEX_CACHE.get(docs_path_str)
    if cached and (_now() - cached[0]) < _INDEX_TTL_SECONDS:
        return cached[1]

    docs_path = Path(docs_path_str)
    if not docs_path.is_dir():
        _INDEX_CACHE[docs_path_str] = (_now(), [])
        return []

    indexed = _index_local_docs(docs_path)
    print(f"DEBUG: Foram carregados {len(indexed)} pedaços de texto.")
    _INDEX_CACHE[docs_path_str] = (_now(), indexed)
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
    max_chunks: int = 10,
    subfolders: list[str] | None = None,
) -> list[dict]:
    configured = LOCAL_DOCS_PATH
    if not os.path.isabs(configured):
        configured = os.path.join(os.path.dirname(os.path.abspath(__file__)), configured)

    indexed = _get_indexed_chunks(configured)
    if not indexed:
        return []

    translated_query = translate_query_for_rag(user_message)
    query_tokens_pt = _tokenize(user_message)
    query_tokens_en = _tokenize(translated_query) if translated_query else set()
    combined_tokens = query_tokens_pt | query_tokens_en

    clean_subfolders = [_sanitize_subfolder(s) for s in (subfolders or []) if s.strip()]
    scoped = [c for c in indexed if _file_matches_subfolders(c["source"], clean_subfolders)]

    ranked = []
    for chunk in scoped:
        score = _score_chunk(user_message, combined_tokens, chunk["tokens"], chunk["source_tokens"])
        if score > 0:
            ranked.append({"source": chunk["source"], "text": chunk["text"], "score": score})

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:max_chunks]


# ---------------------------------------------------------------------------
# Sport detection / folder scoping helpers
# ---------------------------------------------------------------------------


def _detect_sport(user_message: str) -> dict | None:
    normalized = _normalize_text(user_message)  # lower-case + sem acentos
    for sport in SPORT_KEYWORDS:
        for kw in sport["keywords"]:
            if _normalize_text(kw) in normalized:
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
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/v1/chat/completions",
            json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": f"Translate to English: {user_query}"}],
                "temperature": 0,
                "max_tokens": 50,
                "options": {"stop": ["\n", "Translation:", "Aqui está"]},
            },
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# System prompt construction
# ---------------------------------------------------------------------------


def build_system_prompt(
    user_message: str, uploaded_file_content: str = ""
) -> tuple[str, list[str], list[str]]:
    """Returns (system_prompt, active_folder_scope, used_sources)."""
    league = _detect_sport(user_message)
    regulations = SPORTS_REGULATIONS.get(league["name"], []) if league else []

    requested_folders = _parse_folders_from_message(user_message)
    configured_folders = _parse_folders_from_env()
    auto_folder = (
        [SPORT_FOLDER_MAP[league["name"]]] if league and league["name"] in SPORT_FOLDER_MAP else []
    )
    scoped_folders = requested_folders or configured_folders or auto_folder

    rag_chunks = get_local_rag_context(user_message, max_chunks=10, subfolders=scoped_folders)

    # Files actually used to answer this question, e.g. ["soccer/regras.pdf"]
    used_sources = sorted({c["source"] for c in rag_chunks})

    if rag_chunks:
        rag_block = "\n\nLOCAL DOCUMENT CONTEXT (RAG):\n" + "\n".join(
            f"{i + 1}. {_trim_text(c['text'], 700)}" for i, c in enumerate(rag_chunks)
        )
    else:
        rag_block = "\n\nLOCAL DOCUMENT CONTEXT (RAG):\n- No matching local documents found for this question."

    upload_block = ""
    if uploaded_file_content:
        upload_block = (
            "\n\nUSER UPLOADED FILE CONTEXT:\n"
            "The user uploaded a file with the following content. Use it if relevant to the query:\n"
            f"---\n{_trim_text(uploaded_file_content, 8000)}\n---"
        )

    reg_snippet = ""
    if regulations and not rag_chunks:
        reg_snippet = (
            f"\n\nOFFICIAL REGULATIONS — FALLBACK ({league['name']}):\n"
            + "\n".join(f"{i + 1}. {r}" for i, r in enumerate(regulations[:3]))
        )

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

    scope_note = "\n\nACTIVE FOLDER SCOPE: " + (", ".join(scoped_folders) if scoped_folders else "all")

    system_prompt = f"""You are SportSphere, an AI sports assistant. You answer questions based on the documents provided below.

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

    return system_prompt, scoped_folders, used_sources


# ---------------------------------------------------------------------------
# Ollama streaming call
# ---------------------------------------------------------------------------


def stream_ollama_response(system_prompt: str, messages: list[dict]):
    """Generator that yields text chunks from Ollama's streaming response."""
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
                import json as _json
                data = _json.loads(line)
                delta = data.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content
            except Exception:
                continue
    except Exception as e:
        yield f"\n\n⚠️ Erro ao contactar o Ollama: {e}"


def check_model_status() -> bool:
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/v1/models", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False