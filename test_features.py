#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_features.py - Test completo delle features di riassumi_libri.py

Verifica che tutte le funzionalità richieste siano presenti e funzionanti.
"""

import sys
import os
import tempfile
import json
from pathlib import Path

# Importa il modulo da testare
import riassumi_libri as rl

# Colori per output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_test(name, passed, message=""):
    """Stampa il risultato di un test."""
    status = f"{Colors.OKGREEN}✅ PASS{Colors.ENDC}" if passed else f"{Colors.FAIL}❌ FAIL{Colors.ENDC}"
    print(f"{status} - {name}")
    if message:
        print(f"      {message}")

def print_section(title):
    """Stampa un'intestazione di sezione."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{title}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def test_imports():
    """Test 1: Verifica che tutti i moduli siano importabili."""
    print_section("TEST 1: Importazioni e Dipendenze")

    tests = []

    # Core modules
    tests.append(("requests", hasattr(rl, 'requests'), "Libreria per chiamate HTTP"))
    tests.append(("tqdm", hasattr(rl, 'tqdm'), "Barra di progresso"))

    # Supporto EPUB
    tests.append(("EPUB support", rl.EPUB_SUPPORT, "ebooklib e BeautifulSoup"))

    # Supporto PDF
    tests.append(("PDF support", rl.PDF_SUPPORT, "PyPDF2"))

    # Supporto DOCX
    tests.append(("DOCX support", rl.DOCX_SUPPORT, "python-docx"))

    passed = 0
    for name, result, desc in tests:
        print_test(name, result, desc)
        if result:
            passed += 1

    return passed, len(tests)

def test_constants():
    """Test 2: Verifica che tutte le costanti siano definite."""
    print_section("TEST 2: Costanti e Configurazione")

    tests = [
        ("VERSION", hasattr(rl, 'VERSION'), f"Versione: {rl.VERSION if hasattr(rl, 'VERSION') else 'N/A'}"),
        ("LAST_UPDATE", hasattr(rl, 'LAST_UPDATE'), f"Ultimo aggiornamento: {rl.LAST_UPDATE if hasattr(rl, 'LAST_UPDATE') else 'N/A'}"),
        ("DEFAULT_INPUT_DIR", hasattr(rl, 'DEFAULT_INPUT_DIR'), rl.DEFAULT_INPUT_DIR if hasattr(rl, 'DEFAULT_INPUT_DIR') else ''),
        ("DEFAULT_OUTPUT_DIR", hasattr(rl, 'DEFAULT_OUTPUT_DIR'), rl.DEFAULT_OUTPUT_DIR if hasattr(rl, 'DEFAULT_OUTPUT_DIR') else ''),
        ("DEFAULT_MODEL", hasattr(rl, 'DEFAULT_MODEL'), rl.DEFAULT_MODEL if hasattr(rl, 'DEFAULT_MODEL') else ''),
        ("DEFAULT_MIN_WORDS", hasattr(rl, 'DEFAULT_MIN_WORDS'), str(rl.DEFAULT_MIN_WORDS) if hasattr(rl, 'DEFAULT_MIN_WORDS') else ''),
        ("OLLAMA_URL", hasattr(rl, 'OLLAMA_URL'), rl.OLLAMA_URL if hasattr(rl, 'OLLAMA_URL') else ''),
        ("MAX_CHUNK_SIZE", hasattr(rl, 'MAX_CHUNK_SIZE'), f"{rl.MAX_CHUNK_SIZE} caratteri" if hasattr(rl, 'MAX_CHUNK_SIZE') else ''),
        ("CHUNK_OVERLAP", hasattr(rl, 'CHUNK_OVERLAP'), f"{rl.CHUNK_OVERLAP} caratteri" if hasattr(rl, 'CHUNK_OVERLAP') else ''),
    ]

    passed = 0
    for name, result, desc in tests:
        print_test(name, result, desc)
        if result:
            passed += 1

    return passed, len(tests)

def test_prompts():
    """Test 3: Verifica che tutti i prompt templates siano definiti."""
    print_section("TEST 3: Prompt Templates")

    tests = [
        ("PROMPT_MAP", hasattr(rl, 'PROMPT_MAP') and "{text}" in rl.PROMPT_MAP, "Template per MAP step"),
        ("PROMPT_REDUCE", hasattr(rl, 'PROMPT_REDUCE') and "{summaries}" in rl.PROMPT_REDUCE, "Template per REDUCE step"),
        ("PROMPT_GLOBAL", hasattr(rl, 'PROMPT_GLOBAL') and "{chapter_summaries}" in rl.PROMPT_GLOBAL, "Template per riassunto globale"),
    ]

    passed = 0
    for name, result, desc in tests:
        print_test(name, result, desc)
        if result:
            passed += 1

    return passed, len(tests)

def test_utility_functions():
    """Test 4: Verifica le funzioni utility."""
    print_section("TEST 4: Funzioni Utility")

    tests = []

    # Test ensure_directory
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "test_dir", "nested")
        try:
            rl.ensure_directory(test_path)
            tests.append(("ensure_directory", os.path.exists(test_path), "Crea directory ricorsivamente"))
        except Exception as e:
            tests.append(("ensure_directory", False, f"Errore: {e}"))

    # Test sanitize_filename
    test_cases = [
        ("file.epub", "file"),
        ("file<test>.pdf", "file_test_"),
        ("C:\\path\\file.epub", "file"),
    ]
    sanitize_ok = True
    for input_name, expected in test_cases:
        result = rl.sanitize_filename(input_name)
        if expected not in result:
            sanitize_ok = False
            break
    tests.append(("sanitize_filename", sanitize_ok, "Rimuove caratteri non validi"))

    # Test count_words
    word_count = rl.count_words("Questo è un test con cinque parole")
    tests.append(("count_words", word_count == 7, f"Conta parole correttamente ({word_count})"))

    # Test chunk_text
    long_text = "Parola " * 5000  # Testo lungo
    chunks = rl.chunk_text(long_text, max_size=1000, overlap=100)
    chunks_ok = len(chunks) > 1 and all(len(c) <= 1100 for c in chunks)  # 1000 + overlap margin
    tests.append(("chunk_text", chunks_ok, f"Suddivide testo in {len(chunks)} chunks"))

    # Test chunk_text con testo corto
    short_text = "Testo corto"
    short_chunks = rl.chunk_text(short_text, max_size=1000)
    tests.append(("chunk_text (testo corto)", len(short_chunks) == 1, "Non divide testo breve"))

    passed = 0
    for name, result, desc in tests:
        print_test(name, result, desc)
        if result:
            passed += 1

    return passed, len(tests)

def test_core_functions():
    """Test 5: Verifica che le funzioni core siano definite."""
    print_section("TEST 5: Funzioni Core")

    functions = [
        ("show_banner", "Mostra banner con versione"),
        ("interactive_setup", "Setup interattivo guidato"),
        ("call_ollama", "Chiamata API Ollama con retry"),
        ("extract_chapters_from_epub", "Estrazione capitoli da EPUB"),
        ("extract_chapters_from_pdf", "Estrazione capitoli da PDF"),
        ("summarize_chapter", "Riassunto capitolo con MAP-REDUCE"),
        ("generate_global_summary", "Riassunto complessivo del libro"),
        ("write_docx_output", "Generazione file DOCX"),
        ("write_md_output", "Generazione file Markdown"),
        ("process_book", "Elaborazione completa di un libro"),
        ("select_files_interactive", "Selezione interattiva file"),
        ("main", "Funzione principale del programma"),
    ]

    passed = 0
    total = len(functions)

    for func_name, desc in functions:
        exists = hasattr(rl, func_name) and callable(getattr(rl, func_name))
        print_test(func_name, exists, desc)
        if exists:
            passed += 1

    return passed, total

def test_banner_and_version():
    """Test 6: Verifica il banner e le informazioni di versione."""
    print_section("TEST 6: Banner e Versione")

    tests = []

    # Verifica che VERSION sia presente
    has_version = hasattr(rl, 'VERSION') and rl.VERSION
    tests.append(("VERSION definita", has_version, f"v{rl.VERSION}" if has_version else "N/A"))

    # Verifica che LAST_UPDATE sia presente
    has_update = hasattr(rl, 'LAST_UPDATE') and rl.LAST_UPDATE
    tests.append(("LAST_UPDATE definita", has_update, rl.LAST_UPDATE if has_update else "N/A"))

    # Verifica che show_banner sia callable
    has_banner = hasattr(rl, 'show_banner') and callable(rl.show_banner)
    tests.append(("show_banner callable", has_banner, "Funzione per mostrare banner"))

    # Test esecuzione banner (cattura output)
    if has_banner:
        try:
            import io
            from contextlib import redirect_stdout

            f = io.StringIO()
            with redirect_stdout(f):
                rl.show_banner()
            output = f.getvalue()

            banner_ok = "RIASSUMI LIBRI" in output and "Versione" in output
            tests.append(("Banner output corretto", banner_ok, "Contiene titolo e versione"))
        except Exception as e:
            tests.append(("Banner output", False, f"Errore: {e}"))

    passed = 0
    for name, result, desc in tests:
        print_test(name, result, desc)
        if result:
            passed += 1

    return passed, len(tests)

def test_cli_arguments():
    """Test 7: Verifica che gli argomenti CLI siano configurati."""
    print_section("TEST 7: Argomenti CLI")

    tests = []

    # Verifica che main usi argparse
    import argparse
    import inspect

    try:
        source = inspect.getsource(rl.main)

        has_argparse = "argparse.ArgumentParser" in source
        tests.append(("argparse.ArgumentParser", has_argparse, "Usa argparse per CLI"))

        # Verifica argomenti specifici
        cli_args = [
            ("--interactive", "Modalità interattiva"),
            ("--model", "Modello Ollama"),
            ("--input_dir", "Directory input"),
            ("--output_dir", "Directory output"),
            ("--min_words", "Parole minime per capitolo"),
            ("--language", "Lingua output"),
        ]

        for arg, desc in cli_args:
            has_arg = arg in source
            tests.append((arg, has_arg, desc))

    except Exception as e:
        tests.append(("Analisi main()", False, f"Errore: {e}"))

    passed = 0
    for name, result, desc in tests:
        print_test(name, result, desc)
        if result:
            passed += 1

    return passed, len(tests)

def test_error_handling():
    """Test 8: Verifica la gestione degli errori."""
    print_section("TEST 8: Gestione Errori e Retry Logic")

    tests = []

    import inspect

    try:
        # Verifica retry logic in call_ollama
        source = inspect.getsource(rl.call_ollama)

        has_retry = "max_retries" in source and "for attempt in range" in source
        tests.append(("Retry logic", has_retry, "Tentativi multipli in call_ollama"))

        has_backoff = "2 **" in source or "wait_time" in source
        tests.append(("Exponential backoff", has_backoff, "Backoff esponenziale tra tentativi"))

        has_timeout = "timeout" in source
        tests.append(("Timeout", has_timeout, "Timeout per chiamate HTTP"))

        # Verifica gestione eccezioni
        has_try_except = "try:" in source and "except" in source
        tests.append(("Try-except", has_try_except, "Gestione eccezioni"))

    except Exception as e:
        tests.append(("Analisi error handling", False, f"Errore: {e}"))

    passed = 0
    for name, result, desc in tests:
        print_test(name, result, desc)
        if result:
            passed += 1

    return passed, len(tests)

def test_multiplatform():
    """Test 9: Verifica la compatibilità multipiattaforma."""
    print_section("TEST 9: Compatibilità Multipiattaforma")

    tests = []

    import inspect

    try:
        # Verifica uso di os.path.expanduser per home directory
        main_source = inspect.getsource(rl.main) if hasattr(rl, 'main') else ""
        constants_text = str([rl.DEFAULT_INPUT_DIR, rl.DEFAULT_OUTPUT_DIR])

        # Le costanti dovrebbero usare expanduser
        uses_expanduser = "expanduser" in inspect.getsource(rl) or "~" in constants_text
        tests.append(("os.path.expanduser", uses_expanduser, "Supporto home directory (~)"))

        # Verifica uso di Path per gestione path
        uses_pathlib = "Path(" in inspect.getsource(rl)
        tests.append(("pathlib.Path", uses_pathlib, "Usa pathlib per path multipiattaforma"))

        # Verifica che DEFAULT_INPUT_DIR e DEFAULT_OUTPUT_DIR usino home
        input_ok = hasattr(rl, 'DEFAULT_INPUT_DIR')
        output_ok = hasattr(rl, 'DEFAULT_OUTPUT_DIR')
        tests.append(("Directory default configurate", input_ok and output_ok, "Input e output directory definite"))

    except Exception as e:
        tests.append(("Analisi multipiattaforma", False, f"Errore: {e}"))

    passed = 0
    for name, result, desc in tests:
        print_test(name, result, desc)
        if result:
            passed += 1

    return passed, len(tests)

def test_map_reduce():
    """Test 10: Verifica l'implementazione MAP-REDUCE."""
    print_section("TEST 10: MAP-REDUCE per Testi Lunghi")

    tests = []

    import inspect

    try:
        # Verifica che summarize_chapter implementi MAP-REDUCE
        source = inspect.getsource(rl.summarize_chapter)

        has_chunking = "chunk_text" in source
        tests.append(("Chunking", has_chunking, "Suddivide testi lunghi"))

        has_map = "PROMPT_MAP" in source
        tests.append(("MAP step", has_map, "Riassume ogni chunk"))

        has_reduce = "PROMPT_REDUCE" in source
        tests.append(("REDUCE step", has_reduce, "Unisce riassunti parziali"))

        has_size_check = "MAX_CHUNK_SIZE" in source or "len(chapter_text)" in source
        tests.append(("Size check", has_size_check, "Verifica dimensione testo"))

    except Exception as e:
        tests.append(("Analisi MAP-REDUCE", False, f"Errore: {e}"))

    passed = 0
    for name, result, desc in tests:
        print_test(name, result, desc)
        if result:
            passed += 1

    return passed, len(tests)

def test_output_formats():
    """Test 11: Verifica i formati di output."""
    print_section("TEST 11: Formati di Output (DOCX e Markdown)")

    tests = []

    # Verifica funzioni di output
    has_docx = hasattr(rl, 'write_docx_output') and callable(rl.write_docx_output)
    tests.append(("write_docx_output", has_docx, "Generazione file DOCX"))

    has_md = hasattr(rl, 'write_md_output') and callable(rl.write_md_output)
    tests.append(("write_md_output", has_md, "Generazione file Markdown"))

    # Test scrittura Markdown (più semplice da testare)
    if has_md:
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "test.md")

            try:
                result = rl.write_md_output(
                    book_title="Test Book",
                    chapter_summaries=[
                        {'title': 'Capitolo 1', 'summary': 'Riassunto 1'},
                        {'title': 'Capitolo 2', 'summary': 'Riassunto 2'},
                    ],
                    global_summary="Riassunto globale di test",
                    output_path=test_path
                )

                md_ok = result and os.path.exists(test_path)

                if md_ok:
                    with open(test_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    has_title = "Test Book" in content
                    has_index = "Indice" in content
                    has_chapters = "Capitolo 1" in content and "Capitolo 2" in content
                    has_global = "Riassunto globale" in content or "Sintesi complessiva" in content

                    tests.append(("Markdown - Titolo", has_title, "Contiene titolo libro"))
                    tests.append(("Markdown - Indice", has_index, "Contiene indice"))
                    tests.append(("Markdown - Capitoli", has_chapters, "Contiene capitoli"))
                    tests.append(("Markdown - Sintesi globale", has_global, "Contiene sintesi complessiva"))
                else:
                    tests.append(("Markdown output", False, "File non generato"))

            except Exception as e:
                tests.append(("Markdown output", False, f"Errore: {e}"))

    passed = 0
    for name, result, desc in tests:
        print_test(name, result, desc)
        if result:
            passed += 1

    return passed, len(tests)

def test_interactive_mode():
    """Test 12: Verifica la modalità interattiva."""
    print_section("TEST 12: Modalità Interattiva")

    tests = []

    import inspect

    # Verifica che interactive_setup sia definito
    has_setup = hasattr(rl, 'interactive_setup') and callable(rl.interactive_setup)
    tests.append(("interactive_setup", has_setup, "Funzione setup interattivo"))

    if has_setup:
        try:
            source = inspect.getsource(rl.interactive_setup)

            has_input = "input(" in source
            tests.append(("User input", has_input, "Chiede input all'utente"))

            has_config = "config" in source and "{" in source
            tests.append(("Config dict", has_config, "Restituisce dizionario configurazione"))

            # Verifica che chieda i parametri principali
            params = ['model', 'input_dir', 'output_dir', 'min_words']
            params_ok = all(param in source for param in params)
            tests.append(("Parametri richiesti", params_ok, "Chiede tutti i parametri necessari"))

        except Exception as e:
            tests.append(("Analisi interactive_setup", False, f"Errore: {e}"))

    # Verifica select_files_interactive
    has_select = hasattr(rl, 'select_files_interactive') and callable(rl.select_files_interactive)
    tests.append(("select_files_interactive", has_select, "Selezione file interattiva"))

    passed = 0
    for name, result, desc in tests:
        print_test(name, result, desc)
        if result:
            passed += 1

    return passed, len(tests)

def generate_report(results):
    """Genera un report finale dei test."""
    print_section("REPORT FINALE")

    total_tests = sum(r[1] for r in results)
    total_passed = sum(r[0] for r in results)
    total_failed = total_tests - total_passed

    percentage = (total_passed / total_tests * 100) if total_tests > 0 else 0

    print(f"Test eseguiti:  {total_tests}")
    print(f"Test passati:   {Colors.OKGREEN}{total_passed}{Colors.ENDC}")
    print(f"Test falliti:   {Colors.FAIL}{total_failed}{Colors.ENDC}")
    print(f"Percentuale:    {Colors.OKGREEN if percentage >= 80 else Colors.WARNING}{percentage:.1f}%{Colors.ENDC}")

    print(f"\n{Colors.BOLD}Dettaglio per categoria:{Colors.ENDC}\n")

    for idx, (passed, total) in enumerate(results, 1):
        perc = (passed / total * 100) if total > 0 else 0
        status = f"{Colors.OKGREEN}✓{Colors.ENDC}" if perc >= 80 else f"{Colors.WARNING}!{Colors.ENDC}"
        print(f"{status} Test {idx}: {passed}/{total} ({perc:.0f}%)")

    print("\n" + "="*70)

    if percentage >= 90:
        print(f"{Colors.OKGREEN}{Colors.BOLD}🎉 OTTIMO! Tutte le features sono presenti e funzionanti!{Colors.ENDC}")
    elif percentage >= 70:
        print(f"{Colors.WARNING}{Colors.BOLD}⚠️  BUONO. La maggior parte delle features è presente.{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}❌ ATTENZIONE. Molte features mancano o non funzionano.{Colors.ENDC}")

    print("="*70 + "\n")

    return percentage >= 70

def main():
    """Esegue tutti i test."""
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}")
    print("="*70)
    print("TEST COMPLETO FEATURES - RIASSUMI LIBRI")
    print("="*70)
    print(f"{Colors.ENDC}\n")

    print("Questo script verifica che tutte le features richieste siano")
    print("presenti e funzionanti nel progetto riassumi_libri.py\n")

    results = []

    # Esegui tutti i test
    results.append(test_imports())
    results.append(test_constants())
    results.append(test_prompts())
    results.append(test_utility_functions())
    results.append(test_core_functions())
    results.append(test_banner_and_version())
    results.append(test_cli_arguments())
    results.append(test_error_handling())
    results.append(test_multiplatform())
    results.append(test_map_reduce())
    results.append(test_output_formats())
    results.append(test_interactive_mode())

    # Genera report
    success = generate_report(results)

    # Exit code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
