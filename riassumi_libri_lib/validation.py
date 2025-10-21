"""
validation.py - Validazione file EPUB e PDF
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Import condizionali
try:
    import ebooklib
    from ebooklib import epub
    EPUB_SUPPORT = True
except ImportError:
    EPUB_SUPPORT = False

try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


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
