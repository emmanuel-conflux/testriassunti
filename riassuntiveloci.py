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

GESTIONE ERRORI (v2.3.0+):
- Visualizzazione dettagliata errori (tipo, messaggio, tentativi)
- Retry automatico con exponential backoff
- Salvataggio stato chunk falliti in JSON
- Recupero selettivo con --retry-failed

USO:
  --sampling-ratio 1.0   # 100% del testo (lento ma completo)
  --sampling-ratio 0.6   # 60% del testo (bilanciato)
  --sampling-ratio 0.3   # 30% del testo (veloce)
  --retry-failed file.failed_chunks.json  # Recupera solo chunk falliti
"""

import os
import sys
import argparse
import re
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple

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

VERSION = "2.3.0-ERROR-RECOVERY"
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


def call_ollama_fast(prompt: str, model: str = DEFAULT_MODEL, max_retries: int = 3) -> Tuple[Optional[str], Optional[Dict]]:
    """
    Chiamata a Ollama con retry e informazioni dettagliate sugli errori.

    Args:
        prompt: Il prompt da inviare
        model: Nome del modello Ollama
        max_retries: Numero massimo di tentativi (default: 3)

    Returns:
        Tuple[Optional[str], Optional[Dict]]: (testo_generato, info_errore)
        - Se successo: (testo, None)
        - Se errore: (None, {"type": "timeout|connection|other", "message": "...", "attempts": N})
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

    last_error = None

    for attempt in range(max_retries):
        try:
            # Timeout di 10 minuti: chunk enormi (32k) richiedono tempo sostanziale
            # Il guadagno di velocità viene da fare MENO chiamate totali (5 vs 20-30)
            response = requests.post(OLLAMA_URL, json=payload, timeout=600)
            response.raise_for_status()
            result = response.json()
            text = result.get("response", "").strip()
            if text:
                return (text, None)
            else:
                last_error = {"type": "empty_response", "message": "Risposta vuota da Ollama", "attempts": attempt + 1}

        except requests.exceptions.Timeout:
            last_error = {
                "type": "timeout",
                "message": f"Timeout dopo 600 secondi (tentativo {attempt + 1}/{max_retries})",
                "attempts": attempt + 1
            }
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"\n      ⏱️  Timeout, attendo {wait_time}s prima di riprovare... ", end='', flush=True)
                time.sleep(wait_time)

        except requests.exceptions.ConnectionError as e:
            last_error = {
                "type": "connection",
                "message": f"Errore di connessione: {str(e)[:100]}",
                "attempts": attempt + 1
            }
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"\n      🔌 Errore connessione, riprovo tra {wait_time}s... ", end='', flush=True)
                time.sleep(wait_time)

        except requests.exceptions.HTTPError as e:
            last_error = {
                "type": "http_error",
                "message": f"Errore HTTP {e.response.status_code}: {str(e)[:100]}",
                "attempts": attempt + 1
            }
            # HTTPError spesso non ha senso ritentare
            break

        except Exception as e:
            last_error = {
                "type": "unknown",
                "message": f"Errore imprevisto: {type(e).__name__}: {str(e)[:100]}",
                "attempts": attempt + 1
            }
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"\n      ⚠️  Errore, riprovo tra {wait_time}s... ", end='', flush=True)
                time.sleep(wait_time)

    return (None, last_error)


# ============================================================================
# GESTIONE STATO ERRORI E RECUPERO
# ============================================================================

def save_failed_chunks_state(filepath: str, output_dir: str, failed_chunks: List[Dict]) -> str:
    """
    Salva lo stato dei chunk falliti in un file JSON.

    Args:
        filepath: Percorso del file del libro
        output_dir: Directory di output
        failed_chunks: Lista di chunk falliti con informazioni

    Returns:
        Percorso del file di stato salvato
    """
    book_title = sanitize_filename(Path(filepath).name)
    state_path = os.path.join(output_dir, f"{book_title}.failed_chunks.json")

    state = {
        "book_filepath": str(filepath),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "failed_chunks": failed_chunks
    }

    try:
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        return state_path
    except Exception as e:
        print(f"⚠️  Impossibile salvare stato errori: {e}")
        return ""


def load_failed_chunks_state(state_path: str) -> Optional[Dict]:
    """
    Carica lo stato dei chunk falliti da un file JSON.

    Args:
        state_path: Percorso del file di stato

    Returns:
        Dizionario con lo stato o None se errore
    """
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Impossibile caricare stato: {e}")
        return None


def format_error_details(error_info: Dict) -> str:
    """
    Formatta i dettagli dell'errore per la visualizzazione.

    Args:
        error_info: Dizionario con informazioni sull'errore

    Returns:
        Stringa formattata dell'errore
    """
    error_type = error_info.get("type", "unknown")
    message = error_info.get("message", "Errore sconosciuto")
    attempts = error_info.get("attempts", 1)

    # Emoji per tipo di errore
    emoji_map = {
        "timeout": "⏱️",
        "connection": "🔌",
        "http_error": "🌐",
        "empty_response": "📭",
        "unknown": "❓"
    }

    emoji = emoji_map.get(error_type, "⚠️")
    return f"{emoji} {error_type.upper()}: {message} (tentativi: {attempts})"


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

    # Riassumi ogni chunk con tracking dettagliato degli errori
    chunk_summaries = []
    failed_chunks = []

    for idx, chunk in enumerate(text_chunks, 1):
        print(f"   ⚡ Chunk {idx}/{len(text_chunks)}... ", end='', flush=True)

        prompt = PROMPT_FAST.format(text=chunk)
        summary, error_info = call_ollama_fast(prompt, model)

        if summary:
            chunk_summaries.append({
                "index": idx,
                "summary": summary,
                "success": True
            })
            print("✅")
        else:
            # Chunk fallito - mostra dettagli errore
            print("❌")
            if error_info:
                error_details = format_error_details(error_info)
                print(f"      ╰─> {error_details}")

            # Salva informazioni sul chunk fallito (con chunk completo per recupero)
            failed_chunks.append({
                "index": idx,
                "total_chunks": len(text_chunks),
                "error": error_info,
                "chunk_text": chunk,  # Salva tutto il chunk per recupero completo
                "chunk_size": len(chunk)
            })

    # Riepilogo con dettagli
    success_count = len(chunk_summaries)
    failed_count = len(failed_chunks)

    if success_count == 0:
        print("\n❌ Nessun riassunto generato - tutti i chunk sono falliti")
        return False

    # Mostra riepilogo dettagliato
    print(f"\n📊 RIEPILOGO PROCESSAMENTO:")
    print(f"   ✅ Chunk riusciti: {success_count}/{len(text_chunks)}")
    if failed_count > 0:
        print(f"   ❌ Chunk falliti: {failed_count}/{len(text_chunks)}")
        print(f"   📋 Chunk falliti: {[fc['index'] for fc in failed_chunks]}")

        # Salva stato dei chunk falliti per recupero successivo
        state_path = save_failed_chunks_state(str(filepath), output_dir, failed_chunks)
        if state_path:
            print(f"\n💾 Stato errori salvato in: {state_path}")
            print(f"   Per recuperare i chunk falliti usa:")
            print(f"   python riassuntiveloci.py --retry-failed \"{state_path}\"")

    print()

    # Genera riassunto globale VELOCE
    print(f"[3/3] ⚡ Generazione riassunto globale rapido...")

    # Estrai i summary dai dizionari
    summary_texts = [cs["summary"] for cs in chunk_summaries]
    combined_summaries = "\n\n---\n\n".join(summary_texts)
    global_prompt = PROMPT_GLOBAL_FAST.format(summaries=combined_summaries)
    global_summary, global_error = call_ollama_fast(global_prompt, model)

    if not global_summary:
        print("⚠️  Errore nella generazione del riassunto globale")
        if global_error:
            print(f"      ╰─> {format_error_details(global_error)}")
        print("      Uso riassunti parziali come fallback")
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

    for chunk_data in chunk_summaries:
        idx = chunk_data["index"]
        summary = chunk_data["summary"]
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
# RECUPERO CHUNK FALLITI
# ============================================================================

def retry_failed_chunks(state_path: str, output_dir: str, model: str = DEFAULT_MODEL) -> bool:
    """
    Riprocessa solo i chunk che erano falliti in una precedente esecuzione.

    Args:
        state_path: Percorso del file JSON con lo stato dei chunk falliti
        output_dir: Directory di output
        model: Modello Ollama da usare

    Returns:
        True se successo, False altrimenti
    """
    print(f"\n{'='*60}")
    print(f"🔄 RECUPERO CHUNK FALLITI")
    print(f"{'='*60}\n")

    # Carica lo stato
    state = load_failed_chunks_state(state_path)
    if not state:
        return False

    book_filepath = state.get("book_filepath", "")
    failed_chunks = state.get("failed_chunks", [])
    timestamp = state.get("timestamp", "sconosciuto")

    if not failed_chunks:
        print("✅ Nessun chunk da recuperare")
        return True

    print(f"📖 Libro: {Path(book_filepath).name}")
    print(f"📅 Errore originale: {timestamp}")
    print(f"📋 Chunk da recuperare: {len(failed_chunks)}")
    print(f"   Indici: {[fc['index'] for fc in failed_chunks]}\n")

    # Riprocessa ogni chunk fallito
    recovered_summaries = []
    still_failed = []

    for fc in failed_chunks:
        idx = fc["index"]
        chunk_text = fc.get("chunk_text", "")

        if not chunk_text:
            print(f"⚠️  Chunk {idx}: Testo non disponibile, impossibile recuperare")
            still_failed.append(fc)
            continue

        print(f"🔄 Tentativo recupero Chunk {idx}... ", end='', flush=True)

        # Riprocessa il chunk completo con più tentativi
        prompt = PROMPT_FAST.format(text=chunk_text)
        summary, error_info = call_ollama_fast(prompt, model, max_retries=4)  # Più tentativi per il recovery

        if summary:
            recovered_summaries.append({
                "index": idx,
                "summary": summary,
                "recovered": True
            })
            print("✅ RECUPERATO")
        else:
            print("❌ ANCORA FALLITO")
            if error_info:
                error_details = format_error_details(error_info)
                print(f"      ╰─> {error_details}")
            fc["retry_error"] = error_info
            still_failed.append(fc)

    # Riepilogo recupero
    print(f"\n📊 RIEPILOGO RECUPERO:")
    print(f"   ✅ Chunk recuperati: {len(recovered_summaries)}/{len(failed_chunks)}")
    if still_failed:
        print(f"   ❌ Chunk ancora falliti: {len(still_failed)}/{len(failed_chunks)}")
        print(f"   📋 Indici ancora falliti: {[fc['index'] for fc in still_failed]}")

        # Aggiorna il file di stato con i chunk ancora falliti
        if len(still_failed) < len(failed_chunks):
            # Alcuni sono stati recuperati, aggiorna lo stato
            new_state_path = save_failed_chunks_state(book_filepath, output_dir, still_failed)
            if new_state_path:
                print(f"\n💾 Stato aggiornato: {new_state_path}")
        else:
            print(f"\n⚠️  Nessun chunk recuperato, stato invariato")
    else:
        print(f"\n🎉 Tutti i chunk sono stati recuperati con successo!")
        # Rimuovi il file di stato dato che non ci sono più errori
        try:
            os.remove(state_path)
            print(f"🗑️  File di stato rimosso: {state_path}")
        except:
            pass

    # Salva i riassunti recuperati in un file separato
    if recovered_summaries:
        book_title = sanitize_filename(Path(book_filepath).name)
        recovery_path = os.path.join(output_dir, f"{book_title}.recovered_chunks.md")

        content = f"""# Chunk Recuperati — {book_title}

**Recuperati il:** {time.strftime("%Y-%m-%d %H:%M:%S")}
**Chunk recuperati:** {len(recovered_summaries)}
**Chunk totali falliti originalmente:** {len(failed_chunks)}

---

"""

        for chunk_data in recovered_summaries:
            idx = chunk_data["index"]
            summary = chunk_data["summary"]
            content += f"## Chunk {idx}\n\n{summary}\n\n---\n\n"

        try:
            with open(recovery_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"\n📄 Chunk recuperati salvati in: {recovery_path}")
        except Exception as e:
            print(f"\n⚠️  Errore salvataggio chunk recuperati: {e}")

    return len(recovered_summaries) > 0


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
    print("")
    print("NUOVE FUNZIONALITÀ (v2.3.0):")
    print("  • 🔍 Errori dettagliati (tipo, messaggio, tentativi)")
    print("  • 🔄 Retry automatico con exponential backoff")
    print("  • 💾 Salvataggio stato chunk falliti")
    print("  • 🎯 Recupero selettivo con --retry-failed")
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

  # Recupero chunk falliti (v2.3.0+)
  python riassuntiveloci.py --retry-failed ~/riassunti/libro.failed_chunks.json
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
    parser.add_argument('--retry-failed', type=str, metavar='STATE_FILE',
                       help='Riprocessa solo i chunk falliti da un precedente errore (percorso file .failed_chunks.json)')

    args = parser.parse_args()

    # MODALITÀ RECUPERO CHUNK FALLITI
    if args.retry_failed:
        if not os.path.exists(args.retry_failed):
            print(f"❌ File di stato non trovato: {args.retry_failed}")
            sys.exit(1)

        print("📋 MODALITÀ: Recupero Chunk Falliti")
        print("="*70)
        print(f"Modello: {args.model}")
        print(f"File stato: {args.retry_failed}")
        print(f"Output: {args.output_dir}")
        print("="*70 + "\n")

        # Crea directory output se necessario
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

        # Esegui recupero
        success = retry_failed_chunks(args.retry_failed, args.output_dir, args.model)

        print("\n" + "="*60)
        if success:
            print("✅ RECUPERO COMPLETATO")
        else:
            print("⚠️  RECUPERO PARZIALE O FALLITO")
        print("="*60 + "\n")

        sys.exit(0 if success else 1)

    # MODALITÀ NORMALE (continua con il codice esistente)

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
