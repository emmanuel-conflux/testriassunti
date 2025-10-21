# Meccanismo di Ripresa (Resume)

## Panoramica

Il sistema di riassunto libri ora supporta la ripresa dell'elaborazione, permettendo di interrompere e rilanciare il processo senza rigenerare i capitoli già completati.

## Struttura Output

Per ogni libro elaborato, viene creata la seguente struttura:

```
C:\riassunti\<TitoloLibro>\
  ├── chapters\                 # riassunti per capitolo (Markdown)
  │   ├── 01_Capitolo1_a1b2c3d4.md
  │   ├── 02_Capitolo2_9f0e1d2c.md
  │   └── ...
  ├── state.json                # stato/progresso
  ├── final.docx                # generato solo a completamento
  └── final.md                  # generato solo a completamento
```

### Nome File Capitoli

Formato: `NN_<titolo-sanitizzato>_<hash8>.md`

- **NN**: numero capitolo a 2 cifre (01, 02, ...)
- **titolo-sanitizzato**: titolo del capitolo con caratteri speciali rimossi
- **hash8**: primi 8 caratteri SHA1 delle prime 8000 battute del capitolo

## File di Stato (state.json)

Esempio:

```json
{
  "book_title": "IlMioLibro",
  "total_chapters": 91,
  "completed": [1, 2, 3, 4, 5],
  "chapter_hashes": {
    "1": "a1b2c3d4",
    "2": "9f0e1d2c",
    "3": "e5f6a7b8",
    "4": "c9d0e1f2",
    "5": "a3b4c5d6"
  },
  "model": "qwen3:8b",
  "timestamp": "2025-10-21T10:30:00"
}
```

### Campi

- **book_title**: titolo del libro (sanitizzato)
- **total_chapters**: numero totale di capitoli
- **completed**: array di indici capitoli completati (1-based)
- **chapter_hashes**: mappa indice → hash per verifica integrità
- **model**: modello Ollama utilizzato
- **timestamp**: timestamp ultimo aggiornamento (ISO-8601)

## Logica di Ripresa

All'avvio, lo script:

1. **Carica state.json** (se presente)
2. **Per ogni capitolo**:
   - Calcola hash corrente (SHA1 prime 8000 battute)
   - Verifica 3 condizioni:
     - Capitolo in `completed`
     - Hash coincide con `chapter_hashes[i]`
     - Esiste file `.md` con hash nel nome
   - Se **tutte e 3 OK** → **salta** (⏭️)
   - Altrimenti → **rielabora** (📘)

### Casi Speciali

#### state.json mancante o corrotto

- Tenta ricostruzione scansionando directory `chapters/`
- Estrae indici e hash dai nomi file
- Se nessun file presente, parte da zero

#### Capitolo modificato

- Hash cambiato → rielabora capitolo
- Aggiorna hash e file in `chapters/`
- Aggiorna `state.json`

#### File .md mancante

- Anche se capitolo in `completed` e hash coincide
- Se file mancante → rielabora

## Generazione Finale

I file `final.md` e `final.docx` vengono creati **solo** quando:

```
len(completed) == total_chapters
```

Se l'elaborazione è incompleta:
- I file finali **NON** vengono creati/aggiornati
- Vengono stampati i capitoli mancanti
- Output parziali salvati in `chapters/`

## Robustezza

### File Aperti (es. Word)

Se `final.docx` è aperto:
- Salva con suffisso `-1`, `-2`, ...
- Messaggio: `ℹ️  File principale occupato, salvo come: final-1.docx`

### Salvataggio Atomico

`state.json` usa salvataggio atomico:
1. Scrivi su `state.json.tmp`
2. Rinomina (`os.replace()`) atomicamente
3. Evita corruzione in caso di crash

### Gestione Errori Ollama

Retry con backoff esponenziale:
- 3 tentativi: 2s, 4s, 8s
- Timeout HTTP: 180 secondi

## Parametri CLI

```bash
python riassumi_libri.py \
  --model qwen3:8b \
  --input_dir C:\dariassumere \
  --output_dir C:\riassunti \
  --min_words 300 \
  --language it
```

### Parametri Ollama

- `temperature`: 0.3
- `num_ctx`: 32768
- `num_predict`: 2048
- `timeout`: 180s

### Chunking

- Dimensione max: 12000 caratteri
- Overlap: 600 caratteri

## UX / Logging

### Emoji

- ⏭️ : capitolo saltato (già elaborato)
- 📘 : capitolo in elaborazione
- ✅ : operazione completata
- ⚠️ : warning (hash cambiato, file mancante, ecc.)
- ❌ : errore
- ℹ️ : informazione

### Fasi

```
[1/4] Estrazione capitoli
[2/4] Riassunto capitoli
[3/4] Sintesi globale
[4/4] Scrittura file finali
```

### Esempio Output

```
[2/4] Riassunto capitoli

   ℹ️  Ripresa elaborazione: 10/91 capitoli completati

   ⏭️  Capitolo 1/91 — già riassunto (hash a1b2c3d4)
   ⏭️  Capitolo 2/91 — già riassunto (hash 9f0e1d2c)
   ...
   ⏭️  Capitolo 10/91 — già riassunto (hash e5f6a7b8)

   📘 Capitolo 11/91 — Introduzione
      Elaboro chunk 1/3...
      Elaboro chunk 2/3...
      Elaboro chunk 3/3...
      🔄 Unisco 3 riassunti parziali...
   ✅ Completato

   📘 Capitolo 12/91 — La storia
   ✅ Completato
```

## Criteri di Accettazione

### ✅ Test 1: Interruzione

1. Avvia elaborazione
2. Interrompi dopo 10 capitoli (Ctrl+C)
3. Rilancia script
4. **Verifica**: riprende da capitolo 11, salta 1-10

### ✅ Test 2: Modifica Contenuto

1. Elabora libro completo
2. Modifica file di input (cambia un capitolo)
3. Rilancia script
4. **Verifica**: ricalcola solo capitoli con hash cambiato

### ✅ Test 3: Completamento

1. Elabora libro fino alla fine
2. **Verifica**: presenti `final.md` e `final.docx` in `C:\riassunti\<TitoloLibro>\`

### ✅ Test 4: Locale

- **Verifica**: nessuna chiamata a servizi esterni
- Tutto via `http://localhost:11434/api/generate`

## Limitazioni Note

- Linux usa percorsi `/` invece di `\` (gestito automaticamente da `os.path.join`)
- Hash calcolato solo su prime 8000 battute (performance vs. accuratezza)
- File aperti gestiti con suffissi (no lock file)
