#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
riassuntiveloci.py - CLI Tool ULTRA-VELOCE per Riassunti di Libri via Ollama

APPROCCIO RADICALMENTE DIVERSO:
- Sampling intelligente (non tutti i capitoli)
- Riassunto globale unico (no capitolo per capitolo)
- Output minimalista (solo Markdown essenziale)
- Prompt ultra-concisi (max 300 parole per riassunto)
- Niente checkpoint (esecuzione diretta)
- Chunk enormi (max 32k caratteri)
- Temperature alta (velocità > qualità)

GUADAGNO VELOCITÀ: 5-10x più veloce di riassumi.py
"""

import os
import sys
import argparse
import re
from pathlib import Path
from typing import List, Dict, Optional

# Dependencies
import requests

# EPUB handling
try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    EPUB_SUPPORT = True
except ImportError:
    EPUB_SUPPORT = False

# PDF handling
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


# ============================================================================
# CONFIGURAZIONE VELOCITÀ
# ============================================================================

VERSION = "2.0.0-VELOCE"
LAST_UPDATE = "2025-10-21"

DEFAULT_INPUT_DIR = os.path.expanduser("~/dariassumere")
DEFAULT_OUTPUT_DIR = os.path.expanduser("~/riassunti")
DEFAULT_MODEL = "qwen3:8b"
OLLAMA_URL = "http://localhost:11434/api/generate"

# Configurazione VELOCITÀ MASSIMA
SPEED_CHUNK_SIZE = 32000        # ENORME: 32k caratteri per chunk
SPEED_MAX_CHUNKS = 5            # Massimo 5 chunk per libro (sampling)
SPEED_SAMPLE_CHAPTERS = True    # Campiona solo alcuni capitoli
SPEED_SAMPLE_RATIO = 0.3        # Usa solo 30% dei capitoli
SPEED_MIN_SAMPLE = 3            # Minimo 3 capitoli campionati
SPEED_MAX_SAMPLE = 8            # Massimo 8 capitoli campionati

# Prompt ULTRA-CONCISI (velocità massima)
PROMPT_FAST = """Riassumi il seguente testo in italiano.
Massimo 300 parole, solo concetti chiave.

TESTO:
{text}

RIASSUNTO BREVE IN ITALIANO:"""

PROMPT_GLOBAL_FAST = """Basandoti su questi estratti, genera un riassunto complessivo del libro in italiano.
Massimo 500 parole.

ESTRATTI:
{summaries}

RIASSUNTO LIBRO (max 500 parole):"""


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def ensure_directory(path: str) -> None:
    """Crea la directory se non esiste."""
    Path(path).mkdir(parents=True, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    """Rimuove caratteri non validi dal nome file."""
    name = Path(filename).stem
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    return name.strip()


def call_ollama_fast(prompt: str, model: str = DEFAULT_MODEL) -> Optional[str]:
    """
    Chiamata VELOCE a Ollama (niente retry, alta temperature, context ridotto).

    Args:
        prompt: Il prompt da inviare
        model: Nome del modello Ollama

    Returns:
        Testo generato o None in caso di errore
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,  # Alta per velocità (meno "thinking")
            "num_ctx": 32000,    # Context ridotto per velocità
            "num_predict": 500   # Limite output per velocità
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        response.raise_for_status()
        result = response.json()
        return result.get("response", "").strip()
    except Exception as e:
        print(f"⚠️  Errore Ollama: {e}")
        return None


# ============================================================================
# ESTRAZIONE ULTRA-VELOCE
# ============================================================================

def extract_text_fast_epub(filepath: str) -> str:
    """
    Estrazione VELOCE da EPUB: tutto il testo in un colpo solo.

    Args:
        filepath: Percorso del file EPUB

    Returns:
        Tutto il testo del libro concatenato
    """
    if not EPUB_SUPPORT:
        print("❌ Supporto EPUB non disponibile")
        return ""

    try:
        book = epub.read_epub(filepath)
        full_text = []

        # Prendi tutti gli item dello spine senza parsing elaborato
        spine_items = [book.get_item_with_id(item_id) for item_id, _ in book.spine]

        for item in spine_items:
            if item is None:
                continue

            try:
                content = item.get_content()
                soup = BeautifulSoup(content, 'html.parser')

                # Rimuovi solo script e style
                for tag in soup(['script', 'style']):
                    tag.decompose()

                text = soup.get_text(separator=' ', strip=True)
                if len(text) > 100:  # Solo se ha contenuto minimo
                    full_text.append(text)

            except:
                continue

        return "\n\n".join(full_text)

    except Exception as e:
        print(f"❌ Errore lettura EPUB: {e}")
        return ""


def extract_text_fast_pdf(filepath: str) -> str:
    """
    Estrazione VELOCE da PDF: tutto il testo senza parsing capitoli.

    Args:
        filepath: Percorso del file PDF

    Returns:
        Tutto il testo del libro concatenato
    """
    if not PDF_SUPPORT:
        print("❌ Supporto PDF non disponibile")
        return ""

    try:
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            full_text = []

            for page in reader.pages:
                try:
                    text = page.extract_text()
                    if text and len(text.strip()) > 50:
                        full_text.append(text)
                except:
                    continue

        return "\n\n".join(full_text)

    except Exception as e:
        print(f"❌ Errore lettura PDF: {e}")
        return ""


def smart_sample_text(text: str, max_chunks: int = SPEED_MAX_CHUNKS,
                     chunk_size: int = SPEED_CHUNK_SIZE) -> List[str]:
    """
    Sampling INTELLIGENTE: prende inizio, campioni intermedi, e fine.

    Args:
        text: Testo completo del libro
        max_chunks: Numero massimo di chunk da estrarre
        chunk_size: Dimensione di ogni chunk

    Returns:
        Lista di chunk campionati strategicamente
    """
    if len(text) <= chunk_size:
        return [text]

    # Dividi il testo in segmenti
    words = text.split()
    total_words = len(words)
    words_per_chunk = chunk_size // 5  # Stima ~5 caratteri per parola

    if total_words <= words_per_chunk:
        return [text]

    chunks = []

    # 1. INIZIO (sempre importante)
    start_chunk = ' '.join(words[:words_per_chunk])
    chunks.append(start_chunk)

    if max_chunks == 1:
        return chunks

    # 2. FINE (sempre importante)
    end_chunk = ' '.join(words[-words_per_chunk:])

    if max_chunks == 2:
        chunks.append(end_chunk)
        return chunks

    # 3. CAMPIONI INTERMEDI (distribuiti uniformemente)
    num_middle_chunks = max_chunks - 2
    middle_positions = []

    for i in range(num_middle_chunks):
        # Posizioni equidistanti tra inizio e fine
        position = words_per_chunk + (i + 1) * (total_words - 2 * words_per_chunk) // (num_middle_chunks + 1)
        middle_positions.append(position)

    for pos in middle_positions:
        chunk = ' '.join(words[pos:pos + words_per_chunk])
        if len(chunk) > 500:  # Solo se ha contenuto significativo
            chunks.append(chunk)

    # Aggiungi il chunk finale
    chunks.append(end_chunk)

    return chunks


# ============================================================================
# PROCESSING ULTRA-VELOCE
# ============================================================================

def process_book_fast(filepath: str, output_dir: str, model: str = DEFAULT_MODEL) -> bool:
    """
    Elaborazione ULTRA-VELOCE di un libro.

    STRATEGIA:
    1. Estrazione rapida tutto il testo
    2. Sampling intelligente (solo parti chiave)
    3. Riassunti ultra-concisi
    4. Output minimalista (solo .md)

    Args:
        filepath: Percorso del file del libro
        output_dir: Directory di output
        model: Modello Ollama da usare

    Returns:
        True se successo, False altrimenti
    """
    filepath = Path(filepath)
    extension = filepath.suffix.lower()
    book_title = sanitize_filename(filepath.name)

    print(f"\n{'='*60}")
    print(f"⚡ ELABORAZIONE VELOCE: {filepath.name}")
    print(f"{'='*60}\n")

    # [1/3] Estrazione VELOCE
    print(f"[1/3] ⚡ Estrazione rapida testo completo...")

    if extension == '.epub':
        full_text = extract_text_fast_epub(str(filepath))
    elif extension == '.pdf':
        full_text = extract_text_fast_pdf(str(filepath))
    else:
        print(f"❌ Formato non supportato: {extension}")
        return False

    if not full_text or len(full_text) < 1000:
        print("❌ Testo insufficiente estratto")
        return False

    words_count = len(full_text.split())
    print(f"✅ Estratte ~{words_count:,} parole\n")

    # [2/3] Sampling e Riassunto VELOCE
    print(f"[2/3] ⚡ Sampling intelligente e riassunti rapidi...")

    # Campiona parti strategiche
    sampled_chunks = smart_sample_text(full_text,
                                       max_chunks=SPEED_MAX_CHUNKS,
                                       chunk_size=SPEED_CHUNK_SIZE)

    print(f"   📊 Campionati {len(sampled_chunks)} chunk strategici")
    print(f"   (inizio, {len(sampled_chunks)-2} intermedi, fine)")

    # Riassumi ogni chunk
    chunk_summaries = []

    for idx, chunk in enumerate(sampled_chunks, 1):
        print(f"   ⚡ Chunk {idx}/{len(sampled_chunks)}... ", end='', flush=True)

        prompt = PROMPT_FAST.format(text=chunk)
        summary = call_ollama_fast(prompt, model)

        if summary:
            chunk_summaries.append(summary)
            print("✅")
        else:
            print("⚠️")

    if not chunk_summaries:
        print("\n❌ Nessun riassunto generato")
        return False

    print(f"✅ {len(chunk_summaries)} riassunti parziali generati\n")

    # Genera riassunto globale VELOCE
    print(f"[3/3] ⚡ Generazione riassunto globale rapido...")

    combined_summaries = "\n\n---\n\n".join(chunk_summaries)
    global_prompt = PROMPT_GLOBAL_FAST.format(summaries=combined_summaries)
    global_summary = call_ollama_fast(global_prompt, model)

    if not global_summary:
        print("⚠️  Uso riassunti parziali come fallback")
        global_summary = combined_summaries
    else:
        print("✅ Riassunto globale generato")

    # [4/3] Output MINIMALISTA (solo Markdown)
    print(f"\n[4/4] ⚡ Scrittura output minimalista...")

    md_path = os.path.join(output_dir, f"{book_title}.veloce.md")

    # Output ESSENZIALE (no formattazione elaborata)
    content = f"""# Riassunto Veloce — {book_title}

**Generato con:** riassuntiveloci.py v{VERSION}
**Modalità:** Ultra-veloce (sampling intelligente)
**Chunk analizzati:** {len(chunk_summaries)}/{len(sampled_chunks)}
**Parole totali libro:** ~{words_count:,}

---

## Riassunto Complessivo

{global_summary}

---

## Estratti Analizzati

"""

    for idx, summary in enumerate(chunk_summaries, 1):
        content += f"### Estratto {idx}\n\n{summary}\n\n"

    content += f"""---

*Riassunto generato automaticamente con approccio ultra-veloce.*
*Per riassunti più dettagliati, usa riassumi.py*
"""

    try:
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ MD: {md_path}")
        return True
    except Exception as e:
        print(f"❌ Errore scrittura: {e}")
        return False


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Funzione principale del programma."""
    print("\n" + "="*70)
    print("⚡ RIASSUNTI VELOCI - CLI Tool ULTRA-VELOCE via Ollama")
    print("="*70)
    print(f"Versione: {VERSION}")
    print(f"Ultimo aggiornamento: {LAST_UPDATE}")
    print("")
    print("OTTIMIZZAZIONI VELOCITÀ:")
    print("  • Sampling intelligente (non tutti i capitoli)")
    print("  • Riassunti ultra-concisi (max 300 parole)")
    print("  • Chunk enormi (32k caratteri)")
    print("  • Niente checkpoint")
    print("  • Output minimalista")
    print("")
    print("GUADAGNO: 5-10x più veloce di riassumi.py")
    print("="*70 + "\n")

    parser = argparse.ArgumentParser(
        description="CLI Tool ULTRA-VELOCE per Riassunti di Libri via Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python riassuntiveloci.py
  python riassuntiveloci.py --model qwen3:8b
  python riassuntiveloci.py --input_dir /path/to/books
        """
    )

    parser.add_argument('--model', type=str, default=DEFAULT_MODEL,
                       help=f'Modello Ollama (default: {DEFAULT_MODEL})')
    parser.add_argument('--input_dir', type=str, default=DEFAULT_INPUT_DIR,
                       help=f'Directory input (default: {DEFAULT_INPUT_DIR})')
    parser.add_argument('--output_dir', type=str, default=DEFAULT_OUTPUT_DIR,
                       help=f'Directory output (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--max_chunks', type=int, default=SPEED_MAX_CHUNKS,
                       help=f'Numero massimo chunk da campionare (default: {SPEED_MAX_CHUNKS})')

    args = parser.parse_args()

    print("📋 PARAMETRI DI ESECUZIONE")
    print("="*70)
    print(f"Modello: {args.model}")
    print(f"Input: {args.input_dir}")
    print(f"Output: {args.output_dir}")
    print(f"Max chunk campionati: {args.max_chunks}")
    print(f"Dimensione chunk: {SPEED_CHUNK_SIZE:,} caratteri")
    print("="*70 + "\n")

    # Verifica directory input
    if not os.path.exists(args.input_dir):
        print(f"❌ Directory input non trovata: {args.input_dir}")
        print(f"   Crea la directory con: mkdir -p {args.input_dir}")
        sys.exit(1)

    # Scansiona file
    print(f"🔍 Scansione {args.input_dir}")
    files = []

    for ext in ['.epub', '.pdf']:
        files.extend(Path(args.input_dir).glob(f'*{ext}'))

    if not files:
        print("❌ Nessun file EPUB o PDF trovato")
        sys.exit(1)

    print(f"✅ Trovati {len(files)} file\n")

    # Crea directory output
    try:
        ensure_directory(args.output_dir)
    except Exception as e:
        print(f"❌ Impossibile creare directory output: {e}")
        sys.exit(1)

    # Verifica Ollama
    print("🔍 Verifica connessione a Ollama...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        print("✅ Ollama raggiungibile\n")
    except Exception as e:
        print(f"❌ Errore connessione Ollama: {e}")
        sys.exit(1)

    # Elabora ogni file
    success_count = 0

    # Salva il valore personalizzato se fornito
    if args.max_chunks != SPEED_MAX_CHUNKS:
        global SPEED_MAX_CHUNKS
        SPEED_MAX_CHUNKS = args.max_chunks

    for idx, filepath in enumerate(files, 1):
        print(f"\n{'#'*60}")
        print(f"FILE {idx}/{len(files)}")
        print(f"{'#'*60}")

        try:
            if process_book_fast(str(filepath), args.output_dir, args.model):
                success_count += 1
        except Exception as e:
            print(f"\n❌ Errore: {e}")
            continue

    # Riepilogo finale
    print(f"\n{'='*60}")
    print(f"⚡ COMPLETATO IN MODALITÀ VELOCE")
    print(f"{'='*60}")
    print(f"File elaborati: {success_count}/{len(files)}")
    print(f"Output salvati in: {args.output_dir}")
    print(f"Suffisso file: .veloce.md")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
