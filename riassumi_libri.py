#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
riassumi_libri.py - CLI Tool per Riassunti di Libri via Ollama

Legge file EPUB o PDF, li analizza tramite Ollama locale e genera
riassunti dettagliati capitolo per capitolo in formato DOCX e Markdown.
"""

import os
import sys
import argparse
import time
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Dependencies
import requests
from tqdm import tqdm

# EPUB handling
try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    EPUB_SUPPORT = True
except ImportError:
    EPUB_SUPPORT = False
    print("⚠️  ebooklib o BeautifulSoup non disponibili. Supporto EPUB disabilitato.")

# PDF handling
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("⚠️  PyPDF2 non disponibile. Supporto PDF disabilitato.")

# DOCX generation
try:
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False
    print("⚠️  python-docx non disponibile. Generazione DOCX disabilitata.")


# ============================================================================
# CONFIGURAZIONE
# ============================================================================

VERSION = "1.2.0"
LAST_UPDATE = "2025-10-21"

DEFAULT_INPUT_DIR = os.path.expanduser("~/dariassumere")
DEFAULT_OUTPUT_DIR = os.path.expanduser("~/riassunti")
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_MIN_WORDS = 300
DEFAULT_LANGUAGE = "it"
OLLAMA_URL = "http://localhost:11434/api/generate"

# Chunking configuration
DEFAULT_CHUNK_SIZE = 12000  # caratteri (piccolo: 6000, medio: 12000, grande: 24000)
CHUNK_OVERLAP = 600         # caratteri

# Preset chunk sizes
CHUNK_PRESETS = {
    'piccolo': 6000,
    'medio': 12000,
    'grande': 24000
}

# Prompt templates
PROMPT_MAP = """Sei un analista testuale.
Il testo può essere in italiano o inglese, ma rispondi solo in italiano.
Crea un riassunto dettagliato del seguente frammento.

# Sintesi (400–600 parole)
# Temi chiave
# Personaggi/Concetti principali
# Citazioni (se presenti)
# Osservazioni sullo stile

FRAMMENTO:
{text}

RIASSUNTO IN ITALIANO:"""

PROMPT_REDUCE = """Unisci e armonizza i seguenti riassunti parziali del capitolo.
Rispondi in italiano, producendo un riassunto coerente (600–900 parole).

RIASSUNTI PARZIALI:
{summaries}

RIASSUNTO UNIFICATO IN ITALIANO:"""

PROMPT_GLOBAL = """Genera un riassunto complessivo in italiano basato sui seguenti riassunti dei capitoli:

{chapter_summaries}

Produce un documento strutturato con:
# Trama complessiva
# Temi e messaggi ricorrenti
# Evoluzione dei personaggi/idee
# Citazioni rappresentative
# Stile e tono
# Sintesi finale

RIASSUNTO COMPLESSIVO IN ITALIANO:"""


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

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


def chunk_text(text: str, max_size: int = DEFAULT_CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
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


def show_banner() -> None:
    """Mostra il banner iniziale con versione e data di aggiornamento."""
    print("\n" + "="*70)
    print("📚 RIASSUMI LIBRI - CLI Tool via Ollama")
    print("="*70)
    print(f"Versione: {VERSION}")
    print(f"Ultimo aggiornamento: {LAST_UPDATE}")
    print("="*70 + "\n")


def interactive_setup() -> Dict[str, any]:
    """
    Guida l'utente attraverso un setup interattivo.

    Returns:
        Dizionario con le configurazioni scelte dall'utente
    """
    print("🔧 CONFIGURAZIONE INIZIALE")
    print("-" * 70)
    print("Premi INVIO per usare i valori predefiniti\n")

    config = {}

    # Modello Ollama
    print(f"📦 Modello Ollama da usare:")
    print(f"   Suggerimenti: qwen3:8b (veloce), qwen3:30b (preciso), llama3:8b")
    model = input(f"   Modello [{DEFAULT_MODEL}]: ").strip()
    config['model'] = model if model else DEFAULT_MODEL

    # Directory input
    print(f"\n📂 Directory contenente i libri da riassumere:")
    input_dir = input(f"   Path [{DEFAULT_INPUT_DIR}]: ").strip()
    config['input_dir'] = os.path.expanduser(input_dir) if input_dir else DEFAULT_INPUT_DIR

    # Directory output
    print(f"\n📁 Directory dove salvare i riassunti:")
    output_dir = input(f"   Path [{DEFAULT_OUTPUT_DIR}]: ").strip()
    config['output_dir'] = os.path.expanduser(output_dir) if output_dir else DEFAULT_OUTPUT_DIR

    # Parole minime per capitolo
    print(f"\n📝 Numero minimo di parole per considerare un capitolo valido:")
    print(f"   Valori bassi (100-200) includono più sezioni, valori alti (500+) solo capitoli sostanziali")
    min_words_str = input(f"   Parole minime [{DEFAULT_MIN_WORDS}]: ").strip()
    try:
        config['min_words'] = int(min_words_str) if min_words_str else DEFAULT_MIN_WORDS
    except ValueError:
        print(f"   ⚠️  Valore non valido, uso default: {DEFAULT_MIN_WORDS}")
        config['min_words'] = DEFAULT_MIN_WORDS

    # Dimensione chunk
    print(f"\n📏 Dimensione blocchi di testo (chunk) per l'elaborazione:")
    print(f"   IMPATTO SULLA VELOCITÀ:")
    print(f"   - PICCOLO (6k):  Più chiamate a Ollama, più lento ma usa meno RAM")
    print(f"   - MEDIO (12k):   Bilanciato (consigliato)")
    print(f"   - GRANDE (24k):  Meno chiamate a Ollama, più veloce ma usa più RAM")
    print(f"   ")
    print(f"   Chunk più grandi = MENO chiamate totali = PIÙ VELOCE")
    print(f"   (Ogni capitolo lungo viene diviso in chunk per elaborazione)")
    chunk_choice = input(f"   Dimensione [piccolo/medio/grande]: ").strip().lower()

    if chunk_choice in CHUNK_PRESETS:
        config['chunk_size'] = CHUNK_PRESETS[chunk_choice]
        print(f"   ✅ Impostato: {chunk_choice} ({config['chunk_size']} caratteri)")
    else:
        config['chunk_size'] = DEFAULT_CHUNK_SIZE
        print(f"   ℹ️  Uso default: medio ({DEFAULT_CHUNK_SIZE} caratteri)")

    # Selezione file
    print(f"\n🎯 Vuoi elaborare:")
    print(f"   1. Tutti i file nella directory")
    print(f"   2. Solo file specifici (selezione interattiva)")
    choice = input(f"   Scelta [1]: ").strip()
    config['select_files'] = (choice == '2')

    print("\n" + "="*70)
    print("✅ CONFIGURAZIONE COMPLETATA")
    print("="*70 + "\n")

    return config


# ============================================================================
# OLLAMA INTERACTION
# ============================================================================

def call_ollama(prompt: str, model: str = DEFAULT_MODEL, temperature: float = 0.3,
                max_retries: int = 3) -> Optional[str]:
    """
    Chiama l'API Ollama con retry logic.

    Args:
        prompt: Il prompt da inviare
        model: Nome del modello Ollama
        temperature: Temperatura per la generazione
        max_retries: Numero massimo di tentativi

    Returns:
        Testo generato o None in caso di errore
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": 128000
        }
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=300)
            response.raise_for_status()

            result = response.json()
            return result.get("response", "").strip()

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)  # 2s, 4s, 8s
                print(f"⚠️  Tentativo {attempt + 1} fallito: {e}")
                print(f"   Riprovo tra {wait_time} secondi...")
                time.sleep(wait_time)
            else:
                print(f"❌ Errore Ollama dopo {max_retries} tentativi: {e}")
                return None
        except Exception as e:
            print(f"❌ Errore imprevisto: {e}")
            return None

    return None


# ============================================================================
# EPUB EXTRACTION
# ============================================================================

def extract_chapters_from_epub(filepath: str, min_words: int = DEFAULT_MIN_WORDS) -> List[Dict[str, str]]:
    """
    Estrae i capitoli da un file EPUB.

    Args:
        filepath: Percorso del file EPUB
        min_words: Numero minimo di parole per considerare un capitolo valido

    Returns:
        Lista di dizionari con 'title' e 'text' per ogni capitolo
    """
    if not EPUB_SUPPORT:
        print("❌ Supporto EPUB non disponibile. Installa: pip install ebooklib beautifulsoup4")
        return []

    try:
        book = epub.read_epub(filepath)
        chapters = []

        # Ottieni gli item dello spine (ordine di lettura)
        spine_items = [book.get_item_with_id(item_id) for item_id, _ in book.spine]

        for idx, item in enumerate(spine_items, 1):
            if item is None:
                continue

            # Estrai contenuto HTML
            try:
                content = item.get_content()
                soup = BeautifulSoup(content, 'html.parser')

                # Rimuovi elementi non testuali
                for tag in soup(['script', 'style', 'svg', 'img']):
                    tag.decompose()

                # Estrai testo
                text = soup.get_text(separator='\n', strip=True)

                # Verifica lunghezza minima
                if count_words(text) < min_words:
                    continue

                # Prova a estrarre il titolo
                title = f"Capitolo {idx}"
                h1 = soup.find(['h1', 'h2', 'h3'])
                if h1:
                    title = h1.get_text(strip=True) or title

                chapters.append({
                    'title': title,
                    'text': text
                })

            except Exception as e:
                print(f"⚠️  Errore nell'elaborazione item {idx}: {e}")
                continue

        return chapters

    except Exception as e:
        print(f"❌ Errore nella lettura EPUB: {e}")
        return []


# ============================================================================
# PDF EXTRACTION
# ============================================================================

def extract_chapters_from_pdf(filepath: str, min_words: int = DEFAULT_MIN_WORDS) -> List[Dict[str, str]]:
    """
    Estrae i capitoli da un file PDF.

    Args:
        filepath: Percorso del file PDF
        min_words: Numero minimo di parole per considerare un capitolo valido

    Returns:
        Lista di dizionari con 'title' e 'text' per ogni capitolo
    """
    if not PDF_SUPPORT:
        print("❌ Supporto PDF non disponibile. Installa: pip install PyPDF2")
        return []

    try:
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            full_text = ""

            # Estrai tutto il testo
            for page in reader.pages:
                try:
                    full_text += page.extract_text() + "\n"
                except Exception as e:
                    print(f"⚠️  Errore nell'estrazione pagina: {e}")
                    continue

        # Tenta di dividere in capitoli usando pattern comuni
        chapter_patterns = [
            r'(?:^|\n)(?:CAPITOLO|Capitolo|CHAPTER|Chapter)\s+(\d+|[IVXLCDM]+)[:\.\s]+(.*?)(?=\n(?:CAPITOLO|Capitolo|CHAPTER|Chapter)|\Z)',
            r'(?:^|\n)(\d+)\s*[\.\)]\s+(.*?)(?=\n\d+\s*[\.\)]|\Z)',
        ]

        chapters = []
        found_chapters = False

        for pattern in chapter_patterns:
            matches = list(re.finditer(pattern, full_text, re.MULTILINE | re.DOTALL))
            if matches:
                for idx, match in enumerate(matches, 1):
                    title = match.group(0).split('\n')[0].strip()

                    # Trova il testo del capitolo (dal match corrente al prossimo)
                    start_pos = match.start()
                    end_pos = matches[idx].start() if idx < len(matches) else len(full_text)
                    text = full_text[start_pos:end_pos].strip()

                    if count_words(text) >= min_words:
                        chapters.append({
                            'title': title if title else f"Capitolo {idx}",
                            'text': text
                        })

                if chapters:
                    found_chapters = True
                    break

        # Se non trova capitoli, divide in blocchi di dimensione fissa
        if not found_chapters:
            print("⚠️  Nessun pattern di capitolo trovato. Suddivisione in blocchi...")
            words = full_text.split()
            chunk_size = 3000  # parole per blocco

            for i in range(0, len(words), chunk_size):
                chunk_words = words[i:i + chunk_size]
                text = ' '.join(chunk_words)

                if count_words(text) >= min_words:
                    chapters.append({
                        'title': f"Sezione {len(chapters) + 1}",
                        'text': text
                    })

        return chapters

    except Exception as e:
        print(f"❌ Errore nella lettura PDF: {e}")
        return []


# ============================================================================
# SUMMARIZATION
# ============================================================================

def summarize_chapter(chapter_text: str, chapter_title: str, model: str = DEFAULT_MODEL,
                     chunk_size: int = DEFAULT_CHUNK_SIZE) -> Optional[str]:
    """
    Riassume un capitolo usando MAP-REDUCE se necessario.

    Args:
        chapter_text: Testo del capitolo
        chapter_title: Titolo del capitolo
        model: Modello Ollama da usare
        chunk_size: Dimensione massima dei chunk in caratteri

    Returns:
        Riassunto del capitolo o None
    """
    # Se il testo è abbastanza corto, usa direttamente MAP
    if len(chapter_text) <= chunk_size:
        prompt = PROMPT_MAP.format(text=chapter_text)
        return call_ollama(prompt, model)

    # Altrimenti usa MAP-REDUCE
    print(f"   📄 Capitolo lungo ({len(chapter_text)} char), applico MAP-REDUCE...")

    # MAP: riassumi ogni chunk
    chunks = chunk_text(chapter_text, max_size=chunk_size)
    partial_summaries = []

    for idx, chunk in enumerate(chunks, 1):
        print(f"      Elaboro chunk {idx}/{len(chunks)}...")
        prompt = PROMPT_MAP.format(text=chunk)
        summary = call_ollama(prompt, model)

        if summary:
            partial_summaries.append(summary)
        else:
            print(f"⚠️  Chunk {idx} saltato per errore")

    if not partial_summaries:
        print("❌ Nessun riassunto parziale generato")
        return None

    # REDUCE: unisci i riassunti parziali
    print(f"   🔄 Unisco {len(partial_summaries)} riassunti parziali...")
    combined = "\n\n---\n\n".join(partial_summaries)
    prompt = PROMPT_REDUCE.format(summaries=combined)

    return call_ollama(prompt, model)


def generate_global_summary(chapter_summaries: List[Dict[str, str]], model: str = DEFAULT_MODEL) -> Optional[str]:
    """
    Genera un riassunto complessivo del libro.

    Args:
        chapter_summaries: Lista di dizionari con 'title' e 'summary'
        model: Modello Ollama da usare

    Returns:
        Riassunto complessivo o None
    """
    summaries_text = ""
    for item in chapter_summaries:
        summaries_text += f"## {item['title']}\n{item['summary']}\n\n"

    prompt = PROMPT_GLOBAL.format(chapter_summaries=summaries_text)
    return call_ollama(prompt, model)


# ============================================================================
# OUTPUT GENERATION
# ============================================================================

def write_docx_output(book_title: str, chapter_summaries: List[Dict[str, str]],
                     global_summary: str, output_path: str) -> bool:
    """
    Genera un file DOCX con i riassunti.

    Args:
        book_title: Titolo del libro
        chapter_summaries: Lista di riassunti dei capitoli
        global_summary: Riassunto complessivo
        output_path: Percorso del file di output

    Returns:
        True se successo, False altrimenti
    """
    if not DOCX_SUPPORT:
        print("⚠️  Generazione DOCX non disponibile. Installa: pip install python-docx")
        return False

    try:
        doc = Document()

        # Titolo principale
        title = doc.add_heading(f'Riassunto dettagliato — {book_title}', 0)
        title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        # Indice
        doc.add_heading('Indice', level=1)
        for idx, item in enumerate(chapter_summaries, 1):
            doc.add_paragraph(f"{idx}. {item['title']}", style='List Number')

        doc.add_page_break()

        # Capitoli
        for item in chapter_summaries:
            doc.add_heading(item['title'], level=1)
            doc.add_paragraph(item['summary'])
            doc.add_paragraph()  # Spazio

        doc.add_page_break()

        # Sintesi complessiva
        doc.add_heading('Sintesi complessiva del libro', level=1)
        doc.add_paragraph(global_summary)

        # Salva
        doc.save(output_path)
        return True

    except Exception as e:
        print(f"❌ Errore nella generazione DOCX: {e}")
        return False


def write_md_output(book_title: str, chapter_summaries: List[Dict[str, str]],
                   global_summary: str, output_path: str) -> bool:
    """
    Genera un file Markdown con i riassunti.

    Args:
        book_title: Titolo del libro
        chapter_summaries: Lista di riassunti dei capitoli
        global_summary: Riassunto complessivo
        output_path: Percorso del file di output

    Returns:
        True se successo, False altrimenti
    """
    try:
        content = f"# Riassunto dettagliato — {book_title}\n\n"

        # Indice
        content += "## Indice\n\n"
        for idx, item in enumerate(chapter_summaries, 1):
            content += f"{idx}. {item['title']}\n"
        content += "\n---\n\n"

        # Capitoli
        for item in chapter_summaries:
            content += f"## {item['title']}\n\n"
            content += f"{item['summary']}\n\n"
            content += "---\n\n"

        # Sintesi complessiva
        content += "## Sintesi complessiva del libro\n\n"
        content += f"{global_summary}\n"

        # Scrivi file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return True

    except Exception as e:
        print(f"❌ Errore nella generazione Markdown: {e}")
        return False


# ============================================================================
# CHECKPOINT SYSTEM
# ============================================================================

def get_checkpoint_path(book_title: str, output_dir: str) -> str:
    """
    Ottiene il percorso del file di checkpoint per un libro.

    Args:
        book_title: Titolo del libro (sanitized)
        output_dir: Directory di output

    Returns:
        Percorso del file di checkpoint
    """
    return os.path.join(output_dir, f".checkpoint_{book_title}.json")


def save_checkpoint(book_title: str, output_dir: str, chapter_summaries: List[Dict[str, str]],
                   current_index: int, total_chapters: int, model: str, min_words: int,
                   chunk_size: int) -> None:
    """
    Salva lo stato corrente dell'elaborazione.

    Args:
        book_title: Titolo del libro
        output_dir: Directory di output
        chapter_summaries: Riassunti dei capitoli completati
        current_index: Indice del capitolo corrente
        total_chapters: Numero totale di capitoli
        model: Modello usato
        min_words: Parole minime per capitolo
        chunk_size: Dimensione chunk in caratteri
    """
    checkpoint_path = get_checkpoint_path(book_title, output_dir)

    checkpoint_data = {
        'book_title': book_title,
        'timestamp': time.time(),
        'model': model,
        'min_words': min_words,
        'chunk_size': chunk_size,
        'total_chapters': total_chapters,
        'current_index': current_index,
        'chapter_summaries': chapter_summaries
    }

    try:
        with open(checkpoint_path, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️  Impossibile salvare checkpoint: {e}")


def load_checkpoint(book_title: str, output_dir: str) -> Optional[Dict]:
    """
    Carica un checkpoint esistente.

    Args:
        book_title: Titolo del libro
        output_dir: Directory di output

    Returns:
        Dati del checkpoint o None se non esiste
    """
    checkpoint_path = get_checkpoint_path(book_title, output_dir)

    if not os.path.exists(checkpoint_path):
        return None

    try:
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Errore nel caricamento checkpoint: {e}")
        return None


def remove_checkpoint(book_title: str, output_dir: str) -> None:
    """
    Rimuove il file di checkpoint.

    Args:
        book_title: Titolo del libro
        output_dir: Directory di output
    """
    checkpoint_path = get_checkpoint_path(book_title, output_dir)
    try:
        if os.path.exists(checkpoint_path):
            os.remove(checkpoint_path)
    except Exception as e:
        print(f"⚠️  Impossibile rimuovere checkpoint: {e}")


def ask_resume_checkpoint(checkpoint: Dict) -> bool:
    """
    Chiede all'utente se vuole riprendere da un checkpoint.

    Args:
        checkpoint: Dati del checkpoint

    Returns:
        True se l'utente vuole riprendere, False altrimenti
    """
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(checkpoint['timestamp']))
    completed = len(checkpoint['chapter_summaries'])
    total = checkpoint['total_chapters']
    percentage = (completed / total * 100) if total > 0 else 0

    # Trova il nome del preset chunk per mostrarlo
    chunk_size = checkpoint.get('chunk_size', DEFAULT_CHUNK_SIZE)
    chunk_name = 'personalizzato'
    for name, size in CHUNK_PRESETS.items():
        if size == chunk_size:
            chunk_name = name
            break

    print("\n" + "="*70)
    print("🔄 LAVORO INTERROTTO TROVATO")
    print("="*70)
    print(f"Libro: {checkpoint['book_title']}")
    print(f"Data interruzione: {timestamp}")
    print(f"Progresso: {completed}/{total} capitoli ({percentage:.1f}%)")
    print(f"Modello: {checkpoint['model']}")
    print(f"Chunk size: {chunk_name} ({chunk_size} caratteri)")
    print("="*70)

    while True:
        choice = input("\nVuoi riprendere da qui? (s/n) [s]: ").strip().lower()
        if choice in ['', 's', 'si', 'y', 'yes']:
            return True
        elif choice in ['n', 'no']:
            return False
        else:
            print("⚠️  Risposta non valida. Inserisci 's' o 'n'")


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def process_book(filepath: str, output_dir: str, model: str = DEFAULT_MODEL,
                min_words: int = DEFAULT_MIN_WORDS, chunk_size: int = DEFAULT_CHUNK_SIZE) -> bool:
    """
    Elabora un singolo libro con supporto per checkpoint/resume.

    Args:
        filepath: Percorso del file del libro
        output_dir: Directory di output
        model: Modello Ollama da usare
        min_words: Numero minimo di parole per capitolo
        chunk_size: Dimensione chunk in caratteri

    Returns:
        True se successo, False altrimenti
    """
    filepath = Path(filepath)
    extension = filepath.suffix.lower()
    book_title = sanitize_filename(filepath.name)

    print(f"\n{'='*60}")
    print(f"📚 Elaborazione: {filepath.name}")
    print(f"{'='*60}\n")

    # Controlla se esiste un checkpoint
    checkpoint = load_checkpoint(book_title, output_dir)
    resume_from_checkpoint = False
    start_index = 0
    chapter_summaries = []

    if checkpoint:
        # Verifica che i parametri siano compatibili
        checkpoint_chunk_size = checkpoint.get('chunk_size', DEFAULT_CHUNK_SIZE)
        if (checkpoint['model'] == model and
            checkpoint['min_words'] == min_words and
            checkpoint_chunk_size == chunk_size):
            if ask_resume_checkpoint(checkpoint):
                resume_from_checkpoint = True
                chapter_summaries = checkpoint['chapter_summaries']
                start_index = len(chapter_summaries)
                print(f"\n✅ Ripresa dal capitolo {start_index + 1}\n")
            else:
                print("\n🔄 Ricomincio da capo...\n")
                remove_checkpoint(book_title, output_dir)
        else:
            print("\n⚠️  Parametri diversi dal checkpoint, ricomincio da capo...\n")
            remove_checkpoint(book_title, output_dir)

    # [1/4] Estrazione capitoli
    if not resume_from_checkpoint:
        print(f"[1/4] Estrazione capitoli da {filepath.name}")
    else:
        print(f"[1/4] Ricaricamento struttura capitoli")

    if extension == '.epub':
        chapters = extract_chapters_from_epub(str(filepath), min_words)
    elif extension == '.pdf':
        chapters = extract_chapters_from_pdf(str(filepath), min_words)
    else:
        print(f"❌ Formato non supportato: {extension}")
        return False

    if not chapters:
        print("❌ Nessun capitolo estratto")
        return False

    print(f"✅ Trovati {len(chapters)} capitoli\n")

    # Verifica che il numero di capitoli corrisponda
    if resume_from_checkpoint and checkpoint['total_chapters'] != len(chapters):
        print("⚠️  Numero di capitoli diverso dal checkpoint, ricomincio da capo...\n")
        remove_checkpoint(book_title, output_dir)
        chapter_summaries = []
        start_index = 0
        resume_from_checkpoint = False

    # [2/4] Riassunto capitoli
    print(f"[2/4] Riassunto capitoli")

    if resume_from_checkpoint:
        print(f"   ⏭️  Saltati {start_index} capitoli già elaborati\n")

    with tqdm(total=len(chapters), desc="Elaborazione capitoli", unit="cap", initial=start_index) as pbar:
        for idx, chapter in enumerate(chapters, 1):
            # Salta i capitoli già elaborati
            if idx <= start_index:
                continue

            print(f"\n   📖 Capitolo {idx}/{len(chapters)}: {chapter['title']}")

            summary = summarize_chapter(chapter['text'], chapter['title'], model, chunk_size)

            if summary:
                chapter_summaries.append({
                    'title': chapter['title'],
                    'summary': summary
                })
                print(f"   ✅ Completato")

                # Salva checkpoint dopo ogni capitolo completato
                save_checkpoint(book_title, output_dir, chapter_summaries,
                               idx, len(chapters), model, min_words, chunk_size)
            else:
                print(f"   ⚠️  Saltato per errore")

            pbar.update(1)

    if not chapter_summaries:
        print("\n❌ Nessun riassunto generato")
        remove_checkpoint(book_title, output_dir)
        return False

    # [3/4] Riassunto globale
    print(f"\n[3/4] Generazione riassunto complessivo")
    global_summary = generate_global_summary(chapter_summaries, model)

    if not global_summary:
        print("⚠️  Riassunto complessivo non generato, uso sintesi base")
        global_summary = "Riassunto complessivo non disponibile."
    else:
        print("✅ Riassunto complessivo generato")

    # [4/4] Scrittura output
    print(f"\n[4/4] Scrittura file di output")

    docx_path = os.path.join(output_dir, f"{book_title}.riassunto.docx")
    md_path = os.path.join(output_dir, f"{book_title}.riassunto.md")

    docx_ok = write_docx_output(book_title, chapter_summaries, global_summary, docx_path)
    md_ok = write_md_output(book_title, chapter_summaries, global_summary, md_path)

    if docx_ok:
        print(f"✅ DOCX: {docx_path}")
    if md_ok:
        print(f"✅ MD: {md_path}")

    # Rimuovi checkpoint se completato con successo
    if docx_ok or md_ok:
        remove_checkpoint(book_title, output_dir)

    return docx_ok or md_ok


def select_files_interactive(files: List[Path]) -> List[Path]:
    """
    Permette all'utente di selezionare interattivamente i file da elaborare.

    Args:
        files: Lista di file disponibili

    Returns:
        Lista di file selezionati
    """
    print(f"\n📋 File disponibili ({len(files)}):")
    print("-" * 70)
    for idx, filepath in enumerate(files, 1):
        print(f"   {idx}. {filepath.name}")
    print("-" * 70)

    print("\nInserisci i numeri dei file da elaborare separati da virgola")
    print("(es: 1,3,5 oppure 'all' per tutti, 'q' per uscire)")

    while True:
        selection = input("\nSelezione: ").strip().lower()

        if selection == 'q':
            print("Operazione annullata.")
            sys.exit(0)

        if selection == 'all':
            return files

        try:
            indices = [int(x.strip()) for x in selection.split(',')]
            selected = []

            for idx in indices:
                if 1 <= idx <= len(files):
                    selected.append(files[idx - 1])
                else:
                    print(f"⚠️  Indice {idx} non valido (range: 1-{len(files)})")
                    continue

            if selected:
                print(f"\n✅ Selezionati {len(selected)} file:")
                for f in selected:
                    print(f"   - {f.name}")
                return selected
            else:
                print("⚠️  Nessun file selezionato. Riprova.")

        except ValueError:
            print("⚠️  Formato non valido. Usa numeri separati da virgola (es: 1,2,3)")


def main():
    """Funzione principale del programma."""
    # Mostra sempre il banner all'avvio
    show_banner()

    parser = argparse.ArgumentParser(
        description="CLI Tool per Riassunti di Libri via Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python riassumi_libri.py --interactive
  python riassumi_libri.py --model qwen3:30b --min_words 500
  python riassumi_libri.py --input_dir /path/to/books --output_dir /path/to/output
        """
    )

    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Modalità interattiva con domande guidate')
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL,
                       help=f'Modello Ollama da usare (default: {DEFAULT_MODEL})')
    parser.add_argument('--input_dir', type=str, default=DEFAULT_INPUT_DIR,
                       help=f'Directory input (default: {DEFAULT_INPUT_DIR})')
    parser.add_argument('--output_dir', type=str, default=DEFAULT_OUTPUT_DIR,
                       help=f'Directory output (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--min_words', type=int, default=DEFAULT_MIN_WORDS,
                       help=f'Parole minime per capitolo (default: {DEFAULT_MIN_WORDS})')
    parser.add_argument('--chunk_size', type=int, default=DEFAULT_CHUNK_SIZE,
                       help=f'Dimensione chunk in caratteri (default: {DEFAULT_CHUNK_SIZE})')
    parser.add_argument('--language', type=str, default=DEFAULT_LANGUAGE,
                       help=f'Lingua output (default: {DEFAULT_LANGUAGE})')

    args = parser.parse_args()

    # Modalità interattiva
    select_files = False
    if args.interactive:
        config = interactive_setup()
        args.model = config['model']
        args.input_dir = config['input_dir']
        args.output_dir = config['output_dir']
        args.min_words = config['min_words']
        args.chunk_size = config['chunk_size']
        select_files = config['select_files']

    # Trova il nome del preset chunk per mostrarlo
    chunk_name = 'personalizzato'
    for name, size in CHUNK_PRESETS.items():
        if size == args.chunk_size:
            chunk_name = name
            break

    print("📋 PARAMETRI DI ESECUZIONE")
    print("="*70)
    print(f"Modello: {args.model}")
    print(f"Input: {args.input_dir}")
    print(f"Output: {args.output_dir}")
    print(f"Min parole/capitolo: {args.min_words}")
    print(f"Chunk size: {chunk_name} ({args.chunk_size} caratteri)")
    print("="*70 + "\n")

    # Verifica directory input
    if not os.path.exists(args.input_dir):
        print(f"❌ Directory input non trovata: {args.input_dir}")
        print(f"   Crea la directory con: mkdir -p {args.input_dir}")
        sys.exit(1)

    if not os.path.isdir(args.input_dir):
        print(f"❌ Il percorso input non è una directory: {args.input_dir}")
        sys.exit(1)

    # Scansiona file prima di fare altre verifiche
    print(f"🔍 Scansione {args.input_dir}")
    files = []

    for ext in ['.epub', '.pdf']:
        files.extend(Path(args.input_dir).glob(f'*{ext}'))

    if not files:
        print("❌ Nessun file EPUB o PDF trovato nella directory input")
        print(f"   Aggiungi file .epub o .pdf in: {args.input_dir}")
        sys.exit(1)

    print(f"✅ Trovati {len(files)} file: {', '.join([f.name for f in files])}\n")

    # Selezione file interattiva se richiesto
    if select_files:
        files = select_files_interactive(files)

    # Crea directory output
    try:
        ensure_directory(args.output_dir)
    except Exception as e:
        print(f"❌ Impossibile creare directory output: {e}")
        sys.exit(1)

    # Verifica che Ollama sia raggiungibile (solo dopo aver verificato che ci sono file)
    print("🔍 Verifica connessione a Ollama...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        print("✅ Ollama raggiungibile\n")
    except Exception as e:
        print(f"❌ Errore connessione Ollama: {e}")
        print("   Assicurati che Ollama sia in esecuzione su http://localhost:11434")
        sys.exit(1)

    # Elabora ogni file
    success_count = 0

    for idx, filepath in enumerate(files, 1):
        print(f"\n{'#'*60}")
        print(f"FILE {idx}/{len(files)}")
        print(f"{'#'*60}")

        try:
            if process_book(str(filepath), args.output_dir, args.model, args.min_words, args.chunk_size):
                success_count += 1
        except Exception as e:
            print(f"\n❌ Errore nell'elaborazione: {e}")
            continue

    # Riepilogo finale
    print(f"\n{'='*60}")
    print(f"✅ OPERAZIONE COMPLETATA")
    print(f"{'='*60}")
    print(f"File elaborati: {success_count}/{len(files)}")
    print(f"Output salvati in: {args.output_dir}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
