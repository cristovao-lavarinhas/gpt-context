"""Local document library management — list/upload/delete files under local-docs/."""

from __future__ import annotations
from pathlib import Path

import os
import re
import shutil
import rag

LOCAL_DOCS_PATH = rag.LOCAL_DOCS_PATH
if not os.path.isabs(LOCAL_DOCS_PATH):
    LOCAL_DOCS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOCAL_DOCS_PATH)

DOCS_ROOT = Path(LOCAL_DOCS_PATH)

# Pastas que o assistente conhece (mesmas que o rag.py usa em SPORT_FOLDER_MAP).
FOLDER_LABELS: dict[str, str] = {
    "soccer": "Futebol",
    "basketball": "Basquetebol",
    "nfl": "Futebol Americano",
    "tennis": "Ténis",
    "cricket": "Cricket",
    "formula1": "Fórmula 1",
    "olympics": "Atletismo / Olimpíadas",
}


def _safe_filename(name: str) -> str:
    name = os.path.basename(name)
    name = re.sub(r"[^A-Za-z0-9 ._\-()]", "_", name)
    return name.strip() or "ficheiro"


def _safe_folder_name(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9\-_]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name


def list_library() -> list[dict]:
    DOCS_ROOT.mkdir(parents=True, exist_ok=True)

    existing_dirs = {f.name for f in DOCS_ROOT.iterdir() if f.is_dir()}
    all_folders = sorted(existing_dirs | set(FOLDER_LABELS.keys()))

    result = []
    for folder in all_folders:
        label = FOLDER_LABELS.get(folder, folder.replace("-", " ").replace("_", " ").title())
        folder_path = DOCS_ROOT / folder
        files = []
        if folder_path.is_dir():
            for f in sorted(folder_path.iterdir()):
                if f.is_file():
                    stat = f.stat()
                    files.append({
                        "name": f.name,
                        "size": stat.st_size,
                        "modified": int(stat.st_mtime),
                    })
        result.append({
            "folder": folder,
            "label": label,
            "files": files,
            "custom": folder not in FOLDER_LABELS,
        })
    return result


def create_folder(name: str) -> dict:
    safe = _safe_folder_name(name)
    if not safe:
        raise ValueError("Nome de pasta inválido.")
    if safe in FOLDER_LABELS:
        raise ValueError("Já existe uma pasta conhecida com esse nome.")

    folder_path = DOCS_ROOT / safe
    if folder_path.exists():
        raise ValueError("Já existe uma pasta com esse nome.")

    folder_path.mkdir(parents=True)
    rag.invalidate_index_cache()
    return {"folder": safe, "label": name.strip() or safe, "files": [], "custom": True}


def save_file(folder: str, filename: str, content: bytes) -> dict:
    folder_path = DOCS_ROOT / folder
    if folder not in FOLDER_LABELS and not folder_path.is_dir():
        raise ValueError("Pasta desconhecida.")

    ext = Path(filename).suffix.lower()
    if ext not in rag.SUPPORTED_EXTENSIONS:
        raise ValueError(f"Tipo de ficheiro não suportado: {ext}")

    if len(content) > rag.MAX_FILE_SIZE_BYTES:
        raise ValueError("Ficheiro demasiado grande (máx. 5MB).")

    folder_path.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_filename(filename)
    dest = folder_path / safe_name

    stem, suffix = dest.stem, dest.suffix
    counter = 1
    while dest.exists():
        dest = folder_path / f"{stem} ({counter}){suffix}"
        counter += 1

    dest.write_bytes(content)
    rag.invalidate_index_cache()

    stat = dest.stat()
    return {"name": dest.name, "size": stat.st_size, "modified": int(stat.st_mtime)}


def delete_file(folder: str, filename: str) -> None:
    folder_path = DOCS_ROOT / folder
    if folder not in FOLDER_LABELS and not folder_path.is_dir():
        raise ValueError("Pasta desconhecida.")

    safe_name = _safe_filename(filename)
    target = folder_path / safe_name
    if not target.is_file():
        raise FileNotFoundError("Ficheiro não encontrado.")

    target.unlink()
    rag.invalidate_index_cache()

def delete_folder(folder: str) -> None:
    if folder in FOLDER_LABELS:
        raise ValueError("Não é possível apagar uma pasta de desporto incorporada.")

    folder_path = DOCS_ROOT / folder
    if not folder_path.is_dir():
        raise FileNotFoundError("Pasta não encontrada.")

    shutil.rmtree(folder_path)
    rag.invalidate_index_cache()