# 📚 Riassumi Libri - CLI Tool via Ollama

Tool CLI in Python per generare riassunti dettagliati di libri (EPUB/PDF) utilizzando Ollama locale.

## 🎯 Caratteristiche

- **Analisi locale**: Tutto funziona offline tramite Ollama
- **Supporto formati**: EPUB e PDF
- **Riassunti dettagliati**: Capitolo per capitolo con sintesi globale
- **Output multipli**: File Word (.docx) e Markdown (.md)
- **MAP-REDUCE**: Gestione intelligente di testi lunghi
- **Multilingua**: Output sempre in italiano, anche per libri in altre lingue
- **Progress tracking**: Barra di progresso e logging dettagliato
- **Configurabile**: Parametri CLI personalizzabili

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
    ├── libro2.riassunto.docx
    └── libro2.riassunto.md
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

### Parametri Configurabili

```bash
python riassumi_libri.py [opzioni]

Opzioni:
  --model MODEL          Modello Ollama (default: qwen3:8b)
  --input_dir DIR        Directory input (default: C:\dariassumere)
  --output_dir DIR       Directory output (default: C:\riassunti)
  --min_words NUM        Parole minime per capitolo (default: 300)
  --language LANG        Lingua output (default: it)
  -h, --help            Mostra questo messaggio
```

### Esempi

#### Usare un modello diverso
```bash
python riassumi_libri.py --model llama3:70b
```

#### Directory personalizzate
```bash
python riassumi_libri.py --input_dir /path/to/books --output_dir /path/to/output
```

#### Capitoli più lunghi
```bash
python riassumi_libri.py --min_words 500
```

#### Configurazione completa
```bash
python riassumi_libri.py \
  --model qwen3:30b \
  --input_dir "D:\Libri" \
  --output_dir "D:\Riassunti" \
  --min_words 400
```

## 📖 Come Funziona

### 1. Estrazione Capitoli

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

### 5. Gestione Errori

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

### Chunking
- **Max size**: 12.000 caratteri per blocco
- **Overlap**: 600 caratteri tra blocchi
- **Divisione**: Cerca punti naturali (`.`, `\n`, spazio)

### Limiti
- **Context window**: 128.000 token (configurabile in `call_ollama()`)
- **Temperature**: 0.3 (bilanciato tra creatività e coerenza)
- **Timeout**: 300 secondi per chiamata Ollama

### Performance
- **EPUB medio** (10 capitoli): ~5-10 minuti con qwen3:8b
- **PDF lungo** (20+ sezioni): ~15-30 minuti
- **Dipende da**: CPU, RAM, modello scelto, lunghezza libro

## 🔮 Sviluppi Futuri

- [ ] GUI con Tkinter
- [ ] Supporto altri formati (MOBI, AZW3, TXT)
- [ ] Cache riassunti parziali
- [ ] Elaborazione parallela di più libri
- [ ] Esportazione in altri formati (HTML, LaTeX)
- [ ] Configurazione prompt personalizzabili
- [ ] Supporto multi-lingua per output

## 📄 Licenza

Questo progetto è fornito "as-is" per uso personale ed educativo.

## 🤝 Contributi

Suggerimenti e miglioramenti sono benvenuti! Apri una issue o pull request.

---

**Sviluppato con ❤️ e Claude Code**
