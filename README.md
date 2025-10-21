# 📚 Riassumi Libri - CLI Tool via Ollama

Tool CLI in Python per generare riassunti di libri (EPUB/PDF) utilizzando Ollama locale.

## ⚡ Due Modalità Disponibili

### 📖 **riassumi.py** - Modalità Dettagliata
Analisi completa capitolo per capitolo con riassunti approfonditi.
- ✅ Riassunti dettagliati (400-900 parole per capitolo)
- ✅ Output DOCX + Markdown con formattazione professionale
- ✅ Sistema checkpoint/resume per riprendere lavori interrotti
- ✅ MAP-REDUCE completo per gestione testi lunghi
- ⏱️ **Tempo**: ~10-30 minuti per libro medio

### ⚡ **riassuntiveloci.py** - Modalità Ultra-Veloce (NUOVO!)
Approccio radicalmente diverso per velocità massima.
- ✅ **5-10x più veloce** tramite sampling intelligente
- ✅ Riassunti concisi (300 parole per estratto, 500 per globale)
- ✅ Output Markdown minimalista
- ✅ Niente overhead: esecuzione diretta senza checkpoint
- ⚡ **Tempo**: ~2-5 minuti per libro medio

**Quale scegliere?**
- 📖 Usa `riassumi.py` per analisi approfondite, documenti di studio, o quando hai tempo
- ⚡ Usa `riassuntiveloci.py` per overview rapide, screening libri, o quando hai fretta

---

## 🎯 Caratteristiche (riassumi.py)

- **Analisi locale**: Tutto funziona offline tramite Ollama
- **Supporto formati**: EPUB e PDF
- **Riassunti dettagliati**: Capitolo per capitolo con sintesi globale
- **Output multipli**: File Word (.docx) e Markdown (.md)
- **MAP-REDUCE**: Gestione intelligente di testi lunghi
- **Chunk configurabile**: Ottimizza velocità scegliendo dimensione blocchi (piccolo/medio/grande)
- **Checkpoint/Resume**: Riprendi lavori interrotti dal punto esatto dove ti eri fermato
- **Modalità interattiva**: Configurazione guidata user-friendly con domande passo-passo
- **Multilingua**: Output sempre in italiano, anche per libri in altre lingue
- **Progress tracking**: Barra di progresso e logging dettagliato
- **Configurabile**: Parametri CLI personalizzabili o modalità interattiva

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
# Installa Python 3.11+ se necessario
# Poi installa le dipendenze:

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
    ├── libro1.riassunto.docx
    ├── libro1.riassunto.md
    ├── libro1.veloce.md      # Output modalità veloce
    ├── libro2.riassunto.docx
    ├── libro2.riassunto.md
    └── libro2.veloce.md      # Output modalità veloce
```

## 🚀 Utilizzo

### ⚡ RIASSUNTIVELOCI.PY - Modalità Ultra-Veloce

#### Esecuzione Base
```bash
python riassuntiveloci.py
```

Il programma:
1. Scansiona la directory input
2. Per ogni libro:
   - Estrae tutto il testo rapidamente
   - **Campiona 5 chunk strategici** (inizio, 3 intermedi, fine)
   - Genera riassunti ultra-concisi (max 300 parole per chunk)
   - Crea un riassunto globale (max 500 parole)
3. Salva output in `.veloce.md` (solo Markdown)

#### Parametri
```bash
python riassuntiveloci.py [opzioni]

Opzioni:
  --model MODEL          Modello Ollama (default: qwen3:8b)
  --input_dir DIR        Directory input (default: ~/dariassumere)
  --output_dir DIR       Directory output (default: ~/riassunti)
  --max_chunks NUM       Max chunk da campionare (default: 5)
  -h, --help             Mostra questo messaggio
```

#### Esempi
```bash
# Esecuzione standard (5 chunk campionati)
python riassuntiveloci.py

# Campionamento più dettagliato (8 chunk)
python riassuntiveloci.py --max_chunks 8

# Modello più veloce
python riassuntiveloci.py --model llama3:8b

# Directory personalizzate
python riassuntiveloci.py --input_dir /path/to/books --output_dir /path/to/output
```

#### Output di Esempio
```
============================================================
⚡ RIASSUNTI VELOCI - CLI Tool ULTRA-VELOCE via Ollama
============================================================
Versione: 2.0.0-VELOCE
OTTIMIZZAZIONI VELOCITÀ:
  • Sampling intelligente (non tutti i capitoli)
  • Riassunti ultra-concisi (max 300 parole)
  • Chunk enormi (32k caratteri, massima efficienza)
  • Retry automatico per timeout (max 2 tentativi)
  • Timeout esteso (10 minuti per chunk)
  • Output minimalista

GUADAGNO: 5-10x più veloce di riassumi.py
============================================================

[1/3] ⚡ Estrazione rapida testo completo...
✅ Estratte ~87,423 parole

[2/3] ⚡ Sampling intelligente e riassunti rapidi...
   📊 Campionati 5 chunk strategici
   (inizio, 3 intermedi, fine)
   ⚡ Chunk 1/5... ✅
   ⚡ Chunk 2/5... ✅
   ⚡ Chunk 3/5... ✅
   ⚡ Chunk 4/5... ✅
   ⚡ Chunk 5/5... ✅
✅ 5 riassunti parziali generati

[3/3] ⚡ Generazione riassunto globale rapido...
✅ Riassunto globale generato

[4/4] ⚡ Scrittura output minimalista...
✅ MD: ~/riassunti/Il_Nome_della_Rosa.veloce.md

============================================================
⚡ COMPLETATO IN MODALITÀ VELOCE
============================================================
File elaborati: 1/1
Output salvati in: ~/riassunti
Suffisso file: .veloce.md
============================================================
```

---

### 📖 RIASSUMI.PY - Modalità Dettagliata

### Esecuzione Base

```bash
python riassumi.py
```

Quando lanciato senza parametri, il programma:
1. **Chiede** se vuoi usare la configurazione interattiva guidata
   - Se rispondi **sì** (o premi INVIO): ti guida nella configurazione completa
   - Se rispondi **no**: usa i valori predefiniti
2. Cerca file `.epub` e `.pdf` nella directory input
3. Li elabora con Ollama
4. Salva i riassunti nella directory output

#### Modalità Interattiva Esplicita

Puoi saltare la domanda e avviare direttamente la modalità interattiva:

```bash
python riassumi.py --interactive
```

### Parametri Configurabili

```bash
python riassumi.py [opzioni]

Opzioni:
  -i, --interactive      Avvia modalità interattiva guidata (salta la domanda)
  --model MODEL          Modello Ollama (default: qwen3:8b)
  --input_dir DIR        Directory input (default: ~/dariassumere)
  --output_dir DIR       Directory output (default: ~/riassunti)
  --min_words NUM        Parole minime per capitolo (default: 300)
  --chunk_size NUM       Dimensione chunk in caratteri (default: 12000)
  --language LANG        Lingua output (default: it)
  -h, --help             Mostra questo messaggio
```

**Nota**: Se specifichi parametri da linea di comando, il programma NON chiederà se vuoi usare la modalità interattiva.

### Esempi

#### Usare un modello diverso
```bash
python riassumi.py --model llama3:70b
```

#### Directory personalizzate
```bash
python riassumi.py --input_dir /path/to/books --output_dir /path/to/output
```

#### Capitoli più lunghi
```bash
python riassumi.py --min_words 500
```

#### Configurazione completa
```bash
python riassumi.py \
  --model qwen3:30b \
  --input_dir "D:\Libri" \
  --output_dir "D:\Riassunti" \
  --min_words 400
```

## 📖 Come Funziona

### 📖 RIASSUMI.PY - Approccio Dettagliato

#### 1. Estrazione Capitoli

#### EPUB
- Legge lo spine del file per l'ordine di lettura
- Usa BeautifulSoup per pulire HTML (rimuove script, style, svg)
- Estrae titoli da tag `<h1>`, `<h2>`, `<h3>`
- Filtra capitoli con meno di `min_words` parole

#### PDF
- Estrae testo pagina per pagina
- Cerca pattern di capitoli: "Capitolo X", "Chapter X", numeri, ecc.
- Se non trova capitoli, suddivide in sezioni di ~3000 parole
- Filtra sezioni troppo corte

### 2. Chunking (MAP-REDUCE)

Per capitoli lunghi (>12.000 caratteri):

1. **MAP**: Suddivide in blocchi di max 12.000 char con overlap di 600
2. **REDUCE**: Riassume ogni blocco separatamente
3. **MERGE**: Unisce i riassunti parziali in uno coerente

Per capitoli brevi: riassunto diretto.

### 3. Prompt Templates

#### MAP (riassunto parziale)
```
Sei un analista testuale.
Il testo può essere in italiano o inglese, ma rispondi solo in italiano.
Crea un riassunto dettagliato del seguente frammento.

# Sintesi (400–600 parole)
# Temi chiave
# Personaggi/Concetti principali
# Citazioni (se presenti)
# Osservazioni sullo stile
```

#### REDUCE (capitolo completo)
```
Unisci e armonizza i seguenti riassunti parziali del capitolo.
Rispondi in italiano, producendo un riassunto coerente (600–900 parole).
```

#### GLOBAL (sintesi libro)
```
Genera un riassunto complessivo in italiano con:
# Trama complessiva
# Temi e messaggi ricorrenti
# Evoluzione dei personaggi/idee
# Citazioni rappresentative
# Stile e tono
# Sintesi finale
```

### 4. Generazione Output

#### File DOCX
- Titolo principale centrato
- Indice con link ai capitoli
- Riassunti dettagliati per capitolo
- Sintesi complessiva finale
- Formattazione professionale

#### File Markdown
- Struttura gerarchica con headers
- Indice numerato
- Separatori tra capitoli
- Sintesi complessiva finale
- Formato universale e leggibile

### 5. Sistema Checkpoint/Resume

Il programma salva automaticamente il progresso dopo ogni capitolo completato:

- **Salvataggio automatico**: Checkpoint creato dopo ogni capitolo elaborato
- **Ripresa intelligente**: Se interrompi il programma (Ctrl+C, crash, ecc.), al prossimo avvio ti chiederà se vuoi riprendere
- **Validazione parametri**: Riprende solo se modello, chunk size e min_words sono gli stessi
- **File checkpoint**: Salvato in `.checkpoint_<nome_libro>.json` nella directory di output
- **Pulizia automatica**: Checkpoint rimosso al completamento con successo

**Esempio di ripresa:**
```
🔄 LAVORO INTERROTTO TROVATO
======================================================================
Libro: Il_Nome_della_Rosa
Data interruzione: 2025-10-21 14:32:15
Progresso: 7/10 capitoli (70.0%)
Modello: qwen3:8b
Chunk size: medio (12000 caratteri)
======================================================================

Vuoi riprendere da qui? (s/n) [s]: _
```

### 6. Gestione Errori

- **Retry Logic**: 3 tentativi con backoff esponenziale (2s, 4s, 8s)
- **Fallback**: Se un capitolo fallisce, continua con i successivi
- **Validazione**: Verifica connessione Ollama all'avvio
- **Logging**: Messaggi dettagliati per ogni fase

## 📊 Output di Esempio

```
============================================================
📚 RIASSUMI LIBRI - CLI Tool via Ollama
============================================================
Modello: qwen3:8b
Input: C:\dariassumere
Output: C:\riassunti
Min parole/capitolo: 300
============================================================

🔍 Verifica connessione a Ollama...
✅ Ollama raggiungibile

[1/4] Scansione C:\dariassumere
Trovati 2 file: Il_Nome_della_Rosa.epub, Brave_New_World.pdf

############################################################
FILE 1/2
############################################################

============================================================
📚 Elaborazione: Il_Nome_della_Rosa.epub
============================================================

[1/4] Estrazione capitoli da Il_Nome_della_Rosa.epub
✅ Trovati 10 capitoli

[2/4] Riassunto capitoli
   📖 Capitolo 1/10: Primo giorno - Prima
   ✅ Completato

   📖 Capitolo 2/10: Primo giorno - Terza
   📄 Capitolo lungo (15240 char), applico MAP-REDUCE...
      Elaboro chunk 1/2...
      Elaboro chunk 2/2...
   🔄 Unisco 2 riassunti parziali...
   ✅ Completato

[... continua ...]

[3/4] Generazione riassunto complessivo
✅ Riassunto complessivo generato

[4/4] Scrittura file di output
✅ DOCX: C:\riassunti\Il_Nome_della_Rosa.riassunto.docx
✅ MD: C:\riassunti\Il_Nome_della_Rosa.riassunto.md

============================================================
✅ OPERAZIONE COMPLETATA
============================================================
File elaborati: 2/2
Output salvati in: C:\riassunti
============================================================
```

---

### ⚡ RIASSUNTIVELOCI.PY - Approccio Ultra-Veloce

#### 1. Estrazione Rapida
- **EPUB/PDF**: Estrae tutto il testo in un colpo solo, senza parsing elaborato dei capitoli
- **Niente filtraggio**: Prende tutto il contenuto disponibile
- **Velocità massima**: Minimizza le operazioni di parsing

#### 2. Sampling Intelligente
Invece di elaborare tutto il libro, usa una strategia di campionamento:

1. **Chunk INIZIO**: Prime ~6400 parole (sempre importante per setup e personaggi)
2. **Chunk INTERMEDI**: 3 campioni distribuiti uniformemente nel testo
3. **Chunk FINE**: Ultime ~6400 parole (sempre importante per conclusioni)

**Totale**: 5 chunk strategici invece di 20+ capitoli completi

**Dimensione chunk**: 32.000 caratteri (vs 12.000 di riassumi.py)
→ 2.7x più grandi = Molte meno chiamate a Ollama = Molto più veloce

#### 3. Riassunti Ultra-Concisi

**Prompt veloce** (vs prompt elaborato di riassumi.py):
```
Riassumi il seguente testo in italiano.
Massimo 300 parole, solo concetti chiave.
```

**Prompt globale veloce**:
```
Basandoti su questi estratti, genera un riassunto complessivo del libro.
Massimo 500 parole.
```

#### 4. Ottimizzazioni Ollama
- **Temperature**: 0.7 (alta, meno "thinking" = più veloce)
- **Context window**: 32.000 token (ridotto vs 128.000 = più veloce)
- **Predict limit**: 500 token max per risposta
- **Retry limitato**: Max 2 tentativi per timeout occasionali (bilanciato)

#### 5. Output Minimalista
- **Solo Markdown**: Niente generazione DOCX (più lenta)
- **Formattazione essenziale**: Solo headers e separatori base
- **Niente indici elaborati**: Struttura semplice e diretta

#### 6. Confronto Velocità

| Aspetto | riassumi.py | riassuntiveloci.py | Guadagno |
|---------|-------------|---------------------|----------|
| Chunk processati | 20-30 | 5 | **4-6x meno** |
| Parole per riassunto | 600-900 | 300 | **2-3x meno** |
| Chiamate Ollama | 25-40 | 6 | **4-7x meno** |
| Context window | 128k | 32k | **4x ridotto** |
| Output generati | 2 (DOCX+MD) | 1 (MD) | **2x meno** |
| Checkpoint overhead | Sì | No | **0% overhead** |
| **Tempo totale** | **10-30 min** | **2-5 min** | **5-10x più veloce** |

---

## 🛠️ Modelli Ollama Consigliati

### Bilanciati (Qualità/Velocità)
- **qwen3:8b** (default) - Ottimo compromesso
- **llama3:8b** - Molto veloce, buona qualità
- **mistral:7b** - Rapido e accurato

### Alta Qualità (richiede più RAM)
- **qwen3:30b** - Eccellente per analisi complesse
- **llama3:70b** - Top qualità (richiede 40+ GB RAM)
- **mixtral:8x7b** - Ottimo per testi lunghi

### Download Modelli

```bash
# Scarica modello (esempio)
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

### Nessun capitolo estratto
```
❌ Nessun capitolo estratto
```
**Soluzione**:
1. Verifica che il file non sia corrotto
2. Riduci `--min_words` (es. `--min_words 100`)
3. Prova con un altro file per confermare il problema

### Dipendenze mancanti
```
⚠️ ebooklib o BeautifulSoup non disponibili
```
**Soluzione**:
```bash
pip install -r requirements.txt
```

## 📝 Note Tecniche

### 📖 RIASSUMI.PY

#### Chunking
- **Max size**: 12.000 caratteri per blocco
- **Overlap**: 600 caratteri tra blocchi
- **Divisione**: Cerca punti naturali (`.`, `\n`, spazio)

#### Limiti
- **Context window**: 128.000 token (configurabile in `call_ollama()`)
- **Temperature**: 0.3 (bilanciato tra creatività e coerenza)
- **Timeout**: 300 secondi per chiamata Ollama

#### Performance
- **EPUB medio** (10 capitoli): ~5-10 minuti con qwen3:8b
- **PDF lungo** (20+ sezioni): ~15-30 minuti
- **Dipende da**: CPU, RAM, modello scelto, lunghezza libro

### ⚡ RIASSUNTIVELOCI.PY

#### Chunking
- **Max size**: 32.000 caratteri per blocco (2.7x più grande di riassumi.py)
- **Overlap**: 0 (niente overlap, sampling discontinuo)
- **Strategia**: Campionamento intelligente invece di divisione continua
- **Retry**: Max 2 tentativi per gestire timeout occasionali

#### Limiti
- **Context window**: 32.000 token (ridotto per velocità)
- **Temperature**: 0.7 (alta per velocità)
- **Timeout**: 600 secondi (10 min) per chiamata - chunk enormi richiedono tempo
- **Max predict**: 500 token per risposta

#### Performance
- **EPUB medio** (10 capitoli): ~2-3 minuti con qwen3:8b
- **PDF lungo** (20+ sezioni): ~3-5 minuti
- **Guadagno**: 5-10x più veloce di riassumi.py
- **Trade-off**: Meno dettaglio, ma overview efficace

## 🔮 Sviluppi Futuri

### 📖 RIASSUMI.PY
- [ ] GUI con Tkinter
- [ ] Supporto altri formati (MOBI, AZW3, TXT)
- [ ] Cache riassunti parziali
- [ ] Configurazione prompt personalizzabili
- [ ] Supporto multi-lingua per output
- [ ] Esportazione in altri formati (HTML, LaTeX, PDF)

### ⚡ RIASSUNTIVELOCI.PY
- [ ] **Parallelizzazione**: Elaborare chunk contemporaneamente
- [ ] **Streaming**: Output progressivo durante elaborazione
- [ ] **Cache smart**: Riuso estratti già processati
- [ ] **Sampling configurabile**: Scegliere quanti chunk campionare
- [ ] **Modalità "flash"**: Solo inizio + fine (2 chunk, <1 minuto)
- [ ] **Batch processing**: Elaborare più libri in parallelo

### ✨ GENERALE
- [ ] Tool unificato con flag `--fast` / `--detailed`
- [ ] Confronto automatico qualità riassunti (veloce vs dettagliato)
- [ ] Supporto web UI per entrambe le modalità

## 📄 Licenza

Questo progetto è fornito "as-is" per uso personale ed educativo.

## 🤝 Contributi

Suggerimenti e miglioramenti sono benvenuti! Apri una issue o pull request.

---

**Sviluppato con ❤️ e Claude Code**
