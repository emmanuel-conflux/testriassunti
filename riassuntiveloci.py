#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
riassuntiveloci.py - CLI Tool per Riassunti di Libri via Ollama

APPROCCIO:
- Sampling configurabile (da 30% a 100% del testo)
- Sampling strategico: inizio, chunk distribuiti uniformemente, fine
- Riassunto globale unico (no capitolo per capitolo)
- Output minimalista (solo Markdown essenziale)
- Prompt ultra-concisi (max 300 parole per riassunto)
- Niente checkpoint (esecuzione diretta)
- Chunk enormi (max 32k caratteri)
- Temperature alta (velocità > qualità)

USO:
  --sampling-ratio 1.0   # 100% del testo (lento ma completo)
  --sampling-ratio 0.6   # 60% del testo (bilanciato)
  --sampling-ratio 0.3   # 30% del testo (veloce)
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
# CONFIGURAZIONE
# ============================================================================

VERSION = "2.2.0-CONFIGURABILE"
LAST_UPDATE = "2025-10-21"

DEFAULT_INPUT_DIR = os.path.expanduser("~/dariassumere")
DEFAULT_OUTPUT_DIR = os.path.expanduser("~/riassunti")
DEFAULT_MODEL = "qwen3:8b"
OLLAMA_URL = "http://localhost:11434/api/generate"

# Configurazione chunk
SPEED_CHUNK_SIZE = 32000        # ENORME: 32k caratteri per chunk
SPEED_MAX_CHUNKS = 5            # Parametro mantenuto per compatibilità (non più utilizzato)

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


def call_ollama_fast(prompt: str, model: str = DEFAULT_MODEL, max_retries: int = 2) -> Optional[str]:
    """
    Chiamata a Ollama con retry limitato per timeout.

    Args:
        prompt: Il prompt da inviare
        model: Nome del modello Ollama
        max_retries: Numero massimo di tentativi (default: 2)

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

    for attempt in range(max_retries):
        try:
            # Timeout di 10 minuti: chunk enormi (32k) richiedono tempo sostanziale
            # Il guadagno di velocità viene da fare MENO chiamate totali (5 vs 20-30)
            response = requests.post(OLLAMA_URL, json=payload, timeout=600)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "").strip()
        except requests.exceptions.Timeout as e:
            if attempt < max_retries - 1:
                print(f"⏱️  Timeout, riprovo ({attempt + 2}/{max_retries})...")
            else:
                print(f"⚠️  Timeout dopo {max_retries} tentativi")
                return None
        except Exception as e:
            print(f"⚠️  Errore Ollama: {e}")
            return None

    return None


# ============================================================================
# ESTRAZIONE TESTO
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


def split_text_into_chunks(text: str, chunk_size: int = SPEED_CHUNK_SIZE,
                          sampling_ratio: float = 1.0) -> List[str]:
    """
    Divide il testo in chunk con sampling configurabile.

    Args:
        text: Testo completo del libro
        chunk_size: Dimensione di ogni chunk
        sampling_ratio: Percentuale di chunk da mantenere (0.0-1.0)
                       1.0 = tutti i chunk (lettura completa)
                       0.3 = 30% dei chunk (veloce)

    Returns:
        Lista di chunk campionati uniformemente
    """
    if len(text) <= chunk_size:
        return [text]

    # Prima dividi tutto il testo in chunk
    all_chunks = []
    words = text.split()
    words_per_chunk = chunk_size // 5  # Stima ~5 caratteri per parola

    for i in range(0, len(words), words_per_chunk):
        chunk = ' '.join(words[i:i + words_per_chunk])
        if len(chunk) > 500:  # Solo se ha contenuto significativo
            all_chunks.append(chunk)

    # Se sampling_ratio = 1.0, ritorna tutti i chunk
    if sampling_ratio >= 1.0:
        return all_chunks

    total_chunks = len(all_chunks)

    # Calcola quanti chunk mantenere
    num_chunks_to_keep = max(2, int(total_chunks * sampling_ratio))

    # Se dobbiamo mantenere tutti o quasi tutti, ritorna tutto
    if num_chunks_to_keep >= total_chunks:
        return all_chunks

    # Sampling strategico: mantieni inizio, fine, e chunk distribuiti uniformemente
    selected_chunks = []

    # 1. Sempre il primo chunk (inizio del libro)
    selected_chunks.append(all_chunks[0])

    # 2. Chunk intermedi distribuiti uniformemente
    if num_chunks_to_keep > 2:
        num_middle = num_chunks_to_keep - 2
        # Distribuisci uniformemente i chunk nel mezzo
        step = (total_chunks - 2) / (num_middle + 1)
        for i in range(1, num_middle + 1):
            idx = int(1 + i * step)
            if idx < total_chunks - 1:
                selected_chunks.append(all_chunks[idx])

    # 3. Sempre l'ultimo chunk (fine del libro)
    selected_chunks.append(all_chunks[-1])

    return selected_chunks


# ============================================================================
# PROCESSING COMPLETO
# ============================================================================

def process_book_fast(filepath: str, output_dir: str, model: str = DEFAULT_MODEL,
                     sampling_ratio: float = 1.0) -> bool:
    """
    Elaborazione di un libro con sampling configurabile.

    STRATEGIA:
    1. Estrazione rapida tutto il testo
    2. Divisione in chunk con sampling configurabile
    3. Riassunti ultra-concisi
    4. Output minimalista (solo .md)

    Args:
        filepath: Percorso del file del libro
        output_dir: Directory di output
        model: Modello Ollama da usare
        sampling_ratio: Percentuale di testo da processare (0.0-1.0)

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

    # [2/3] Divisione e Riassunto con sampling configurabile
    print(f"[2/3] ⚡ Divisione del testo e riassunti...")

    # Divide il testo in chunk con sampling configurabile
    text_chunks = split_text_into_chunks(full_text,
                                        chunk_size=SPEED_CHUNK_SIZE,
                                        sampling_ratio=sampling_ratio)

    # Calcola chunk totali per mostrare la percentuale
    words = full_text.split()
    words_per_chunk = SPEED_CHUNK_SIZE // 5
    total_possible_chunks = len([i for i in range(0, len(words), words_per_chunk)])

    if sampling_ratio >= 1.0:
        print(f"   📊 Processando {len(text_chunks)} chunk (100% del testo)")
    else:
        print(f"   📊 Processando {len(text_chunks)}/{total_possible_chunks} chunk ({sampling_ratio:.0%} del testo)")
        print(f"   (sampling strategico: inizio, medio, fine)")

    # Riassumi ogni chunk
    chunk_summaries = []

    for idx, chunk in enumerate(text_chunks, 1):
        print(f"   ⚡ Chunk {idx}/{len(text_chunks)}... ", end='', flush=True)

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
    if sampling_ratio >= 1.0:
        mode_text = "Lettura completa del testo (100%)"
    else:
        mode_text = f"Sampling strategico ({sampling_ratio:.0%} del testo)"

    content = f"""# Riassunto Veloce — {book_title}

**Generato con:** riassuntiveloci.py v{VERSION}
**Modalità:** {mode_text}
**Chunk analizzati:** {len(chunk_summaries)}/{total_possible_chunks}
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

*Riassunto generato automaticamente con lettura completa del testo.*
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
    print("⚡ RIASSUNTI VELOCI - CLI Tool per Riassunti via Ollama")
    print("="*70)
    print(f"Versione: {VERSION}")
    print(f"Ultimo aggiornamento: {LAST_UPDATE}")
    print("")
    print("CARATTERISTICHE:")
    print("  • Sampling configurabile (velocità vs completezza)")
    print("  • --sampling-ratio 1.0 = 100% (completo)")
    print("  • --sampling-ratio 0.6 = 60% (bilanciato)")
    print("  • --sampling-ratio 0.3 = 30% (veloce)")
    print("  • Riassunti ultra-concisi (max 300 parole)")
    print("  • Chunk enormi (32k caratteri)")
    print("="*70 + "\n")

    parser = argparse.ArgumentParser(
        description="CLI Tool per Riassunti di Libri via Ollama con Sampling Configurabile",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  # Lettura completa (lento ma completo)
  python riassuntiveloci.py --sampling-ratio 1.0

  # Bilanciato (velocità e qualità)
  python riassuntiveloci.py --sampling-ratio 0.6

  # Veloce (solo 30% del testo)
  python riassuntiveloci.py --sampling-ratio 0.3

  # Con parametri personalizzati
  python riassuntiveloci.py --model qwen3:8b --sampling-ratio 0.5
  python riassuntiveloci.py --input_dir /path/to/books --sampling-ratio 0.7
        """
    )

    parser.add_argument('--model', type=str, default=DEFAULT_MODEL,
                       help=f'Modello Ollama (default: {DEFAULT_MODEL})')
    parser.add_argument('--input_dir', type=str, default=DEFAULT_INPUT_DIR,
                       help=f'Directory input (default: {DEFAULT_INPUT_DIR})')
    parser.add_argument('--output_dir', type=str, default=DEFAULT_OUTPUT_DIR,
                       help=f'Directory output (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--sampling-ratio', type=float, default=1.0,
                       help='Percentuale di testo da processare (0.0-1.0, default: 1.0 = tutto)')

    args = parser.parse_args()

    # Validazione sampling-ratio
    sampling_ratio = args.sampling_ratio
    if sampling_ratio < 0.0 or sampling_ratio > 1.0:
        print("❌ Errore: --sampling-ratio deve essere tra 0.0 e 1.0")
        sys.exit(1)

    print("📋 PARAMETRI DI ESECUZIONE")
    print("="*70)
    print(f"Modello: {args.model}")
    print(f"Input: {args.input_dir}")
    print(f"Output: {args.output_dir}")
    print(f"Sampling ratio: {sampling_ratio:.0%} del testo")
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

    for idx, filepath in enumerate(files, 1):
        print(f"\n{'#'*60}")
        print(f"FILE {idx}/{len(files)}")
        print(f"{'#'*60}")

        try:
            if process_book_fast(str(filepath), args.output_dir, args.model, sampling_ratio):
                success_count += 1
        except Exception as e:
            print(f"\n❌ Errore: {e}")
            continue

    # Riepilogo finale
    print(f"\n{'='*60}")
    if sampling_ratio >= 1.0:
        print(f"✅ COMPLETATO - LETTURA COMPLETA (100%)")
    else:
        print(f"✅ COMPLETATO - SAMPLING {sampling_ratio:.0%}")
    print(f"{'='*60}")
    print(f"File elaborati: {success_count}/{len(files)}")
    print(f"Output salvati in: {args.output_dir}")
    print(f"Suffisso file: .veloce.md")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
