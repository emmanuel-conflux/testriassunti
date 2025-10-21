# 📚 Riassumi Libri - CLI Tool via Ollama (OTTIMIZZATO)

Tool CLI in Python per generare riassunti dettagliati di libri (EPUB/PDF) utilizzando Ollama locale.

## ✨ Novità Versione Ottimizzata

### 🚀 Velocità & Efficienza
- **Filtro intelligente**: Esclude automaticamente front/back matter (copyright, TOC, indice, ecc.)
- **Merge sezioni corte**: Unisce sezioni consecutive troppo brevi per ridurre i capitoli
- **Parametri ottimizzati**: MAP 300 parole, REDUCE 550 parole, num_predict 800 token
- **Chunking efficiente**: 16.000 caratteri con overlap 400

### 💾 Resume Robusto
- **Checkpoint per capitolo**: Salva progress in `state.json`
- **Hash-based tracking**: Rileva modifiche ai capitoli
- **Ripresa sicura**: Interrompi e riprendi senza perdere lavoro
- **Verifica hash**: Rigenera solo capitoli modificati

### 🔍 Dry-Run
- Modalità `--dry_run` per vedere cosa verrà elaborato
- Report dettagliato con statistiche
- Stima tempo di elaborazione
- Nessuna chiamata a Ollama

## 🎯 Caratteristiche

- **Analisi locale**: Tutto funziona offline tramite Ollama
- **Supporto formati**: EPUB e PDF
- **Riassunti dettagliati**: Capitolo per capitolo con sintesi globale
- **Output multipli**: File Word (.docx) e Markdown (.md)
- **MAP-REDUCE**: Gestione intelligente di testi lunghi
- **Multilingua**: Output sempre in italiano, anche per libri in altre lingue
- **Progress tracking**: Logging dettagliato con fasi chiare
- **Configurabile**: Tutti i parametri personalizzabili via CLI

## 🔧 Requisiti

### Sistema

- **OS**: Windows 11 (compatibile anche Linux/macOS con path adattati)
- **Python**: 3.11 o superiore
- **RAM**: Minimo 8 GB (consigliato 16+ GB per modelli grandi)
- **Ollama**: Installato e in esecuzione

### Software

#### Installazione Ollama

1. Scarica Ollama da [ollama.com](https://ollama.com)
2. Installa e avvia il servizio
3. Scarica il modello predefinito:
   ```bash
   ollama pull qwen3:8b
   ```
4. Verifica che Ollama sia attivo:
   ```bash
   curl http://localhost:11434/api/tags
   ```

#### Python e Dipendenze

```bash
pip install -r requirements.txt
```

**Dipendenze principali:**
- `requests` - Comunicazione con Ollama
- `tqdm` - Barre di progresso
- `EbookLib` - Lettura EPUB
- `beautifulsoup4` - Parsing HTML/XML
- `PyPDF2` - Lettura PDF
- `python-docx` - Generazione Word

## 📁 Struttura Directory

```
C:\
├── dariassumere\          # Input: file EPUB/PDF
│   ├── libro1.epub
│   ├── libro2.pdf
│   └── ...
│
└── riassunti\             # Output: riassunti generati
    └── libro1\
        ├── chapters\      # Capitoli singoli (checkpoint)
        │   ├── 01_Chapter_One_a1b2c3d4.md
        │   ├── 02_Chapter_Two_e5f6g7h8.md
        │   └── ...
        ├── state.json     # Stato resume
        ├── final.docx     # Riassunto completo DOCX
        └── final.md       # Riassunto completo Markdown
```

## 🚀 Utilizzo

### Esecuzione Base

```bash
python riassumi_libri.py
```

Questo comando:
1. Cerca file `.epub` e `.pdf` in `C:\dariassumere`
2. Li elabora con il modello `qwen3:8b`
3. Salva i riassunti in `C:\riassunti`

### Modalità Dry-Run (CONSIGLIATO per primo uso)

```bash
python riassumi_libri.py --dry_run
```

Mostra:
- Quante sezioni verranno elaborate
- Quante verranno saltate (front/back matter)
- Quante verranno unite (merge)
- Stima tempo totale

### Parametri Configurabili

```bash
python riassumi_libri.py [opzioni]

Parametri principali:
  --model MODEL          Modello Ollama (default: qwen3:8b)
  --input_dir DIR        Directory input (default: C:\dariassumere)
  --output_dir DIR       Directory output (default: C:\riassunti)
  --language LANG        Lingua output (default: it)

Filtro capitoli:
  --min_words NUM        Parole minime per capitolo valido (default: 1000)
  --min_words_merge NUM  Soglia parole per merge (default: 500)
  --target_words_merge NUM Target parole dopo merge (default: 1500)

Chunking:
  --max_chars NUM        Max caratteri per chunk (default: 16000)
  --overlap NUM          Overlap tra chunk (default: 400)

Verbosità LLM:
  --map_words NUM        Parole target per MAP (default: 300)
  --reduce_words NUM     Parole target per REDUCE (default: 550)
  --num_predict NUM      Limitazione token output LLM (default: 800)

Modalità:
  --dry_run             Modalità dry-run (solo report, no elaborazione)
  -h, --help            Mostra questo messaggio
```

### Esempi

#### 1. Dry-run per vedere cosa succederà
```bash
python riassumi_libri.py --dry_run
```

#### 2. Usare un modello diverso
```bash
python riassumi_libri.py --model llama3:70b
```

#### 3. Directory personalizzate
```bash
python riassumi_libri.py --input_dir /path/to/books --output_dir /path/to/output
```

#### 4. Meno capitoli (più merge)
```bash
python riassumi_libri.py --min_words 1500 --target_words_merge 2000
```

#### 5. Riassunti più corti e veloci
```bash
python riassumi_libri.py --map_words 200 --reduce_words 400 --num_predict 600
```

#### 6. Configurazione completa
```bash
python riassumi_libri.py \
  --model qwen3:30b \
  --min_words 1200 \
  --map_words 250 \
  --reduce_words 500 \
  --num_predict 700
```

## 📖 Come Funziona

### [1/5] Scansione & Parsing

#### EPUB
- Legge lo spine del file per l'ordine di lettura
- Usa BeautifulSoup per pulire HTML (rimuove script, style, svg)
- Estrae titoli da tag `<h1>`, `<h2>`, `<h3>`
- Estrae tutte le sezioni (filtri applicati dopo)

#### PDF
- Estrae testo pagina per pagina
- Cerca pattern di capitoli: "Capitolo X", "Chapter X", numeri, ecc.
- Se non trova capitoli, suddivide in sezioni di ~3000 parole

### [2/5] Filtri & Merge Sezioni

#### Filtro Front/Back Matter
Esclude automaticamente sezioni con titoli che matchano (case-insensitive):
- **Front matter**: Cover, Copyright, TOC, Dedication, Foreword, Preface, Acknowledgments
- **Back matter**: Notes, Footnotes, References, Bibliography, Index, Glossary, About the Author

#### Filtro Parole Minime
Sezioni con meno di `min_words` (default 1000) vengono considerate per merge.

#### Merge Sezioni Corte
- Unisce sezioni consecutive con < `min_words_merge` parole (default 500)
- Continua fino a raggiungere `target_words_merge` (default 1500)
- Risultato: capitoli più sostanziosi e meno frammentazione

**Esempio:**
```
PRIMA (90 sezioni):
- Sezione 1: Cover (50 parole) → SKIPPED
- Sezione 2: TOC (100 parole) → SKIPPED
- Sezione 3: Chapter 1 (400 parole) → MERGED con 4
- Sezione 4: Continued (600 parole) → MERGED con 3
- Sezione 5: Chapter 2 (1800 parole) → KEPT
...

DOPO (35 capitoli):
- Capitolo 1: Chapter 1 (1000 parole) → KEPT (merged)
- Capitolo 2: Chapter 2 (1800 parole) → KEPT
...
```

### [3/5] Riassunto Capitoli (con Resume)

#### Checkpoint System
Per ogni capitolo:
1. Calcola hash MD5 del testo (8 caratteri)
2. Verifica se già presente in `state.json`
3. Se hash coincide e file esiste → SALTA
4. Altrimenti → GENERA riassunto
5. Salva in `chapters/NN_<titolo>_<hash>.md`
6. Aggiorna `state.json`

#### MAP-REDUCE
Per capitoli lunghi (>16.000 caratteri):
1. **MAP**: Suddivide in blocchi di max 16.000 char con overlap 400
2. Riassume ogni blocco separatamente (~300 parole)
3. **REDUCE**: Unisce i riassunti parziali (~550 parole)

Per capitoli brevi: riassunto diretto.

#### Retry Logic
- Timeout: 180 secondi per chiamata
- Max tentativi: 3
- Backoff esponenziale: 2s, 4s, 8s

### [4/5] Sintesi Globale

Genera riassunto complessivo del libro basato su tutti i capitoli con:
- Trama complessiva
- Temi e messaggi ricorrenti
- Evoluzione dei personaggi/idee
- Citazioni rappresentative
- Stile e tono
- Sintesi finale

### [5/5] Scrittura Output

#### File DOCX (`final.docx`)
- Copertina con titolo libro
- Indice capitoli
- Riassunti dettagliati per capitolo
- Sintesi complessiva finale
- Formattazione professionale

#### File Markdown (`final.md`)
- Struttura gerarchica con headers
- Indice numerato
- Separatori tra capitoli
- Sintesi complessiva finale

## 📊 Output di Esempio

```
================================================================================
📚 RIASSUMI LIBRI - CLI Tool via Ollama (OTTIMIZZATO)
================================================================================
Modello: qwen3:8b
Input: C:\dariassumere
Output: C:\riassunti
Min parole/capitolo: 1000
Min parole merge: 500
Target parole merge: 1500
Max chars/chunk: 16000
Overlap: 400
MAP words: 300
REDUCE words: 550
Num predict: 800
Dry-run: False
================================================================================

🔍 Verifica connessione a Ollama...
✅ Ollama raggiungibile

📁 Scansione C:\dariassumere
Trovati 1 file: Il_Nome_della_Rosa.epub

################################################################################
FILE 1/1
################################################################################

================================================================================
📚 Elaborazione: Il_Nome_della_Rosa.epub
================================================================================

[1/5] Scansione & parsing
✅ Estratte 87 sezioni

[2/5] Filtri & merge sezioni
✅ Capitoli finali: 32 (merged: 18, skipped: 55)

♻️  Resume da checkpoint: 15/32 completati

[3/5] Riassunto capitoli (32 totali)

   ⏭️  Salto 1/32 — già riassunto (hash a1b2c3d4)
   ⏭️  Salto 2/32 — già riassunto (hash e5f6g7h8)
   ...
   ⏭️  Salto 15/32 — già riassunto (hash x9y8z7w6)

   📘 Capitolo 16/32 — Primo giorno - Terza (~1450 parole)
   ✅ Completato

   📘 Capitolo 17/32 — Primo giorno - Sesta (~2100 parole)
      📄 Capitolo lungo (18240 char), applico MAP-REDUCE...
         Elaboro chunk 1/2...
         Elaboro chunk 2/2...
      🔄 Unisco 2 riassunti parziali...
   ✅ Completato

[... continua ...]

[4/5] Sintesi globale
✅ Riassunto complessivo generato

[5/5] Scrittura output
✅ DOCX: C:\riassunti\Il_Nome_della_Rosa\final.docx
✅ MD: C:\riassunti\Il_Nome_della_Rosa\final.md

================================================================================
✅ OPERAZIONE COMPLETATA
================================================================================
File elaborati: 1/1
Output salvati in: C:\riassunti
================================================================================
```

## 🧪 Dry-Run Report Esempio

```bash
python riassumi_libri.py --dry_run
```

Output:
```
================================================================================
📊 DRY-RUN REPORT
================================================================================

#     Titolo                                   Parole     Status
--------------------------------------------------------------------------------
1     Cover                                    45         skipped (front/back matter)
2     Copyright                                120        skipped (front/back matter)
3     Table of Contents                        85         skipped (front/back matter)
4     Prologue                                 980        skipped (< min_words)
5     Chapter 1: The Beginning                 1850       kept
6     Chapter 2: The Mystery                   420        kept (merged)
7     Chapter 3: Continued                     650        kept (merged)
8     Chapter 4: The Revelation                2100       kept
...
85    Notes                                    340        skipped (front/back matter)
86    Bibliography                             190        skipped (front/back matter)
87    About the Author                         75         skipped (front/back matter)
--------------------------------------------------------------------------------

📈 STATISTICHE:
   Sezioni originali: 87
   Capitoli finali (kept): 35
   Sezioni merged: 12
   Sezioni skipped: 52
   Tempo stimato: ~87.5 minuti (1.5 ore)
================================================================================
```

## 🔄 Resume & Interruzioni

### Scenario 1: Interruzione Durante Elaborazione

```bash
# Prima esecuzione
python riassumi_libri.py
# ... elabora capitoli 1-15 ...
# CTRL+C (interruzione)

⚠️  Interruzione utente. Progress salvato.
```

```bash
# Riprendi
python riassumi_libri.py
# Riparte dal capitolo 16

♻️  Resume da checkpoint: 15/32 completati

[3/5] Riassunto capitoli (32 totali)
   ⏭️  Salto 1/32 — già riassunto (hash a1b2c3d4)
   ...
   📘 Capitolo 16/32 — ...
```

### Scenario 2: Modifica al Libro

Se modifichi l'EPUB (es. correzione typo), solo i capitoli modificati verranno rigenerati:

```bash
python riassumi_libri.py

♻️  Resume da checkpoint: 32/32 completati
   ⏭️  Salto 1/32 — già riassunto (hash a1b2c3d4)
   🔄 Capitolo 5/32 — hash cambiato, rigenero
   ⏭️  Salto 6/32 — già riassunto (hash k9l8m7n6)
   ...
```

### Scenario 3: Cambio Modello

```bash
python riassumi_libri.py --model llama3:70b

⚠️  Modello cambiato (qwen3:8b → llama3:70b), rigenero tutto
🆕 Nuovo processing
```

## 🛠️ Modelli Ollama Consigliati

### Bilanciati (Qualità/Velocità)
- **qwen3:8b** (default) - Ottimo compromesso, veloce
- **llama3:8b** - Molto veloce, buona qualità
- **mistral:7b** - Rapido e accurato

### Alta Qualità (richiede più RAM)
- **qwen3:30b** - Eccellente per analisi complesse
- **llama3:70b** - Top qualità (richiede 40+ GB RAM)
- **mixtral:8x7b** - Ottimo per testi lunghi

### Download Modelli

```bash
# Scarica modello
ollama pull qwen3:8b

# Lista modelli installati
ollama list

# Rimuovi modello
ollama rm nome_modello
```

## 🐛 Troubleshooting

### Ollama non raggiungibile
```
❌ Errore connessione Ollama: ...
```
**Soluzione**: Verifica che Ollama sia in esecuzione:
```bash
# Windows
ollama serve

# Verifica status
curl http://localhost:11434/api/tags
```

### Modello non trovato
```
❌ Errore Ollama: model not found
```
**Soluzione**: Scarica il modello:
```bash
ollama pull qwen3:8b
```

### Memoria insufficiente
```
❌ Errore Ollama: out of memory
```
**Soluzione**:
1. Usa un modello più piccolo (es. `qwen3:8b` invece di `qwen3:30b`)
2. Chiudi altre applicazioni
3. Riavvia Ollama

### Troppi capitoli generati
```
✅ Capitoli finali: 90 (merged: 5, skipped: 10)
```
**Soluzione**: Aumenta soglie merge:
```bash
python riassumi_libri.py --min_words 1500 --target_words_merge 2000
```

### Nessun capitolo valido
```
❌ Nessun capitolo valido dopo filtri
```
**Soluzione**: Riduci soglia minima:
```bash
python riassumi_libri.py --min_words 500
```

### State.json corrotto
Elimina manualmente `C:\riassunti\<Libro>\state.json` e rilancia. Il tool scansionerà i capitoli esistenti e ricostruirà lo stato.

## ⚙️ Parametri Ottimizzati per Casi d'Uso

### Libro lungo (500+ pagine), velocità massima
```bash
python riassumi_libri.py \
  --model qwen3:8b \
  --min_words 1500 \
  --target_words_merge 2500 \
  --map_words 200 \
  --reduce_words 400 \
  --num_predict 600
```
**Risultato**: ~20-30 capitoli, 1-2 min/capitolo

### Libro medio (200-300 pagine), bilanciato
```bash
python riassumi_libri.py
# (usa tutti i default)
```
**Risultato**: ~30-40 capitoli, 2-3 min/capitolo

### Libro corto (100 pagine), qualità massima
```bash
python riassumi_libri.py \
  --model qwen3:30b \
  --min_words 800 \
  --map_words 400 \
  --reduce_words 700 \
  --num_predict 1000
```
**Risultato**: ~15-20 capitoli, 4-6 min/capitolo

### PDF tecnico/accademico (molte sezioni)
```bash
python riassumi_libri.py \
  --min_words 1200 \
  --min_words_merge 600 \
  --target_words_merge 2000
```
**Risultato**: Merge più aggressivo, capitoli più lunghi

## 📝 Note Tecniche

### Chunking
- **Max size**: 16.000 caratteri per blocco (configurabile)
- **Overlap**: 400 caratteri tra blocchi (configurabile)
- **Divisione**: Cerca punti naturali (`.`, `\n`, spazio)

### Limiti Ollama
- **Context window**: 32.768 token
- **Temperature**: 0.3 (bilanciato tra creatività e coerenza)
- **Timeout**: 180 secondi per chiamata
- **num_predict**: 800 token (limita output, velocizza)

### Performance
- **EPUB medio** (10-15 capitoli): ~25-40 minuti con qwen3:8b
- **EPUB lungo** (30+ capitoli): ~60-90 minuti
- **PDF medio**: ~30-50 minuti
- **Dipende da**: CPU, RAM, modello scelto, lunghezza libro, parametri

### Hash System
- Usa MD5 (primi 8 caratteri)
- Rileva modifiche al testo del capitolo
- Filename: `NN_<titolo>_<hash>.md`
- Ricostruisce `state.json` da file esistenti se corrotto

## 🔮 Sviluppi Futuri

- [ ] GUI con Tkinter
- [ ] Supporto altri formati (MOBI, AZW3, TXT)
- [ ] Elaborazione parallela capitoli
- [ ] Esportazione HTML/LaTeX
- [ ] Prompt personalizzabili (file config)
- [ ] Multi-lingua output
- [ ] Statistiche dettagliate (tempo/capitolo, token usage)

## 📄 Licenza

Questo progetto è fornito "as-is" per uso personale ed educativo.

## 🤝 Contributi

Suggerimenti e miglioramenti sono benvenuti! Apri una issue o pull request.

---

**Sviluppato con ❤️ e Claude Code**
