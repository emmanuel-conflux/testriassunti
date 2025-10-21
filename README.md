# 📚 Riassumi Libri - CLI Tool via Ollama

Tool CLI in Python per generare riassunti di libri (EPUB/PDF) utilizzando Ollama locale.

## ⚡ Due Modalità Disponibili

### 📖 riassumi.py - Modalità Dettagliata
Analisi completa capitolo per capitolo con riassunti approfonditi.
- Riassunti dettagliati (400-900 parole per capitolo)
- Output DOCX + Markdown con formattazione professionale
- Sistema checkpoint/resume per riprendere lavori interrotti
- MAP-REDUCE completo per gestione testi lunghi
- ⏱️ **Tempo**: ~10-30 minuti per libro medio

### ⚡ riassuntiveloci.py - Modalità Configurabile
Approccio flessibile con sampling configurabile da veloce a completo.
- **Sampling configurabile**: dal 30% al 100% del testo
- Riassunti concisi (300 parole per estratto, 500 per globale)
- Output Markdown minimalista
- Niente overhead: esecuzione diretta senza checkpoint
- ⚡ **Tempo**: ~2-30 minuti (dipende dal sampling)

**Quale scegliere?**
- 📖 Usa `riassumi.py` per analisi approfondite, documenti di studio, quando hai tempo
- ⚡ Usa `riassuntiveloci.py --sampling-ratio 0.3` per overview rapide (30% del testo)
- ⚡ Usa `riassuntiveloci.py --sampling-ratio 1.0` per lettura completa veloce (100% del testo)

---

## 🎯 Caratteristiche Principali

### Comuni a Entrambe le Modalità
- **Analisi locale**: Tutto funziona offline tramite Ollama
- **Supporto formati**: EPUB e PDF
- **Multilingua**: Output sempre in italiano, anche per libri in altre lingue
- **Progress tracking**: Barra di progresso e logging dettagliato
- **Configurabile**: Parametri CLI personalizzabili

### Specifiche di riassumi.py
- Analisi capitolo per capitolo con MAP-REDUCE
- Output Word (.docx) e Markdown (.md)
- Sistema checkpoint/resume intelligente
- Modalità interattiva guidata

### Specifiche di riassuntiveloci.py
- Sampling configurabile (30%-100% del testo)
- Sampling strategico: inizio, medio, fine
- Chunk enormi (32k caratteri) per meno chiamate a Ollama
- Solo output Markdown

---

## 🔧 Requisiti

### Sistema
- **Python**: 3.11 o superiore
- **RAM**: Minimo 8 GB (consigliato 16+ GB per modelli grandi)
- **Ollama**: Installato e in esecuzione

### Installazione Ollama

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

### Python e Dipendenze

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

---

## 📁 Struttura Directory

```
~/
├── dariassumere/           # Input: file EPUB/PDF
│   ├── libro1.epub
│   ├── libro2.pdf
│   └── ...
│
└── riassunti/              # Output: riassunti generati
    ├── libro1.riassunto.docx      # Output riassumi.py
    ├── libro1.riassunto.md        # Output riassumi.py
    ├── libro1.veloce.md           # Output riassuntiveloci.py
    └── ...
```

---

## 🚀 Utilizzo

### ⚡ riassuntiveloci.py - Modalità Configurabile

#### Sintassi
```bash
python riassuntiveloci.py [opzioni]

Opzioni:
  --model MODEL            Modello Ollama (default: qwen3:8b)
  --input_dir DIR          Directory input (default: ~/dariassumere)
  --output_dir DIR         Directory output (default: ~/riassunti)
  --sampling-ratio RATIO   Percentuale di testo da processare (0.0-1.0, default: 1.0)
  -h, --help               Mostra questo messaggio
```

#### Esempi
```bash
# Lettura completa (100% del testo, più lento ma completo)
python riassuntiveloci.py --sampling-ratio 1.0

# Bilanciato (60% del testo)
python riassuntiveloci.py --sampling-ratio 0.6

# Veloce (30% del testo, solo overview)
python riassuntiveloci.py --sampling-ratio 0.3

# Con modello personalizzato
python riassuntiveloci.py --model llama3:8b --sampling-ratio 0.5

# Directory personalizzate
python riassuntiveloci.py --input_dir /path/to/books --output_dir /path/to/output
```

#### Come Funziona il Sampling

**Con --sampling-ratio 1.0 (100%):**
- Legge e processa **tutto** il testo del libro
- Divide in chunk da 32k caratteri
- Processa ogni singolo chunk
- Risultato: completo ma più lento

**Con --sampling-ratio 0.3 (30%):**
- Legge tutto il testo ma **campiona** solo il 30%
- Sampling strategico: INIZIO + chunk distribuiti uniformemente + FINE
- Processa solo i chunk campionati
- Risultato: overview rapida ma efficace

---

### 📖 riassumi.py - Modalità Dettagliata

#### Sintassi
```bash
python riassumi.py [opzioni]

Opzioni:
  -i, --interactive      Avvia modalità interattiva guidata
  --model MODEL          Modello Ollama (default: qwen3:8b)
  --input_dir DIR        Directory input (default: ~/dariassumere)
  --output_dir DIR       Directory output (default: ~/riassunti)
  --min_words NUM        Parole minime per capitolo (default: 300)
  --chunk_size NUM       Dimensione chunk in caratteri (default: 12000)
  --language LANG        Lingua output (default: it)
  -h, --help             Mostra questo messaggio
```

#### Esempi
```bash
# Esecuzione base (ti chiede se vuoi modalità interattiva)
python riassumi.py

# Modalità interattiva esplicita
python riassumi.py --interactive

# Modello diverso
python riassumi.py --model llama3:70b

# Capitoli più lunghi
python riassumi.py --min_words 500

# Configurazione completa
python riassumi.py --model qwen3:30b --input_dir /path/to/books --min_words 400
```

#### Sistema Checkpoint/Resume

Il programma salva automaticamente il progresso dopo ogni capitolo:
- **Ripresa intelligente**: Se interrompi (Ctrl+C, crash), al prossimo avvio puoi riprendere
- **Validazione parametri**: Riprende solo se modello e parametri sono identici
- **Pulizia automatica**: Checkpoint rimosso al completamento

---

## 📖 Come Funziona

### riassuntiveloci.py

1. **Estrazione rapida**: Legge tutto il testo in un colpo solo
2. **Divisione in chunk**: Divide il testo in blocchi da 32k caratteri
3. **Sampling configurabile**:
   - Se `--sampling-ratio 1.0`: processa tutti i chunk
   - Se `--sampling-ratio < 1.0`: campiona strategicamente (inizio, medio, fine)
4. **Riassunto chunk**: Riassume ogni chunk selezionato (max 300 parole)
5. **Riassunto globale**: Combina i riassunti parziali (max 500 parole)
6. **Output Markdown**: Salva in `.veloce.md`

**Ottimizzazioni velocità:**
- Chunk enormi (32k vs 12k) = meno chiamate a Ollama
- Prompt concisi = risposte più rapide
- Temperature alta (0.7) = meno "thinking"
- Context window ridotto (32k vs 128k)
- Retry limitato (max 2 tentativi)
- Timeout 10 minuti per chunk (necessario per chunk grandi)

### riassumi.py

1. **Estrazione capitoli**:
   - EPUB: Usa lo spine, estrae titoli da `<h1>`, `<h2>`, `<h3>`
   - PDF: Cerca pattern "Capitolo X" o divide in sezioni ~3000 parole
2. **Chunking MAP-REDUCE**: Per capitoli >12k caratteri:
   - MAP: Divide in blocchi con overlap 600 caratteri
   - REDUCE: Riassume ogni blocco
   - MERGE: Unisce i riassunti parziali
3. **Riassunto capitoli**: Riassume ogni capitolo (400-900 parole)
4. **Sintesi globale**: Riassunto complessivo del libro
5. **Output multipli**: Genera DOCX e Markdown con formattazione professionale

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

### Gestione Modelli
```bash
# Scarica modello
ollama pull qwen3:8b

# Lista modelli installati
ollama list

# Rimuovi modello
ollama rm nome_modello
```

---

## 🐛 Troubleshooting

### Ollama non raggiungibile
```
❌ Errore connessione Ollama: ...
```
**Soluzione**: Verifica che Ollama sia in esecuzione:
```bash
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

### Nessun capitolo estratto (riassumi.py)
```
❌ Nessun capitolo estratto
```
**Soluzione**:
1. Verifica che il file non sia corrotto
2. Riduci `--min_words` (es. `--min_words 100`)
3. Prova con un altro file

### Dipendenze mancanti
```
⚠️ ebooklib o BeautifulSoup non disponibili
```
**Soluzione**:
```bash
pip install -r requirements.txt
```

---

## 📝 Note Tecniche

### riassuntiveloci.py
- **Chunk size**: 32.000 caratteri
- **Overlap**: 0 (sampling discontinuo)
- **Context window**: 32.000 token
- **Temperature**: 0.7
- **Timeout**: 600 secondi (10 minuti)
- **Max predict**: 500 token
- **Performance**:
  - Con `--sampling-ratio 0.3`: ~2-5 minuti
  - Con `--sampling-ratio 1.0`: ~10-30 minuti (dipende dalla lunghezza)

### riassumi.py
- **Chunk size**: 12.000 caratteri (default)
- **Overlap**: 600 caratteri
- **Context window**: 128.000 token
- **Temperature**: 0.3
- **Timeout**: 300 secondi (5 minuti)
- **Performance**: ~10-30 minuti per libro medio

---

## 🔮 Sviluppi Futuri

### riassuntiveloci.py
- [ ] Parallelizzazione: Elaborare chunk contemporaneamente
- [ ] Streaming: Output progressivo durante elaborazione
- [ ] Cache smart: Riuso estratti già processati
- [ ] Modalità "flash": Solo inizio + fine (<1 minuto)

### riassumi.py
- [ ] GUI con Tkinter
- [ ] Supporto altri formati (MOBI, AZW3, TXT)
- [ ] Cache riassunti parziali
- [ ] Prompt personalizzabili

### Generale
- [ ] Tool unificato con flag `--fast` / `--detailed`
- [ ] Web UI per entrambe le modalità
- [ ] Supporto multi-lingua per output

---

## 📄 Licenza

Questo progetto è fornito "as-is" per uso personale ed educativo.

## 🤝 Contributi

Suggerimenti e miglioramenti sono benvenuti! Apri una issue o pull request.

---

**Sviluppato con ❤️ e Claude Code**
