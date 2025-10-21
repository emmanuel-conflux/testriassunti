#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test per il meccanismo di ripresa.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Import funzioni da riassumi_libri
sys.path.insert(0, os.path.dirname(__file__))
from riassumi_libri import (
    chapter_hash,
    ensure_resume_dirs,
    load_state,
    save_state,
    chapter_filename,
    should_skip_chapter,
    rebuild_state_from_chapters,
    sanitize_filename
)


def test_chapter_hash():
    """Test calcolo hash capitolo."""
    print("Test: chapter_hash()")

    text1 = "A" * 8000 + "B" * 1000
    text2 = "A" * 8000 + "C" * 1000

    hash1 = chapter_hash(text1)
    hash2 = chapter_hash(text2)

    assert len(hash1) == 8, f"Hash length should be 8, got {len(hash1)}"
    assert hash1 == hash2, "Hashes should match (same first 8000 chars)"

    text3 = "B" * 8000
    hash3 = chapter_hash(text3)
    assert hash1 != hash3, "Different texts should have different hashes"

    print("  ✅ chapter_hash() OK")


def test_sanitize_filename():
    """Test sanitizzazione nome file."""
    print("Test: sanitize_filename()")

    assert sanitize_filename("Test.epub") == "Test"

    # Verifica che caratteri speciali vengano sostituiti
    result = sanitize_filename("Test<File>.pdf")
    assert "<" not in result and ">" not in result
    assert result.replace("_", "") == "TestFile"  # Senza underscore dovrebbe essere TestFile

    assert sanitize_filename("  Spazi  .epub") == "Spazi"

    print("  ✅ sanitize_filename() OK")


def test_chapter_filename():
    """Test generazione nome file capitolo."""
    print("Test: chapter_filename()")

    filename = chapter_filename(1, "Introduzione", "a1b2c3d4")
    assert filename == "01_Introduzione_a1b2c3d4.md"

    filename = chapter_filename(42, "Test<>:?", "12345678")
    assert filename.startswith("42_Test")
    assert filename.endswith("_12345678.md")
    assert "<" not in filename and ">" not in filename

    print("  ✅ chapter_filename() OK")


def test_state_persistence():
    """Test salvataggio e caricamento stato."""
    print("Test: save_state() / load_state()")

    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = os.path.join(tmpdir, "state.json")

        # Salva stato
        state = {
            'book_title': 'TestBook',
            'total_chapters': 10,
            'completed': [1, 2, 3],
            'chapter_hashes': {'1': 'abc', '2': 'def', '3': 'ghi'},
            'model': 'qwen3:8b'
        }

        save_state(state_file, state)

        # Verifica file esiste
        assert os.path.exists(state_file), "State file should exist"

        # Carica stato
        loaded = load_state(state_file)
        assert loaded is not None, "State should load"
        assert loaded['book_title'] == 'TestBook'
        assert loaded['total_chapters'] == 10
        assert loaded['completed'] == [1, 2, 3]
        assert 'timestamp' in loaded, "Timestamp should be added"

        print("  ✅ save_state() / load_state() OK")


def test_should_skip_chapter():
    """Test logica skip capitolo."""
    print("Test: should_skip_chapter()")

    with tempfile.TemporaryDirectory() as tmpdir:
        chapters_dir = os.path.join(tmpdir, "chapters")
        os.makedirs(chapters_dir)

        # Calcola hash effettivo del testo
        text1 = "A" * 8000
        hash1 = chapter_hash(text1)

        # Stato con capitolo 1 completato
        state = {
            'book_title': 'Test',
            'total_chapters': 3,
            'completed': [1],
            'chapter_hashes': {'1': hash1},
            'model': 'qwen3:8b'
        }

        # Crea file capitolo 1 con hash corretto
        ch1_file = os.path.join(chapters_dir, f"01_Chapter1_{hash1}.md")
        with open(ch1_file, 'w') as f:
            f.write("# Chapter 1\n\nContent")

        # Test 1: capitolo completato, hash coincide, file esiste → skip
        skip, hash_val = should_skip_chapter(1, text1, state, chapters_dir)
        assert skip == True, f"Should skip chapter 1 (hash={hash1})"

        # Test 2: capitolo non completato → no skip
        skip, hash_val = should_skip_chapter(2, text1, state, chapters_dir)
        assert skip == False, "Should not skip chapter 2 (not completed)"

        # Test 3: hash cambiato → no skip
        text_changed = "B" * 8000
        skip, hash_val = should_skip_chapter(1, text_changed, state, chapters_dir)
        assert skip == False, "Should not skip chapter 1 (hash changed)"

        print("  ✅ should_skip_chapter() OK")


def test_rebuild_state():
    """Test ricostruzione stato da file."""
    print("Test: rebuild_state_from_chapters()")

    with tempfile.TemporaryDirectory() as tmpdir:
        chapters_dir = os.path.join(tmpdir, "chapters")
        os.makedirs(chapters_dir)

        # Crea alcuni file capitoli
        files = [
            "01_Chapter1_a1b2c3d4.md",
            "02_Chapter2_e5f6a7b8.md",
            "05_Chapter5_c9d0e1f2.md"
        ]

        for filename in files:
            filepath = os.path.join(chapters_dir, filename)
            with open(filepath, 'w') as f:
                f.write(f"# {filename}\n\nContent")

        # Ricostruisci stato
        state = rebuild_state_from_chapters(chapters_dir, "TestBook", 10, "qwen3:8b")

        assert state['book_title'] == "TestBook"
        assert state['total_chapters'] == 10
        assert sorted(state['completed']) == [1, 2, 5]
        assert state['chapter_hashes']['1'] == 'a1b2c3d4'
        assert state['chapter_hashes']['2'] == 'e5f6a7b8'
        assert state['chapter_hashes']['5'] == 'c9d0e1f2'

        print("  ✅ rebuild_state_from_chapters() OK")


def main():
    """Esegue tutti i test."""
    print("\n" + "="*60)
    print("Test Meccanismo di Ripresa")
    print("="*60 + "\n")

    try:
        test_chapter_hash()
        test_sanitize_filename()
        test_chapter_filename()
        test_state_persistence()
        test_should_skip_chapter()
        test_rebuild_state()

        print("\n" + "="*60)
        print("✅ Tutti i test completati con successo!")
        print("="*60 + "\n")

        return 0

    except AssertionError as e:
        print(f"\n❌ Test fallito: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Errore imprevisto: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
