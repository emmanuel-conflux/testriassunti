# Struttura Modulare - riassumi_libri_lib

## 📁 Architettura

Questo package contiene la logica separata in moduli per migliore manutenibilità e riutilizzo.

### Moduli Implementati

#### ✅ `config.py`
- Costanti di configurazione
- URL e parametri default
- Template dei prompt per Ollama

#### ✅ `utils.py`
- Funzioni utility generiche
- `ensure_directory()` - Creazione directory
- `sanitize_filename()` - Pulizia nomi file
- `count_words()` - Conteggio parole
- `chunk_text()` - Suddivisione testi lunghi

#### ✅ `validation.py`
- Validazione file EPUB e PDF
- `validate_epub()` - Controllo integrità EPUB
- `validate_pdf()` - Controllo integrità PDF
- `validate_file()` - Dispatcher validazione

### Moduli Futuri (TODO)

Per completare la modularizzazione, i seguenti moduli dovrebbero essere estratti dal file principale:

#### 📄 `logging_setup.py`
```python
"""Setup sistema logging"""
- setup_logging(log_file, verbose)
```

#### 📄 `cache.py`
```python
"""Sistema cache e checkpoint"""
- get_checkpoint_path()
- save_checkpoint()
- load_checkpoint()
- delete_checkpoint()
```

#### 📄 `config_loader.py`
```python
"""Caricamento configurazione da file"""
- load_config(config_path)
```

#### 📄 `extractors/`
Subdirectory con estrattori specifici:

**`extractors/__init__.py`**
```python
from .epub import extract_chapters_from_epub
from .pdf import extract_chapters_from_pdf
```

**`extractors/epub.py`**
```python
"""Estrazione capitoli da EPUB"""
- extract_chapters_from_epub()
```

**`extractors/pdf.py`**
```python
"""Estrazione capitoli da PDF"""
- extract_chapters_from_pdf()
```

#### 📄 `ollama_client.py`
```python
"""Client per interazione con Ollama"""
- call_ollama(prompt, model, temperature, max_retries)
```

#### 📄 `summarizer.py`
```python
"""Logica di riassunto"""
- summarize_chapter()
- generate_global_summary()
```

#### 📄 `output_writers/`
Subdirectory con writer specifici:

**`output_writers/__init__.py`**
```python
from .docx_writer import write_docx_output
from .md_writer import write_md_output
```

**`output_writers/docx_writer.py`**
```python
"""Generazione file DOCX"""
- write_docx_output()
```

**`output_writers/md_writer.py`**
```python
"""Generazione file Markdown"""
- write_md_output()
```

#### 📄 `dry_run.py`
```python
"""Analisi dry-run"""
- analyze_book_dry_run()
```

#### 📄 `processor.py`
```python
"""Elaborazione libri"""
- process_book()
- process_book_wrapper()
```

## 🏗️ Struttura Completa Ideale

```
riassumi_libri/
├── riassumi_libri.py           # Entry point CLI
├── riassumi_libri_lib/
│   ├── __init__.py
│   ├── config.py              ✅ Implementato
│   ├── utils.py               ✅ Implementato
│   ├── validation.py          ✅ Implementato
│   ├── logging_setup.py       📄 TODO
│   ├── cache.py               📄 TODO
│   ├── config_loader.py       📄 TODO
│   ├── ollama_client.py       📄 TODO
│   ├── summarizer.py          📄 TODO
│   ├── dry_run.py             📄 TODO
│   ├── processor.py           📄 TODO
│   ├── extractors/
│   │   ├── __init__.py        📄 TODO
│   │   ├── epub.py            📄 TODO
│   │   └── pdf.py             📄 TODO
│   └── output_writers/
│       ├── __init__.py        📄 TODO
│       ├── docx_writer.py     📄 TODO
│       └── md_writer.py       📄 TODO
├── tests/                     📄 TODO
│   ├── __init__.py
│   ├── test_validation.py
│   ├── test_extractors.py
│   └── test_utils.py
└── README_MODULES.md          ✅ Questo file
```

## 🔄 Come Completare la Modularizzazione

1. **Creare i moduli mancanti**: Spostare le funzioni dal file principale ai moduli corrispondenti
2. **Aggiornare gli import**: Modificare riassumi_libri.py per importare dai moduli
3. **Aggiungere test**: Creare test unitari per ogni modulo
4. **Documentare**: Aggiungere docstring e type hints completi
5. **Ottimizzare**: Rifattorizzare dove necessario

## 📚 Benefici della Modularizzazione

- ✅ **Manutenibilità**: Codice più organizzato e facile da modificare
- ✅ **Testabilità**: Test unitari per ogni componente
- ✅ **Riutilizzo**: Moduli utilizzabili in altri progetti
- ✅ **Leggibilità**: File più piccoli e focalizzati
- ✅ **Collaborazione**: Più facile lavorare in team
- ✅ **Debugging**: Isolamento problemi più semplice

## 🎯 Stato Attuale

**Moduli creati**: 3/12 (25%)
**Funzionalità**: Dimostrazione concept + utility fondamentali

La modularizzazione parziale dimostra il concetto e fornisce una base per future espansioni.
Il file principale (`riassumi_libri.py`) mantiene la retrocompatibilità completa.
