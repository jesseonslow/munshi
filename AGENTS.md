# AGENTS.md — Contributor & AI Agent Operating Guidelines

This document provides operational instructions, architectural rules, code conventions, and safety guardrails for AI coding assistants and autonomous agents working in the **Mat Munshi** monorepo.

---

## 1. Project Mission & Identity

**Mat Munshi** is an archival digital ingestion, entity ledger, and knowledge synthesis system built for the digitized historical publications of the Malaysian Branch of the Royal Asiatic Society (**MBRAS**: *JSBRAS*, *JMBRAS*, monographs, reprints, and colonial records).

### The Primary Objective
Transform primary archival PDF sources into:
1. **Continuous, browser-navigable primary Markdown** with permanent `<span id="page-N"></span>` page-break anchors.
2. **A canonical entity ledger (`entity_ledger.db`)** tracking every historical actor, place, event, and concept to exact physical page numbers.
3. **An Open Knowledge Format (OKF v0.2) historical encyclopedia** (`/content/wiki/concepts/`) with zero-hallucination, verifiable citations.

### Golden Rules for Any Code Modification
1. **Never Reintroduce Conversational RAG into Core Pipelines**: Ingestion (`docproc`), stitching (`stitcher`), and entity mapping (`ledger`) must remain decoupled, batch-oriented pipelines.
2. **Deterministic Source Attribution**: Never permit models or scripts to synthesize citations out of memory. Every factual claim must link to a confirmed document and physical page number: `([Author (Year), p. N](/sources/doc_id#page-N))`.
3. **No Phantom Pages**: If an excerpt lacks a verifiable page number (`page_num_1`), the citation generator must link to the document top or omit the specific page anchor rather than guessing.

---

## 2. Monorepo Architecture & Package Boundaries

```text
munshi/
├── apps/
│   ├── docproc/          # Python: MuPDF layout analysis, VLM OCR, metadata extraction
│   ├── stitcher/         # Python: Zero-inference JSONL -> Markdown compiler
│   ├── ledger/           # Python: GLiNER/NER extraction, alias resolver, SQLite ledger
│   └── synthesizer/      # Python: Dual-retrieval OKF article compiler & Jinja2 templates
├── db/                   # Seed authority definitions (seed_dictionary.py)
├── ledger/               # Shared runtime databases & indexes
│   ├── entity_ledger.db  # SQLite database of entities, aliases, and occurrences
│   └── authority_index.json # Compiled Index Malaysiana authority records
├── data/                 # Intermediate JSONL outputs and stitched .md corpus
├── content/              # Final synthesized OKF Markdown articles (/content/wiki/)
├── .env.example          # Environment variable template
└── pyproject.toml        # Root workspace configuration
```

### Dependency & Execution Rules
* **Package Management**: Use [`uv`](https://github.com/astral-sh/uv) exclusively. Never run raw `pip install` without `uv`.
* **Sub-package Scoping**: When executing commands or tests from the root, always scope to the target package:
  ```bash
  uv run --package munshi-docproc <command>
  uv run --package munshi-ledger <command>
  uv run --package munshi-synthesizer <command>
  ```
* **No Direct Cross-App Python Imports**: Apps in `apps/` must not import directly from sibling app packages (e.g., `munshi_docproc` cannot import from `munshi_synthesizer`). Shared contracts belong in standardized schemas, SQLite (`entity_ledger.db`), or root `ledger/` JSON artifacts.

---

## 3. Subsystem Guidelines

### 3.1 Document Processor (`apps/docproc`)
* **Mandate**: Ingest raw PDFs and produce clean, layout-aware JSONL bundles (`documents.jsonl`, `text_blocks.jsonl`, `footnotes.jsonl`, `figures.jsonl`).
* **Dual-Engine Rule**:
  * Use **PyMuPDF** (`fitz`) for fast, local layout detection, text bounding boxes, and reading-order reconstruction.
  * Route difficult OCR, historical non-Latin scripts, and complex layouts to OpenRouter vision models (e.g., `qwen/qwen-2.5-vl-72b-instruct`).
* **Metadata & Classification**:
  * Metadata extraction (`enrich_metadata_llm.py`) and document classification (`classify_doctype.py`) use lightweight reasoning models (e.g., `qwen/qwen-2.5-7b-instruct`).
  * Never introduce conversational prompts here; output must strictly conform to Pydantic JSON schemas.

### 3.2 Archival Stitcher (`apps/stitcher`)
* **Mandate**: Deterministic Python compilation of JSONL records into unbroken, readable Markdown files (`/data/{doc_id}/{doc_id}.md`).
* **Zero Inference Cost ($0.00)**: Must run on local CPU in milliseconds without making LLM calls.
* **Anchor Tag Standard**: Every page boundary MUST be prefixed with an invisible HTML anchor:
  ```html
  <span id="page-45"></span>
  ```
* **Footnote Normalization**: Raw footnote tokens like `[ref:12]` must be resolved to standard Markdown footnotes (`[^1]`) with consolidated definitions at the bottom of the document.

### 3.3 Entity Ledger (`apps/ledger`)
* **Mandate**: Maintain `ledger/entity_ledger.db` as the single source of truth for historical actors, toponyms, events, and subjects.
* **Authority Compilation**:
  * `authority_builder.py` compiles `db/seed_dictionary.py` into `ledger/authority_index.json`.
  * Support facets (`Parent: Subtopic`), clusters, redirects, and variant aliases.
* **Extraction & Resolution Pipeline**:
  * Run sliding-window NER passes (10–15 pages, ~4,000 tokens) across source Markdown.
  * Resolution hierarchy:
    1. **Exact match**: Direct hit on canonical names or pre-mapped aliases.
    2. **Levenshtein / Token-sort**: Disambiguate initials and colonial title additions (e.g., `"Swettenham, F. A."` $\rightarrow$ `"Frank Swettenham"`).
    3. **Vector fallback**: Query `zvec-grep` (`zg`) for contextual semantic disambiguation.
* **Noise Filtering**: Apply frequency thresholding and check `ignored_entities` before queueing entities for synthesis.

### 3.4 Wiki Synthesizer (`apps/synthesizer`)
* **Mandate**: Assemble multi-source Open Knowledge Format (OKF v0.2) encyclopedia articles.
* **Dual Retrieval Strategy**:
  1. Retrieve verified physical occurrences (`doc_id`, `page_num`, `context_snippet`) from `entity_ledger.db`.
  2. Retrieve thematic semantic context from `zvec-grep` (`zg query --human`).
  3. Merge, deduplicate, and pass the verified excerpts into the Jinja2 template.
* **Template Specialization**:
  * Do not use generic, one-size-fits-all prompts.
  * Route requests to specific Jinja2 templates:
    * `person.jinja2`: Early life, colonial/court postings, conflicts, and relationships.
    * `place.jinja2`: Geography, archaeological evidence, administrative transitions.
    * `event.jinja2`: Chronology, causes, combatants, aftermath, historiographical disputes.
    * `concept.jinja2`: Cultural, legal (*adat*), and economic definitions.
    * `group.jinja2`: Ethnic communities, administrative bodies, or merchant syndicates.
* **Mechanical Citation Injection**:
  * Prompt outputs citation tokens: `[REF-N]`.
  * Post-processor deterministically converts `[REF-N]` into verified Markdown anchor links:
    `[Author (Year), p. 24](/sources/doc_id#page-24)`.

---

## 4. Code Style & Technical Standards

### Python Standards
* **Python Version**: 3.11+ (enforced across all `pyproject.toml` files).
* **Typing**: Strict type annotations on all function signatures. Use `from __future__ import annotations`.
* **Validation**: Use **Pydantic v2** (`BaseModel`, `Field`, `BaseSettings`) for all data schemas and environment configs.
* **Formatting & Linting**: Format and lint with `ruff`:
  ```bash
  uv run ruff format .
  uv run ruff check . --fix
  ```

### Database Practices (SQLite)
* Use parameterized SQL queries (`?`) for all SQLite transactions to prevent injection.
* Always handle database paths dynamically using `Path` from `config.py`.
* Ensure connection pooling or proper context-manager disposal (`with sqlite3.connect(...) as conn:`) to avoid locked database files.

---

## 5. Testing & Verification

Before committing changes, agents must run the relevant test suites:

```bash
# Run docproc tests
uv run --package munshi-docproc pytest apps/docproc/tests -v

# Run ledger tests
uv run --package munshi-ledger pytest apps/ledger/tests -v

# Run synthesizer tests
uv run --package munshi-synthesizer pytest apps/synthesizer/tests -v
```

### Spot-Checking & Integrity Linting
When generating or modifying synthesis logic, verify:
* **No Broken Anchors**: Every link to `/sources/{doc_id}#page-{N}` must have a matching file in `data/{doc_id}/{doc_id}.md` with `<span id="page-{N}"></span>`.
* **No Unsubstituted Tokens**: The output must not contain orphaned `[REF-`, `[TODO]`, or generic AI conversational preamble (*"Here is an overview..."*).