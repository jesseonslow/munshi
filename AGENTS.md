# AGENTS.md — Contributor & AI Agent Operating Guidelines

his document defines operational rules, architectural constraints, and code conventions for human developers and autonomous AI assistants working within the **Munshi** codebase.

---

## 1. Project Mission & Identity

**Munshi** is an archival digital ingestion, entity ledger, and encyclopedia synthesis platform for the historical collection of the Malaysian Branch of the Royal Asiatic Society (MBRAS: JSBRAS, JMBRAS, monographs, and reprints).

The goal is an authoritative, verifiable, interlinked reference catalog. Claims, biographies, and analyses must be strictly grounded in primary sources via immutable page anchors `(<span id="page-N"></span>)`.

---

## 2. Monorepo Architecture & Package Boundaries

```
munshi/
├── apps/
│   ├── admin/          # Streamlit UI cockpit (munshi-admin)
│   ├── api/            # FastAPI control plane & janitor (munshi-api)
│   ├── bots/           # Policy-driven wiki maintenance engine (munshi-bots)
│   ├── docproc/        # Layout analysis & VLM extraction (munshi-docproc)
│   ├── ledger/         # SQLite occurrence ledger & authority builder (munshi-ledger)
│   ├── stitcher/       # JSONL -> Markdown compiler (munshi-stitcher)
│   ├── summarizer/     # Publication summarizer (munshi-summarizer)
│   └── synthesizer/    # OKF encyclopedia entry compiler (munshi-synthesizer)
├── db/                 # seed_dictionary.db, entity_ledger.db, authority_index.json
├── sources/            # Stitched archival primary sources (*.md)
├── wiki/               # Flat namespace of encyclopedia entries (*.md)
├── utils/              # Maintenance and repair utilities
├── pyproject.toml      # Root uv workspace configuration
└── uv.lock             # Monorepo lockfile
```

### Dependency & Execution Rules
* **`uv` Workspace Only**: Never use bare pip install. All dependency additions must go through `uv add --package <package-name>`.
* **Scoped Execution**: Execute tools from the root using `--package`:
  ```bash
  uv run --package munshi-api <cmd>
  uv run --package munshi-bots <cmd>
  uv run --package munshi-synthesizer <cmd>
  ```
* **No Direct Cross-App Python Imports**: Apps in `apps/` must not import directly from sibling app packages. Sibling sharing must occur via:
  1. Root workspace package declarations in `pyproject.toml` (e.g., `munshi-summarizer = { workspace = true }`).
  2. Standardized disk contracts (YAML frontmatter in `wiki/`, `<span id="page-N">` in `sources/`, or SQLite in `db/`).
* **Package Namespaces**: Python package directories under `src/` must use underscores (`munshi_bots`, `munshi_api`, `munshi_synthesizer`), never hyphens.

---

## 3. Data & Storage Contracts

### The Flat-File Canonical Database

* The Markdown files in `wiki/*.md` and `sources/*.md` represent the canonical ground truth.
* Databases in `db/` (`entity_ledger.db`, `seed_dictionary.db`) act as lookup indices, whitelists, and occurrence ledgers.
* Any changes to relations, bibliographies, or metadata must be applied directly to the Markdown files. Do not treat SQLite as an isolated source of truth.

### Primary Source Page Anchors

* Stitched primary sources in `sources/*.md` must preserve deterministic page boundaries:
    ```HTML
    <span id="page-24"></span>
    ```
* Citations generated in `wiki/` articles must link directly to these anchors:
    ```Markdown
    ([p. 24](/sources/doc_id#page-24))
    ```

### Canonical Frontmatter Specifications (wiki/*.md)

#### Publications (type: publication)

```YAML
---
id: string
work_id: string                 # e.g., "jmbras-98-1-p23"
title: string
canonical_name: string
type: publication
publication_type: string        # journal_article | monograph | reprint | review | obituary | note | index | bibliography
authors:
  - string                      # Canonical display names
year: integer | string
journal_code: string            # JMBRAS | JSBRAS
volume: integer | string
issue: string | null
pages: string                   # e.g., "23–44"
has_bibliography: boolean
has_footnotes: boolean
PublishedByMBRAS: boolean
source_doc: string
source_path: string             # Relative path, e.g., "../sources/doc_id.md"
summarized: boolean
status: string                  # stub | reviewed | published
keywords:
  - string
---
```

Note: Publication abstracts are not placed in frontmatter. If present in the source text, they live in the body under ## Abstract.

#### Persons (type: person)

```YAML
---
id: string
title: string
canonical_name: string
type: person
aliases:
  - string
roles:
  - string
is_contributor: boolean
status: string                  # stub | compiled
---
```

#### Concepts, Places, Events & Groups

```YAML
---
id: string
title: string
canonical_name: string
type: concept                   # concept | place | event | group
aliases:
  - string
broader:
  - string
narrower:
  - string
related:
  - title: string
    slug: string
    facet: string | null
    inferred: boolean
is_cluster: boolean
status: string
published: boolean
---
```

## 4. Subsystem Behavioral Guidelines

### `apps/bots` (Policy Engine)

* LLM Evaluates, Python Mutates: Models must not write arbitrary text directly to disk. The model returns a structured JSON patch payload, and munshi_bots.file_utils.apply_patch safely updates frontmatter or inserts validated links.
* Declarative Policies: Bot routines live in Markdown documents under apps/bots/policies/<name>.md. Do not build bespoke single-use runner classes.
* Defensive Grounding: Candidate providers must validate slugs against the filesystem before passing them to prompt contexts. Never allow bots to hallucinate target slugs.

### `apps/synthesizer` & `apps/summarizer`

* **MBRAS House Style**:
  * British English orthography (colour, centre, labour, artefact, characterised).
  * Oxford comma in lists of three or more elements.
  * Indigenous, Malay, and Latin taxa must be italicized and glossed on first appearance.
  * Colonial, archaic, or pejorative ethnonyms ("Chinaman", "Mohammedan", "Kling", "Sakai", "Coolie") must be replaced with accurate modern descriptors ("Chinese settler", "Muslim", "South Indian", "Orang Asli", "indentured labourer") unless directly analyzing historical terminology in quotes.
* **Strict Evidence Grounding**: Every statement must reflect the gathered research records. Do not interpolate outside historical context or unverified dates.

### `apps/api`

* **Domain Mutations, Not Generic CRUD**: Endpoints represent multi-file operations (`reassign-author`, `merge-authors`, `fix-source-path`) that update publication frontmatter, author bibliographies, and issue Tables of Contents in a single transaction.

## 5. Development & Verification Checklists

Before committing changes:

1. Verify Formatting & Types: Ensure modifications parse cleanly through PyYAML and Pydantic validation.
2. Execute Scoped Unit Tests:
  ```Bash
  uv run --package munshi-docproc pytest
  ```
3. Verify Git Cleanliness: Ensure scratch scripts, temporary triage outputs, and local virtual environments are not committed to git tracking.