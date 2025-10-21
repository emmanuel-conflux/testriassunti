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
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Dependencies
import requests
from tqdm import tqdm

# Configurazione logging (iniziale, verrà riconfigurato nel main)
logger = logging.getLogger(__name__)

# YAML support (optional)
try:
    import yaml
    YAML_SUPPORT = True
except ImportError:
    YAML_SUPPORT = False
    logger.debug("PyYAML non disponibile. Supporto config YAML disabilitato.")

# EPUB handling
try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    EPUB_SUPPORT = True
except ImportError:
    EPUB_SUPPORT = False
    logger.warning("ebooklib o BeautifulSoup non disponibili. Supporto EPUB disabilitato.")

# PDF handling
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logger.warning("PyPDF2 non disponibile. Supporto PDF disabilitato.")

# DOCX generation
try:
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False
    logger.warning("python-docx non disponibile. Generazione DOCX disabilitata.")


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
# LOGGING SETUP
# ============================================================================

def setup_logging(log_file: Optional[str] = None, verbose: bool = False) -> None:
    """
    Configura il sistema di logging.

    Args:
        log_file: Percorso del file di log (opzionale)
        verbose: Se True, mostra messaggi DEBUG
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Formato dei log
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    handlers = []

    # Handler console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    handlers.append(console_handler)

    # Handler file (se specificato)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # File sempre dettagliato
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        handlers.append(file_handler)

    # Configura logger root
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
        force=True
    )


# ============================================================================
# CONFIGURATION
# ============================================================================

def load_config(config_path: str) -> Dict[str, any]:
    """
    Carica configurazione da file YAML o JSON.

    Args:
        config_path: Percorso del file di configurazione

    Returns:
        Dizionario con la configurazione
    """
    config_file = Path(config_path)

    if not config_file.exists():
        logger.error(f"File di configurazione non trovato: {config_path}")
        return {}

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            # Prova YAML prima (supporta anche JSON)
            if YAML_SUPPORT and config_file.suffix in ['.yaml', '.yml']:
                config = yaml.safe_load(f)
                logger.info(f"Configurazione caricata da {config_path}")
                return config or {}
            # Altrimenti JSON
            elif config_file.suffix == '.json':
                config = json.load(f)
                logger.info(f"Configurazione caricata da {config_path}")
                return config or {}
            else:
                logger.warning(f"Formato file non riconosciuto: {config_file.suffix}. Usa .yaml, .yml o .json")
                return {}

    except Exception as e:
        logger.error(f"Errore nel caricamento configurazione: {e}")
        return {}


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
                logger.warning(f"Tentativo {attempt + 1} fallito: {e}")
                logger.info(f"Riprovo tra {wait_time} secondi...")
                time.sleep(wait_time)
            else:
                logger.error(f"Errore Ollama dopo {max_retries} tentativi: {e}")
                return None
        except Exception as e:
            logger.error(f"Errore imprevisto: {e}")
            return None

    return None


# ============================================================================
# FILE VALIDATION
# ============================================================================

def validate_epub(filepath: str) -> bool:
    """
    Valida che un file EPUB sia leggibile e non corrotto.

    Args:
        filepath: Percorso del file EPUB

    Returns:
        True se il file è valido, False altrimenti
    """
    if not EPUB_SUPPORT:
        logger.error("Supporto EPUB non disponibile")
        return False

    try:
        # Tenta di aprire e leggere il file
        book = epub.read_epub(filepath)

        # Verifica che ci siano item nello spine
        if not book.spine or len(book.spine) == 0:
            logger.error(f"EPUB vuoto o malformato: {filepath}")
            return False

        logger.debug(f"EPUB valido: {filepath}")
        return True

    except Exception as e:
        logger.error(f"EPUB non valido ({filepath}): {e}")
        return False


def validate_pdf(filepath: str) -> bool:
    """
    Valida che un file PDF sia leggibile e non corrotto.

    Args:
        filepath: Percorso del file PDF

    Returns:
        True se il file è valido, False altrimenti
    """
    if not PDF_SUPPORT:
        logger.error("Supporto PDF non disponibile")
        return False

    try:
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)

            # Verifica che ci siano pagine
            if len(reader.pages) == 0:
                logger.error(f"PDF vuoto: {filepath}")
                return False

            # Tenta di estrarre testo dalla prima pagina
            try:
                first_page_text = reader.pages[0].extract_text()
            except Exception as e:
                logger.warning(f"Impossibile estrarre testo dal PDF: {e}")
                # Non è necessariamente un errore fatale
                return True

        logger.debug(f"PDF valido: {filepath}")
        return True

    except Exception as e:
        logger.error(f"PDF non valido ({filepath}): {e}")
        return False


def validate_file(filepath: str) -> bool:
    """
    Valida un file in base all'estensione.

    Args:
        filepath: Percorso del file

    Returns:
        True se il file è valido, False altrimenti
    """
    path = Path(filepath)

    # Verifica esistenza
    if not path.exists():
        logger.error(f"File non trovato: {filepath}")
        return False

    # Verifica dimensione (almeno 1KB)
    if path.stat().st_size < 1024:
        logger.error(f"File troppo piccolo (< 1KB): {filepath}")
        return False

    # Valida in base al formato
    extension = path.suffix.lower()

    if extension == '.epub':
        return validate_epub(str(filepath))
    elif extension == '.pdf':
        return validate_pdf(str(filepath))
    else:
        logger.error(f"Formato non supportato: {extension}")
        return False


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
        logger.error("Supporto EPUB non disponibile. Installa: pip install ebooklib beautifulsoup4")
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
                logger.warning(f"Errore nell'elaborazione item {idx}: {e}")
                continue

        return chapters

    except Exception as e:
        logger.error(f"Errore nella lettura EPUB: {e}")
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
        logger.error("Supporto PDF non disponibile. Installa: pip install PyPDF2")
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
                    logger.warning(f"Errore nell'estrazione pagina: {e}")
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
            logger.warning("Nessun pattern di capitolo trovato. Suddivisione in blocchi...")
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
        logger.error(f"Errore nella lettura PDF: {e}")
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
    logger.info(f"Capitolo lungo ({len(chapter_text)} char), applico MAP-REDUCE...")

    # MAP: riassumi ogni chunk
    chunks = chunk_text(chapter_text)
    partial_summaries = []

    for idx, chunk in enumerate(chunks, 1):
        logger.debug(f"Elaboro chunk {idx}/{len(chunks)}...")
        prompt = PROMPT_MAP.format(text=chunk)
        summary = call_ollama(prompt, model)

        if summary:
            partial_summaries.append(summary)
        else:
            logger.warning(f"Chunk {idx} saltato per errore")

    if not partial_summaries:
        logger.error("Nessun riassunto parziale generato")
        return None

    # REDUCE: unisci i riassunti parziali
    logger.info(f"Unisco {len(partial_summaries)} riassunti parziali...")
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
        logger.warning("Generazione DOCX non disponibile. Installa: pip install python-docx")
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
        logger.error(f"Errore nella generazione DOCX: {e}")
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
        logger.error(f"Errore nella generazione Markdown: {e}")
        return False


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def process_book(filepath: str, output_dir: str, model: str = DEFAULT_MODEL,
                min_words: int = DEFAULT_MIN_WORDS) -> bool:
    """
    Elabora un singolo libro.

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

    print(f"\n{'='*60}")
    print(f"📚 Elaborazione: {filepath.name}")
    print(f"{'='*60}\n")

    # [0/4] Validazione file
    logger.info(f"Validazione file: {filepath.name}")
    if not validate_file(str(filepath)):
        logger.error(f"File non valido, saltato: {filepath.name}")
        return False

    # [1/4] Estrazione capitoli
    print(f"[1/4] Estrazione capitoli da {filepath.name}")

    if extension == '.epub':
        chapters = extract_chapters_from_epub(str(filepath), min_words)
    elif extension == '.pdf':
        chapters = extract_chapters_from_pdf(str(filepath), min_words)
    else:
        logger.error(f"Formato non supportato: {extension}")
        return False

    if not chapters:
        logger.error("Nessun capitolo estratto")
        return False

    logger.info(f"Trovati {len(chapters)} capitoli")

    # [2/4] Riassunto capitoli
    print(f"[2/4] Riassunto capitoli")
    chapter_summaries = []

    with tqdm(total=len(chapters), desc="Elaborazione capitoli", unit="cap") as pbar:
        for idx, chapter in enumerate(chapters, 1):
            print(f"\n   📖 Capitolo {idx}/{len(chapters)}: {chapter['title']}")

            summary = summarize_chapter(chapter['text'], chapter['title'], model)

            if summary:
                chapter_summaries.append({
                    'title': chapter['title'],
                    'summary': summary
                })
                logger.info(f"Capitolo {idx} completato")
            else:
                logger.warning(f"Capitolo {idx} saltato per errore")

            pbar.update(1)

    if not chapter_summaries:
        logger.error("Nessun riassunto generato")
        return False

    # [3/4] Riassunto globale
    print(f"\n[3/4] Generazione riassunto complessivo")
    global_summary = generate_global_summary(chapter_summaries, model)

    if not global_summary:
        logger.warning("Riassunto complessivo non generato, uso sintesi base")
        global_summary = "Riassunto complessivo non disponibile."
    else:
        logger.info("Riassunto complessivo generato")

    # [4/4] Scrittura output
    print(f"\n[4/4] Scrittura file di output")

    docx_path = os.path.join(output_dir, f"{book_title}.riassunto.docx")
    md_path = os.path.join(output_dir, f"{book_title}.riassunto.md")

    docx_ok = write_docx_output(book_title, chapter_summaries, global_summary, docx_path)
    md_ok = write_md_output(book_title, chapter_summaries, global_summary, md_path)

    if docx_ok:
        logger.info(f"DOCX salvato: {docx_path}")
    if md_ok:
        logger.info(f"MD salvato: {md_path}")

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

    parser.add_argument('--config', type=str, default=None,
                       help='File di configurazione YAML/JSON (opzionale)')
    parser.add_argument('--model', type=str, default=None,
                       help=f'Modello Ollama da usare (default: {DEFAULT_MODEL})')
    parser.add_argument('--input_dir', type=str, default=None,
                       help=f'Directory input (default: {DEFAULT_INPUT_DIR})')
    parser.add_argument('--output_dir', type=str, default=None,
                       help=f'Directory output (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--min_words', type=int, default=None,
                       help=f'Parole minime per capitolo (default: {DEFAULT_MIN_WORDS})')
    parser.add_argument('--language', type=str, default=None,
                       help=f'Lingua output (default: {DEFAULT_LANGUAGE})')
    parser.add_argument('--log-file', type=str, default=None,
                       help='File di log (opzionale, es: riassunti.log)')
    parser.add_argument('--verbose', action='store_true',
                       help='Mostra log dettagliati (DEBUG level)')

    args = parser.parse_args()

    # Carica configurazione da file (se specificato)
    config = {}
    if args.config:
        config = load_config(args.config)

    # Merge config: CLI args > config file > defaults
    # Funzione helper per ottenere il valore con priorità
    def get_value(arg_value, config_key, default_value):
        if arg_value is not None:
            return arg_value
        return config.get(config_key, default_value)

    # Applica priorità
    model = get_value(args.model, 'model', DEFAULT_MODEL)
    input_dir = get_value(args.input_dir, 'input_dir', DEFAULT_INPUT_DIR)
    output_dir = get_value(args.output_dir, 'output_dir', DEFAULT_OUTPUT_DIR)
    min_words = get_value(args.min_words, 'min_words', DEFAULT_MIN_WORDS)
    language = get_value(args.language, 'language', DEFAULT_LANGUAGE)
    log_file = get_value(args.log_file, 'log_file', None)
    verbose = args.verbose or config.get('verbose', False)

    # Configura logging
    setup_logging(log_file=log_file, verbose=verbose)

    print("\n" + "="*60)
    print("📚 RIASSUMI LIBRI - CLI Tool via Ollama")
    print("="*60)
    print(f"Modello: {model}")
    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Min parole/capitolo: {min_words}")
    if args.config:
        print(f"Config: {args.config}")
    print("="*60 + "\n")

    # Verifica che Ollama sia raggiungibile
    logger.info("Verifica connessione a Ollama...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        logger.info("Ollama raggiungibile")
    except Exception as e:
        logger.error(f"Errore connessione Ollama: {e}")
        logger.error("Assicurati che Ollama sia in esecuzione su http://localhost:11434")
        sys.exit(1)

    # Verifica directory input
    if not os.path.exists(input_dir):
        logger.error(f"Directory input non trovata: {input_dir}")
        sys.exit(1)

    # Crea directory output
    ensure_directory(output_dir)

    # Scansiona file
    logger.info(f"Scansione directory: {input_dir}")
    files = []

    for ext in ['.epub', '.pdf']:
        files.extend(Path(input_dir).glob(f'*{ext}'))

    if not files:
        logger.error("Nessun file EPUB o PDF trovato")
        sys.exit(1)

    logger.info(f"Trovati {len(files)} file: {', '.join([f.name for f in files])}")

    # Elabora ogni file
    success_count = 0

    for idx, filepath in enumerate(files, 1):
        print(f"\n{'#'*60}")
        print(f"FILE {idx}/{len(files)}")
        print(f"{'#'*60}")

        try:
            if process_book(str(filepath), output_dir, model, min_words):
                success_count += 1
        except Exception as e:
            logger.error(f"Errore nell'elaborazione: {e}", exc_info=verbose)
            continue

    # Riepilogo finale
    print(f"\n{'='*60}")
    print(f"✅ OPERAZIONE COMPLETATA")
    print(f"{'='*60}")
    logger.info(f"File elaborati: {success_count}/{len(files)}")
    logger.info(f"Output salvati in: {output_dir}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
