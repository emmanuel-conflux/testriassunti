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
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime

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

DEFAULT_INPUT_DIR = r"C:\dariassumere"
DEFAULT_OUTPUT_DIR = r"C:\riassunti"
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_MIN_WORDS = 300
DEFAULT_LANGUAGE = "it"
OLLAMA_URL = "http://localhost:11434/api/generate"

# Chunking configuration
MAX_CHUNK_SIZE = 12000  # caratteri
CHUNK_OVERLAP = 600     # caratteri

# Resume configuration
HASH_PREFIX_LENGTH = 8000  # caratteri per calcolare hash
HASH_OUTPUT_LENGTH = 8     # caratteri hash nel nome file
HTTP_TIMEOUT = 180         # secondi per chiamate Ollama

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


def chapter_hash(text: str) -> str:
    """
    Calcola hash SHA1 delle prime 8000 battute del testo.

    Args:
        text: Testo del capitolo

    Returns:
        Primi 8 caratteri dell'hash SHA1
    """
    prefix = text[:HASH_PREFIX_LENGTH]
    hash_obj = hashlib.sha1(prefix.encode('utf-8'))
    return hash_obj.hexdigest()[:HASH_OUTPUT_LENGTH]


def ensure_resume_dirs(book_output_dir: str) -> None:
    """
    Crea la struttura di directory per il resume.

    Args:
        book_output_dir: Directory principale del libro
    """
    Path(book_output_dir).mkdir(parents=True, exist_ok=True)
    Path(book_output_dir, "chapters").mkdir(parents=True, exist_ok=True)


def load_state(state_file: str) -> Optional[Dict]:
    """
    Carica il file di stato se esistente e valido.

    Args:
        state_file: Percorso del file state.json

    Returns:
        Dizionario con lo stato o None se non esiste/corrotto
    """
    if not os.path.exists(state_file):
        return None

    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)

        # Validazione base
        required_keys = ['book_title', 'total_chapters', 'completed', 'chapter_hashes', 'model']
        if not all(key in state for key in required_keys):
            print("⚠️  File state.json corrotto, verrà rigenerato")
            return None

        return state

    except (json.JSONDecodeError, Exception) as e:
        print(f"⚠️  Errore lettura state.json: {e}, verrà rigenerato")
        return None


def save_state(state_file: str, state: Dict) -> None:
    """
    Salva il file di stato in modo atomico.

    Args:
        state_file: Percorso del file state.json
        state: Dizionario con lo stato da salvare
    """
    # Aggiorna timestamp
    state['timestamp'] = datetime.now().isoformat()

    # Salvataggio atomico: scrivi su temp file poi rinomina
    temp_file = state_file + '.tmp'
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        # Rinomina atomicamente
        os.replace(temp_file, state_file)

    except Exception as e:
        print(f"⚠️  Errore salvataggio state.json: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)


def chapter_filename(chapter_num: int, chapter_title: str, chapter_hash: str) -> str:
    """
    Genera il nome del file per un capitolo.

    Args:
        chapter_num: Numero del capitolo (1-based)
        chapter_title: Titolo del capitolo
        chapter_hash: Hash a 8 caratteri del capitolo

    Returns:
        Nome del file nel formato NN_<titolo-sanitizzato>_<hash8>.md
    """
    # Sanitizza il titolo
    title_clean = re.sub(r'[<>:"/\\|?*]', '_', chapter_title)
    title_clean = title_clean.strip()[:50]  # Limita lunghezza

    # Formato: NN_titolo_hash8.md
    return f"{chapter_num:02d}_{title_clean}_{chapter_hash}.md"


def should_skip_chapter(chapter_idx: int, chapter_text: str, state: Dict,
                       chapters_dir: str) -> Tuple[bool, str]:
    """
    Verifica se un capitolo può essere saltato (già elaborato e invariato).

    Args:
        chapter_idx: Indice del capitolo (1-based)
        chapter_text: Testo del capitolo
        state: Stato corrente
        chapters_dir: Directory dei capitoli

    Returns:
        Tuple (skip: bool, hash: str)
    """
    # Calcola hash corrente
    current_hash = chapter_hash(chapter_text)

    # Verifica se il capitolo è in completed
    if chapter_idx not in state['completed']:
        return False, current_hash

    # Verifica se l'hash coincide
    stored_hash = state['chapter_hashes'].get(str(chapter_idx))
    if stored_hash != current_hash:
        print(f"   ⚠️  Hash cambiato per capitolo {chapter_idx} (era {stored_hash}, ora {current_hash})")
        return False, current_hash

    # Verifica se esiste il file .md corrispondente
    # Cerca file che iniziano con NN_ e contengono l'hash
    pattern = f"{chapter_idx:02d}_*_{current_hash}.md"
    matching_files = list(Path(chapters_dir).glob(pattern))

    if not matching_files:
        print(f"   ⚠️  File mancante per capitolo {chapter_idx}")
        return False, current_hash

    # Tutto OK, possiamo saltare
    return True, current_hash


def rebuild_state_from_chapters(chapters_dir: str, book_title: str,
                                total_chapters: int, model: str) -> Dict:
    """
    Ricostruisce lo stato scansionando i file .md esistenti.

    Args:
        chapters_dir: Directory dei capitoli
        book_title: Titolo del libro
        total_chapters: Numero totale di capitoli
        model: Modello usato

    Returns:
        Dizionario con lo stato ricostruito
    """
    state = {
        'book_title': book_title,
        'total_chapters': total_chapters,
        'completed': [],
        'chapter_hashes': {},
        'model': model,
        'timestamp': datetime.now().isoformat()
    }

    # Scansiona directory chapters
    if not os.path.exists(chapters_dir):
        return state

    # Pattern: NN_*_HASH8.md
    pattern = re.compile(r'^(\d{2})_.*_([a-f0-9]{8})\.md$')

    for filename in os.listdir(chapters_dir):
        match = pattern.match(filename)
        if match:
            chapter_num = int(match.group(1))
            chapter_hash = match.group(2)

            if chapter_num not in state['completed']:
                state['completed'].append(chapter_num)
                state['chapter_hashes'][str(chapter_num)] = chapter_hash

    # Ordina completed
    state['completed'].sort()

    print(f"   ℹ️  Ricostruiti {len(state['completed'])} capitoli dallo stato precedente")
    return state


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
            "num_ctx": 32768,
            "num_predict": 2048
        }
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=HTTP_TIMEOUT)
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

def summarize_chapter(chapter_text: str, chapter_title: str, model: str = DEFAULT_MODEL) -> Optional[str]:
    """
    Riassume un capitolo usando MAP-REDUCE se necessario.

    Args:
        chapter_text: Testo del capitolo
        chapter_title: Titolo del capitolo
        model: Modello Ollama da usare

    Returns:
        Riassunto del capitolo o None
    """
    # Se il testo è abbastanza corto, usa direttamente MAP
    if len(chapter_text) <= MAX_CHUNK_SIZE:
        prompt = PROMPT_MAP.format(text=chapter_text)
        return call_ollama(prompt, model)

    # Altrimenti usa MAP-REDUCE
    print(f"   📄 Capitolo lungo ({len(chapter_text)} char), applico MAP-REDUCE...")

    # MAP: riassumi ogni chunk
    chunks = chunk_text(chapter_text)
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
# CHAPTER SUMMARY PERSISTENCE
# ============================================================================

def save_chapter_summary(chapters_dir: str, chapter_num: int, chapter_title: str,
                        chapter_hash: str, summary: str) -> bool:
    """
    Salva il riassunto di un singolo capitolo.

    Args:
        chapters_dir: Directory dei capitoli
        chapter_num: Numero del capitolo (1-based)
        chapter_title: Titolo del capitolo
        chapter_hash: Hash del capitolo
        summary: Riassunto da salvare

    Returns:
        True se successo, False altrimenti
    """
    try:
        filename = chapter_filename(chapter_num, chapter_title, chapter_hash)
        filepath = os.path.join(chapters_dir, filename)

        # Crea contenuto Markdown
        content = f"# {chapter_title}\n\n{summary}\n"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return True

    except Exception as e:
        print(f"❌ Errore salvataggio capitolo {chapter_num}: {e}")
        return False


def load_chapter_summaries(chapters_dir: str, total_chapters: int) -> List[Dict[str, str]]:
    """
    Carica tutti i riassunti dei capitoli dalla directory.

    Args:
        chapters_dir: Directory dei capitoli
        total_chapters: Numero totale di capitoli

    Returns:
        Lista di dizionari con 'title' e 'summary' per ogni capitolo
    """
    summaries = []

    # Pattern: NN_*_HASH8.md
    pattern = re.compile(r'^(\d{2})_(.*)_([a-f0-9]{8})\.md$')

    # Leggi tutti i file e organizzali per numero capitolo
    chapter_files = {}
    for filename in os.listdir(chapters_dir):
        match = pattern.match(filename)
        if match:
            chapter_num = int(match.group(1))
            chapter_files[chapter_num] = os.path.join(chapters_dir, filename)

    # Carica in ordine
    for i in range(1, total_chapters + 1):
        if i in chapter_files:
            try:
                with open(chapter_files[i], 'r', encoding='utf-8') as f:
                    content = f.read()

                # Estrai titolo e contenuto
                lines = content.split('\n', 1)
                title = lines[0].strip('# ').strip() if lines else f"Capitolo {i}"
                summary_text = lines[1].strip() if len(lines) > 1 else ""

                summaries.append({
                    'title': title,
                    'summary': summary_text
                })

            except Exception as e:
                print(f"⚠️  Errore caricamento capitolo {i}: {e}")
                summaries.append({
                    'title': f"Capitolo {i}",
                    'summary': "[Contenuto non disponibile]"
                })
        else:
            summaries.append({
                'title': f"Capitolo {i}",
                'summary': "[Capitolo non elaborato]"
            })

    return summaries


# ============================================================================
# OUTPUT GENERATION
# ============================================================================

def get_available_filename(base_path: str) -> str:
    """
    Trova un nome file disponibile, aggiungendo suffisso -1, -2, ecc. se necessario.

    Args:
        base_path: Percorso del file desiderato

    Returns:
        Percorso disponibile
    """
    if not os.path.exists(base_path):
        return base_path

    # File esiste, prova con suffissi
    path = Path(base_path)
    base_name = path.stem
    extension = path.suffix
    directory = path.parent

    counter = 1
    while True:
        new_path = directory / f"{base_name}-{counter}{extension}"
        if not os.path.exists(new_path):
            return str(new_path)
        counter += 1
        if counter > 100:  # Safety limit
            raise Exception("Troppi file con lo stesso nome")


def write_docx_output(book_title: str, chapter_summaries: List[Dict[str, str]],
                     global_summary: str, output_path: str) -> Tuple[bool, str]:
    """
    Genera un file DOCX con i riassunti.

    Args:
        book_title: Titolo del libro
        chapter_summaries: Lista di riassunti dei capitoli
        global_summary: Riassunto complessivo
        output_path: Percorso del file di output

    Returns:
        Tuple (success: bool, actual_path: str)
    """
    if not DOCX_SUPPORT:
        print("⚠️  Generazione DOCX non disponibile. Installa: pip install python-docx")
        return False, ""

    try:
        # Trova un percorso disponibile (gestisce file aperti)
        actual_path = get_available_filename(output_path)
        if actual_path != output_path:
            print(f"   ℹ️  File principale occupato, salvo come: {Path(actual_path).name}")

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
        doc.save(actual_path)
        return True, actual_path

    except Exception as e:
        print(f"❌ Errore nella generazione DOCX: {e}")
        return False, ""


def write_md_output(book_title: str, chapter_summaries: List[Dict[str, str]],
                   global_summary: str, output_path: str) -> Tuple[bool, str]:
    """
    Genera un file Markdown con i riassunti.

    Args:
        book_title: Titolo del libro
        chapter_summaries: Lista di riassunti dei capitoli
        global_summary: Riassunto complessivo
        output_path: Percorso del file di output

    Returns:
        Tuple (success: bool, actual_path: str)
    """
    try:
        # Trova un percorso disponibile (gestisce file aperti)
        actual_path = get_available_filename(output_path)
        if actual_path != output_path:
            print(f"   ℹ️  File principale occupato, salvo come: {Path(actual_path).name}")

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
        with open(actual_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return True, actual_path

    except Exception as e:
        print(f"❌ Errore nella generazione Markdown: {e}")
        return False, ""


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def process_book(filepath: str, output_dir: str, model: str = DEFAULT_MODEL,
                min_words: int = DEFAULT_MIN_WORDS) -> bool:
    """
    Elabora un singolo libro con supporto per ripresa (resume).

    Args:
        filepath: Percorso del file del libro
        output_dir: Directory di output
        model: Modello Ollama da usare
        min_words: Numero minimo di parole per capitolo

    Returns:
        True se successo, False altrimenti
    """
    filepath = Path(filepath)
    extension = filepath.suffix.lower()
    book_title = sanitize_filename(filepath.name)

    # Setup directory struttura
    book_output_dir = os.path.join(output_dir, book_title)
    chapters_dir = os.path.join(book_output_dir, "chapters")
    state_file = os.path.join(book_output_dir, "state.json")

    print(f"\n{'='*60}")
    print(f"📚 Elaborazione: {filepath.name}")
    print(f"{'='*60}\n")

    # Crea struttura directory
    ensure_resume_dirs(book_output_dir)

    # [1/4] Estrazione capitoli
    print(f"[1/4] Estrazione capitoli da {filepath.name}")

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

    total_chapters = len(chapters)
    print(f"✅ Trovati {total_chapters} capitoli\n")

    # Carica o crea stato
    state = load_state(state_file)
    if state is None:
        # Tenta ricostruzione da file esistenti
        state = rebuild_state_from_chapters(chapters_dir, book_title, total_chapters, model)
    else:
        print(f"   ℹ️  Ripresa elaborazione: {len(state['completed'])}/{total_chapters} capitoli completati")

    # Verifica coerenza
    if state['total_chapters'] != total_chapters:
        print(f"   ⚠️  Numero capitoli cambiato: era {state['total_chapters']}, ora {total_chapters}")
        state['total_chapters'] = total_chapters

    # [2/4] Riassunto capitoli
    print(f"\n[2/4] Riassunto capitoli")

    with tqdm(total=total_chapters, desc="Elaborazione capitoli", unit="cap") as pbar:
        for idx, chapter in enumerate(chapters, 1):
            # Verifica se può essere saltato
            skip, current_hash = should_skip_chapter(idx, chapter['text'], state, chapters_dir)

            if skip:
                print(f"\n   ⏭️  Capitolo {idx}/{total_chapters} — già riassunto (hash {current_hash})")
                pbar.update(1)
                continue

            # Elabora capitolo
            print(f"\n   📘 Capitolo {idx}/{total_chapters} — {chapter['title']}")

            summary = summarize_chapter(chapter['text'], chapter['title'], model)

            if summary:
                # Salva capitolo
                if save_chapter_summary(chapters_dir, idx, chapter['title'], current_hash, summary):
                    # Aggiorna stato
                    if idx not in state['completed']:
                        state['completed'].append(idx)
                        state['completed'].sort()
                    state['chapter_hashes'][str(idx)] = current_hash
                    save_state(state_file, state)

                    print(f"   ✅ Completato")
                else:
                    print(f"   ⚠️  Errore salvataggio")
            else:
                print(f"   ⚠️  Errore generazione riassunto")

            pbar.update(1)

    # Verifica completamento
    if len(state['completed']) != total_chapters:
        print(f"\n⚠️  Elaborazione incompleta: {len(state['completed'])}/{total_chapters} capitoli")
        print(f"   Capitoli mancanti: {sorted(set(range(1, total_chapters + 1)) - set(state['completed']))}")
        print(f"   Output parziali salvati in: {book_output_dir}")
        return False

    # [3/4] Sintesi globale
    print(f"\n[3/4] Generazione sintesi globale")

    # Carica tutti i riassunti dei capitoli
    chapter_summaries = load_chapter_summaries(chapters_dir, total_chapters)

    global_summary = generate_global_summary(chapter_summaries, model)

    if not global_summary:
        print("⚠️  Sintesi complessiva non generata, uso sintesi base")
        global_summary = "Sintesi complessiva non disponibile."
    else:
        print("✅ Sintesi complessiva generata")

    # [4/4] Scrittura output finale
    print(f"\n[4/4] Scrittura file finali")

    final_docx = os.path.join(book_output_dir, "final.docx")
    final_md = os.path.join(book_output_dir, "final.md")

    docx_ok, docx_path = write_docx_output(book_title, chapter_summaries, global_summary, final_docx)
    md_ok, md_path = write_md_output(book_title, chapter_summaries, global_summary, final_md)

    if docx_ok:
        print(f"✅ DOCX: {docx_path}")
    if md_ok:
        print(f"✅ MD: {md_path}")

    print(f"\n✨ Elaborazione completata!")
    print(f"   Directory output: {book_output_dir}")

    return docx_ok or md_ok


def main():
    """Funzione principale del programma."""
    parser = argparse.ArgumentParser(
        description="CLI Tool per Riassunti di Libri via Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python riassumi_libri.py
  python riassumi_libri.py --model qwen3:30b --min_words 500
  python riassumi_libri.py --input_dir /path/to/books --output_dir /path/to/output
        """
    )

    parser.add_argument('--model', type=str, default=DEFAULT_MODEL,
                       help=f'Modello Ollama da usare (default: {DEFAULT_MODEL})')
    parser.add_argument('--input_dir', type=str, default=DEFAULT_INPUT_DIR,
                       help=f'Directory input (default: {DEFAULT_INPUT_DIR})')
    parser.add_argument('--output_dir', type=str, default=DEFAULT_OUTPUT_DIR,
                       help=f'Directory output (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--min_words', type=int, default=DEFAULT_MIN_WORDS,
                       help=f'Parole minime per capitolo (default: {DEFAULT_MIN_WORDS})')
    parser.add_argument('--language', type=str, default=DEFAULT_LANGUAGE,
                       help=f'Lingua output (default: {DEFAULT_LANGUAGE})')

    args = parser.parse_args()

    print("\n" + "="*60)
    print("📚 RIASSUMI LIBRI - CLI Tool via Ollama")
    print("="*60)
    print(f"Modello: {args.model}")
    print(f"Input: {args.input_dir}")
    print(f"Output: {args.output_dir}")
    print(f"Min parole/capitolo: {args.min_words}")
    print("="*60 + "\n")

    # Verifica che Ollama sia raggiungibile
    print("🔍 Verifica connessione a Ollama...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        print("✅ Ollama raggiungibile\n")
    except Exception as e:
        print(f"❌ Errore connessione Ollama: {e}")
        print("   Assicurati che Ollama sia in esecuzione su http://localhost:11434")
        sys.exit(1)

    # Verifica directory input
    if not os.path.exists(args.input_dir):
        print(f"❌ Directory input non trovata: {args.input_dir}")
        sys.exit(1)

    # Crea directory output
    ensure_directory(args.output_dir)

    # Scansiona file
    print(f"[1/4] Scansione {args.input_dir}")
    files = []

    for ext in ['.epub', '.pdf']:
        files.extend(Path(args.input_dir).glob(f'*{ext}'))

    if not files:
        print("❌ Nessun file EPUB o PDF trovato")
        sys.exit(1)

    print(f"Trovati {len(files)} file: {', '.join([f.name for f in files])}\n")

    # Elabora ogni file
    success_count = 0

    for idx, filepath in enumerate(files, 1):
        print(f"\n{'#'*60}")
        print(f"FILE {idx}/{len(files)}")
        print(f"{'#'*60}")

        try:
            if process_book(str(filepath), args.output_dir, args.model, args.min_words):
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
