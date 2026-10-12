# Munshi

A digital archival ingestion, entity ledger, and knowledge synthesis pipeline designed to convert ~150 years of digitized historical publications from the Malaysian Branch of the Royal Asiatic Society (JSBRAS, JMBRAS, monographs, and reprints) into a permanent, interlinked, verifiable encyclopedia.

Rather than relying on conversational runtime RAG or unpredictable vector similarity, Munshi implements a file-first compile-time architecture: layout-aware document extraction, deterministic page-level HTML anchors (`<span id="page-N"></span>`), a top-down authority taxonomy (Index Malaysiana), an autonomous policy-driven bot engine, and an Open Knowledge Format (OKF v0.2) synthesis pipeline.

---

## Architecture Overview

```
                        Raw Archival PDFs / Scans
                                  │
                                  ▼
         ┌──────────────────────────────────────────────────┐
         │ 1. apps/docproc (PyMuPDF Layout & VLM Extraction)│
         └────────────────────────┬─────────────────────────┘
                                  │ JSONL Records (text_blocks, docs, figures)
                                  ▼
         ┌──────────────────────────────────────────────────┐
         │ 2. apps/stitcher (Source Reassembly)             │
         └────────────────────────┬─────────────────────────┘
                                  │ Stitched Sources with <span id="page-N"></span>
                                  ▼
                            sources/*.md
                                  │
            ┌─────────────────────┴───────────────────────┐
            │                                             │
            ▼                                             ▼
┌───────────────────────┐                     ┌───────────────────────┐
│ apps/summarizer       │                     │ db/ (Authority Spine) │
│ Single-publication    │                     │ seed_dictionary.db    │
│ lede & contextualizer │                     │ authority_index.json  │
└───────────┬───────────┘                     └───────────┬───────────┘
            │                                             │
            ▼                                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. wiki/*.md (Canonical Knowledge Base - Flat Namespace)            │
│    Publications, Persons, Concepts, Places, Events, Issues          │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
       ┌────────────────────┼────────────────────┐
       ▼                    ▼                    ▼
┌──────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ apps/bots    │   │ apps/synthesizer│   │ apps/api & admin│
│ Autonomous   │   │ OKF Topic &     │   │ FastAPI control │
│ Policy Bots  │   │ Entity Synthesis│   │ plane & Streamlit│
│ (Gibson, etc)│   │ (Jinja2 Models) │   │ ops cockpit     │
└──────────────┘   └─────────────────┘   └─────────────────┘
```

## Monorepo Layout

The repository is managed via a root `uv` workspace coordinating specialized applications under `apps/`:

```
munshi/
├── pyproject.toml              # Root uv workspace definition
├── uv.lock                     # Monorepo lockfile
├── .env.example                # Shared environment configuration template
│
├── apps/
│   ├── admin/                  # Streamlit operational cockpit & pipeline inspector
│   ├── api/                    # FastAPI control plane, janitor mutations, & audit router
│   ├── bots/                   # Autonomous policy-driven agent runner (runner/engine/providers)
│   ├── docproc/                # PDF layout analysis, OCR, and VLM extraction pipeline
│   ├── ledger/                 # Authority indexer, SQLite ledger builder, & resolution
│   ├── stitcher/               # Deterministic JSONL-to-Markdown source compiler
│   ├── summarizer/             # Single-document historiographical summarization engine
│   └── synthesizer/            # Multi-document OKF encyclopedia synthesis pipeline
│
├── db/                         # Authority definitions, dictionaries, and index stores
│   ├── seed_dictionary.db      # Master Index Malaysiana taxonomic database
│   ├── authority_index.json    # Compiled authority records
│   └── entity_ledger.db        # Entity occurrences and verified citation ledger
│
├── sources/                    # Stitched primary source Markdown files with <span id="page-N">
├── wiki/                       # Canonical flat encyclopedia Markdown files (OKF v0.2)
└── utils/                      # Low-level maintenance scripts (heading repair, wikification)
```

---

## Core Apps & Packages

### 1. Document Processor (`apps/docproc`)
Handles primary ingestion of raw historical PDFs:
* **Layout Analysis**: Native bounding box detection, text block segmentation, and footnote boundary isolation via PyMuPDF.
* **VLM Transcription**: Difficult pages, degraded typography, and plates are routed to vision models (e.g., Qwen-VL / Flash models via OpenRouter).
* **Outputs**: Emits structured JSONL bundles (`documents.jsonl`, `text_blocks.jsonl`, `footnotes.jsonl`, `figures.jsonl`, `plates.jsonl`).

### 2. Archival Stitcher (`apps/stitcher`)
Compiles structured JSONL bundles into continuous Markdown files:
* Embeds deterministic browser-native jump targets: `<span id="page-N"></span>`.
* Normalizes inline markdown footnotes (`[^N]`) and links them to page coordinates.
* Resolves image and plate placements directly into the reading flow.

### 3. Publication Summarizer (`apps/summarizer`)
Ingests primary sources from `sources/` and populates publication stubs in wiki/:
* Produces two-tier analytical overviews: introductory lede paragraphs, deep summaries (findings and conclusions), and historiographical context blocks.
* Emits grounded page citations linking back to source anchors: `([p. X](/sources/{doc_id}#page-X))`.
* Automatically parses frontmatter abstracts and keywords directly from source files without token waste.

### 4. Wiki Synthesizer (`apps/synthesizer`)
Compiles multi-source, comprehensive entries across topics, actors, and events:
* **Evidence Gathering**: Aggregates verified citations, occurrence snippets, and pre-computed summaries across the corpus.
* **Jinja2 Archetype Templates**: Renders domain-specific prompt layouts (`person`, `place`, `event`, `concept`, `group`).
* **MBRAS Style Compliance**: Enforces British English orthography, Oxford comma usage, and translation of non-English terms on first mention while avoiding colonial pejoratives.

### 5. Autonomous Maintenance Bots (`apps/bots`)
Declarative, policy-driven agents that crawl wiki/*.md and apply structured modifications:
* **Runner & Engine**: A unified async runner (`munshi_bots.runner`) evaluates target pages against declarative Markdown policies (`policies/*.md`).
* **Candidate Providers**: Pluggable providers (`SourceCandidateProvider`, `SurfaceMentionCandidateProvider`) supply contextual candidates without running heavy shell commands.
* **Safe Mutations**: LLMs output structured JSON patches; pure Python mutators apply atomic YAML frontmatter and prose hyperlink edits.

---

## Getting Started

### Prerequisites
* Python 3.11+
* [uv](https://github.com/astral-sh/uv) (recommended package and workspace manager)
* OpenRouter API key

### Configuration
Copy the example environment file to the repository root and configure your API keys:

```bash
cp .env.example .env
```

### Installation
Sync all workspace packages and dependencies in editable mode:

```bash
uv sync
```

---

## Common Workflow

### Processing Sources & Summaries
Run ingestion over single documents or directory batches:

```bash
# Process a PDF scan
uv run --package munshi-docproc munshi-docproc process /path/to/scan.pdf --out-dir data

# Stitch JSONL artifacts into anchored source Markdown
uv run --package munshi-stitcher python apps/stitcher/stitcher.py

# Summarize a target publication into wiki/
uv run --package munshi-summarizer munshi-summarize --target supplying-coal-and-piracy --execute
```

### Topic Synthesis

```bash
# Synthesize an individual topic entry
uv run --package munshi-synthesizer munshi-synthesizer synthesize "Tin Mining" --execute

# Batch-synthesize pending topic candidates
uv run --package munshi-synthesizer munshi-synthesizer batch --execute
```

### 3. Extract Entities & Build the Ledger
Parse authority records and execute extraction sweeps across the corpus:

```bash
# Compile canonical authority index from parsed records
uv run --package munshi-ledger munshi-ledger build-authority

# Execute the entity extraction sweep
uv run --package munshi-ledger munshi-ledger sweep
```

### Running Wiki Maintenance Bots

```bash
# Execute a declarative bot policy (e.g., Gibson bot for source-stub verification)
uv run --package munshi-bots python -m munshi_bots.runner gibson

# Dry-run a policy with candidate debugging
uv run --package munshi-bots python -m munshi_bots.runner ridley --dry-run
```