# Mat Munshi

A digital archival ingestion, entity ledger, and knowledge synthesis pipeline designed to convert digitized historical publications from the Malaysian Branch of the Royal Asiatic Society (JSBRAS, JMBRAS, monographs, and reprints) into an interlinked, verifiable encyclopedia.

The system replaces conversational RAG with deterministic archival processing: layout-aware document extraction, permanent page-level HTML anchors (`<span id="page-N"></span>`), a canonical entity occurrence ledger, and an Open Knowledge Format (OKF v0.2) synthesis engine.

---

## Architecture Overview

Raw Archive PDFs
      │
      ▼
[apps/docproc] (MuPDF Layout + Qwen VL OCR + LLM Metadata)
      │
      ▼
Outputs: text_blocks.jsonl, documents.jsonl, footnotes.jsonl, figures.jsonl
      │
      ▼
[apps/stitcher] (Deterministic Markdown Compilation)
      │
      ├──▶ data/{doc_id}/{doc_id}.md (Source Markdown with  anchors)
      │
      ├─────────────────────────────────────────┐
      ▼                                         ▼
[zvec-grep (zg)] (Hybrid / Lexical Search)    [apps/ledger] (NER Sweep & Entity Resolution)
      │                                         │
      ▼                                         ▼
.zvec-grep/ Index Store                     ledger/entity_ledger.db (SQLite)
      │                                         │
      └───────────────────┬─────────────────────┘
                          ▼
                          [apps/synthesizer] (Dual Retrieval: Ledger + Semantic Context)
                          │
                          ▼
                          content/wiki/concepts/*.md (Open Knowledge Format)
                          │
                          ▼
                          Static Discovery & Public Web (Astro)

                          ---

## Monorepo Layout

The workspace is organized into modular Python packages and shared storage:

```text
munshi/
├── apps/
│   ├── docproc/          # PDF layout analysis, VLM OCR, and metadata enrichment
│   ├── stitcher/         # Compiles JSONL records into continuous Markdown with page anchors
│   ├── ledger/           # GLiNER entity extraction, alias resolution, and SQLite ledger
│   └── synthesizer/      # Dual-retrieval OKF article compiler and prompt templates
├── db/                   # Seed authority dictionaries and canonical indices
├── ledger/               # SQLite databases and persistent vector caches
│   ├── entity_ledger.db  # Canonical entities, occurrences, and alias mappings
│   └── authority_index.json # Parsed Index Malaysiana authority records
├── sources/                 # Extracted JSONL artifacts and stitched source Markdown
├── content/              # Synthesized output Wiki Markdown pages (OKF v0.2)
├── .env.example          # Environment variable template
└── pyproject.toml        # Root workspace configuration
```

---

## Core Apps & Packages

### 1. Document Processor (`apps/docproc`)
Handles primary ingestion of raw historical PDFs:
* **Layout Analysis & OCR**: Fast bounding box, text block, and footnote boundary detection via PyMuPDF, with difficult page OCR and figure transcription handled via vision models (e.g. Qwen2.5-VL / Qwen3-VL via OpenRouter).
* **Metadata & Classification**: Extracts bibliographic metadata (title, author, volume, year) and classifies publication types.
* **Outputs**: Emits structured JSONL bundles (`documents.jsonl`, `text_blocks.jsonl`, `footnotes.jsonl`, `figures.jsonl`, `plates.jsonl`).

### 2. Archival Stitcher (`apps/stitcher`)
Compiles structured JSONL bundles into continuous Markdown files:
* Embeds deterministic browser-native jump targets: `<span id="page-N"></span>`.
* Normalizes inline markdown footnotes (`[^N]`) and links them to page coordinates.
* Resolves image and plate placements directly into the reading flow.

### 3. Retrieval & Indexing (`zvec-grep`)
* Provides in-process vector and lexical indexing (`zg`) over stitched Markdown sources.
* Supports exact citation lookup (`--fts`) and hybrid semantic context retrieval (`--human`) with preserved line and page anchor positions.

### 4. Entity Ledger (`apps/ledger`)
Maintains an authoritative SQLite database of historical actors, places, and events:
* **Extraction Sweep**: Sliding-window NER passes over compiled Markdown to surface canonical entities and text context snippets.
* **Authority Resolution**: Normalizes variants and aliases against `Index Malaysiana` authority headwords.
* **Noise Mitigation**: Manages stopword patterns and suppression lists to keep synthesis candidate queues clean.

### 5. Wiki Synthesizer (`apps/synthesizer`)
Compiles comprehensive, fully grounded historical encyclopedia entries:
* **Dual Retrieval**: Simultaneously queries exact occurrence coordinates from SQLite and semantic context windows via `zvec-grep`.
* **Template Generation**: Routes evidence bundles through archetype-specific Jinja2 prompts (`person`, `place`, `event`, `concept`, `group`, `publication`).
* **Strict Evidence Grounding**: Enforces inline citations to exact document page coordinates: `([Source: doc_id, p. N](/sources/doc_id#page-N))`.

---

## Getting Started

### Prerequisites
* Python 3.11+
* [uv](https://github.com/astral-sh/uv) (recommended package and workspace manager)
* SQLite 3
* [zvec-grep (`zg`)](https://github.com/alibaba/zvec) CLI installed on PATH

### Configuration
Copy the example environment file to the repository root and configure your API keys:

```bash
cp .env.example .env```

Key environment variables:

OPENROUTER_API_KEY="sk-or-v1-..."
DOCPROC_LLM_PROVIDER="openrouter"
DOCPROC_OCR_MODEL="qwen/qwen-2.5-vl-72b-instruct"
DOCPROC_REASONING_MODEL="qwen/qwen-2.5-7b-instruct"
MUNSHI_SYNTHESIS_MODEL="google/gemini-2.5-flash"
DATA_DIR="data"
LEDGER_DB="ledger/entity_ledger.db"
AUTHORITY_INDEX="ledger/authority_index.json"
```

---

## Standard Workflow

### 1. Process Raw Archival Documents
Run ingestion over single documents or directory batches:

```bash
# Process a single scanned PDF
uv run --package munshi-docproc munshi-docproc process path/to/document.pdf --out-dir data

# Stitch JSONL artifacts into anchored Markdown
uv run --package munshi-stitcher python apps/stitcher/stitcher.py
```

### 2. Index Compiled Sources
Index the generated Markdown corpus for hybrid and lexical search:

```bash
cd data
zg index --embedding local/potion-retrieval-32m
cd ..
```

### 3. Extract Entities & Build the Ledger
Parse authority records and execute extraction sweeps across the corpus:

```bash
# Compile canonical authority index from parsed records
uv run --package munshi-ledger munshi-ledger build-authority

# Execute the entity extraction sweep
uv run --package munshi-ledger munshi-ledger sweep
```

### 4. Synthesize Wiki Articles
Compile cited Open Knowledge Format articles for target entities:

```bash
# Dry run: Inspect evidence aggregation and rendered prompt
uv run --package munshi-synthesizer munshi-synthesize synthesize "Frank Swettenham"

# Live execution: Synthesize article and commit to Wiki directory
uv run --package munshi-synthesizer munshi-synthesize synthesize "Frank Swettenham" --execute
```

---

## Output Standards

* **Source Markdown**: Preserved at `data/{doc_id}/{doc_id}.md` with YAML frontmatter, `<span id="page-N"></span>` markers before each page boundary, and resolved footnote definitions.
* **Synthesized Concept Pages**: Saved to `content/wiki/concepts/{slug}.md` adhering to OKF v0.2, containing entity metadata, thematic sections, inline citation anchors, and archival bibliographies.