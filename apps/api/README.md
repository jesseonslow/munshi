# Munshi API (`munshi-api`)

Unified control plane, janitorial mutation engine, and graph integrity reconciler for the **Mat Munshi** digital archival encyclopedia.

This service acts as the atomic mutation bridge for the monorepo, decoupling raw filesystem operations on `wiki/` and `sources/` from frontends (the Admin Dashboard) and autonomous maintenance bots.

---

## Capabilities

* **Atomic Multi-File Mutations (`/api/janitor/*`)**:
  * **Reassign Publication Authors**: Surgically shifts an article's authorship across the publication frontmatter, updates the source author's bibliography, populates the target author's bibliography, and rewrites the parent journal issue Table of Contents and contributor lists in a single atomic transaction.
  * **Auto-Fix Source Paths**: Updates invalid, fragmented, or mispointed `source_path` and `source_doc` declarations across article frontmatters.
  * **Merge Author Profiles**: Merges duplicate scholar profiles, preserving alias history and rewriting all inbound Markdown hyperlinks across the entire corpus.
* **Graph Health & Attribution Auditing (`/api/audit/*`)**:
  * **Cross-Entity Attribution Consistency**: Systematically verifies that articles claimed in an author's `## Bibliography` match the declared frontmatter authors in the publication stubs and the journal issue Tables of Contents (detecting discrepancies like `W. Cheah` vs. `Cheah Boon Kheng`).
  * **Corpus-Wide Source Path Auditing**: Scans all `type: article` entries to detect missing files, target fragments (`glossary.md`, `references.md`), and coordinate mismatches.
  * **Broken Link Detection**: Groups and ranks missing outbound relative Markdown links (`[Title](./target.md)`).
  * **Split Author Detection**: Identifies potential duplicate contributor profiles sharing identical surnames and initials.
* **Source Verification & Neural Arbitration (`/api/sources/*`)**:
  * Compares publication coordinates against physical start-page and volume coordinates scraped from source headers.
  * Integrates with Laya's non-autoregressive `noul` primitive to arbitrate ambiguous or mismatched source files without generative LLM overhead or hallucination.

---

## Directory Layout

```
apps/api/
├── pyproject.toml
├── README.md
└── src/
    └── munshi_api/
        ├── __init__.py
        ├── config.py             # Root path resolution & environment settings
        ├── app.py                # FastAPI entrypoint & router composition
        ├── cli.py                # Terminal runner for local administrative jobs
        ├── models/               # Pydantic request/response contracts
        │   ├── __init__.py
        │   ├── audit.py
        │   ├── janitor.py
        │   └── sources.py
        ├── routers/              # HTTP Route Controllers
        │   ├── __init__.py
        │   ├── audit.py
        │   ├── janitor.py
        │   └── sources.py
        └── services/             # Pure Python domain engines
            ├── __init__.py
            ├── graph_auditor.py
            ├── janitor_engine.py
            └── source_matcher.py

```

---

## Configuration

Settings are loaded automatically from the repository root `.env` file via `ApiConfig`:

```
WIKI_DIR="wiki"
SOURCES_DIR="sources"
DB_DIR="db"
LEDGER_DB="db/entity_ledger.db"
SEED_DB="db/seed_dictionary.db"

```

---

## Running the Service

### 1. Installation

From the monorepo root:

```
uv sync

```

Or install in editable mode:

```
uv pip install -e apps/api

```

### 2. Start the HTTP Server

```
uv run uvicorn munshi_api.app:app --reload --port 8000

```

Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

### 3. CLI Commands

Run graph integrity and source alignment audits directly from your terminal:

```
# Run general graph health check (broken links & split authors)
uv run munshi-api audit

# Audit cross-entity author attribution mismatches
uv run munshi-api audit-attributions

# Audit source_path integrity across all articles
uv run munshi-api audit-sources

```

---

## API Endpoints

### Janitor Operations (`/api/janitor`)

* `POST /api/janitor/reassign-author`: Atomically reassigns an article to a different author and updates all referencing issue TOCs and bibliography lists.
* `POST /api/janitor/fix-source-path`: Updates `source_path` and `source_doc` in an article's frontmatter.
* `POST /api/janitor/merge-authors`: Merges a duplicate author profile into a canonical profile and rewrites all inbound links.



### Source Operations (`/api/sources`)

* `GET /api/sources/validate/{slug}`: Evaluates whether a wiki stub links to the authentic primary source markdown file via physical coordinates and Laya neural verification.

### Graph Audits (`/api/audit`)

* `GET /api/audit/health`: Returns overall graph statistics, broken links, and potential split author clusters.
* `GET /api/audit/attributions`: Scans for conflicts where author bibliographies, publication frontmatters, and issue TOCs disagree.
* `GET /api/audit/sources`: Returns all articles with missing, fragmented, or misaligned source paths.
* `GET /api/ping`: Service liveness check.