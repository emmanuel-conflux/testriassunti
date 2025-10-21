"""
config.py - Configurazione e costanti
"""

# ============================================================================
# CONFIGURAZIONE DEFAULT
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

# Cache and checkpoint configuration
CACHE_DIR = ".cache"
CHECKPOINT_SUFFIX = ".checkpoint.json"

# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

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
