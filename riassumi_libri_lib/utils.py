"""
utils.py - Funzioni utility
"""

import re
from pathlib import Path
from typing import List

from .config import MAX_CHUNK_SIZE, CHUNK_OVERLAP


def ensure_directory(path: str) -> None:
    """Crea la directory se non esiste."""
    Path(path).mkdir(parents=True, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    """Rimuove caratteri non validi dal nome file."""
    # Rimuovi estensione se presente
    name = Path(filename).stem
    # Sostituisci caratteri non validi
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    return name.strip()


def count_words(text: str) -> int:
    """Conta le parole in un testo."""
    return len(text.split())


def chunk_text(text: str, max_size: int = MAX_CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Suddivide il testo in blocchi di dimensione massima con overlap.

    Args:
        text: Testo da suddividere
        max_size: Dimensione massima di ogni blocco in caratteri
        overlap: Numero di caratteri di sovrapposizione tra blocchi

    Returns:
        Lista di blocchi di testo
    """
    if len(text) <= max_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + max_size

        # Se non siamo alla fine, cerca un punto di divisione naturale
        if end < len(text):
            # Cerca ultimo punto, a capo o spazio nel range overlap
            search_start = max(start, end - overlap)
            natural_break = max(
                text.rfind('.', search_start, end),
                text.rfind('\n', search_start, end),
                text.rfind(' ', search_start, end)
            )
            if natural_break > start:
                end = natural_break + 1

        chunks.append(text[start:end].strip())
        start = end - overlap if end < len(text) else end

    return chunks
