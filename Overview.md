# Mat Munshi: Architecture Overview & System Reference

## 1. Vision & Core Philosophy
* **Human-Centric Archival Encyclopedia**: Deliver an interlinked, static digital research portal (Wiki) covering Malayan history, synthesized from the *Journal of the Straits / Malayan / Malaysian Branch of the Royal Asiatic Society* (JSBRAS/JMBRAS), monographs, and reprints.
* **Top-Down Authority Spine**: Use *Index Malaysiana* as the primary ground truth to extract known authors, articles, publications, and subject taxonomies, avoiding naive, unconstrained NER extraction across arbitrary text blocks.
* **Deterministic Attribution**: Ground every historical claim, concept, and biographical profile directly in archival sources using immutable page anchors (`<span id="page-N"></span>`) and issue metadata.
* **Hybrid Two-Tier Resolution**: Combine fast exact-match authority lookup caches with semantic embedding fallback (`zvec-grep` / `ZvecResolver`) to resolve historical name variants and OCR fluctuations without cloud database lock-in.

---

## 2. System Architecture & Component Flow

                      │
                      ▼
      ┌─────────────────────────────────┐
      │ 1. apps/docproc (PyMuPDF + VLM) │
      └─────────────────────────────────┘
                      │
  Outputs: JSONL Layout & Text Bundles
                      │
                      ▼
      ┌─────────────────────────────────┐
      │ 2. apps/stitcher (stitcher.py)  │
      └─────────────────────────────────┘
                      │
      Output: Clean Source Markdown
    (/content/sources/{doc_id}.md with
      YAML frontmatter, <span id="page-N">, [^N])
                      │
┌─────────────────────┴─────────────────────┐
│                                           │
▼                                           ▼
┌─────────────────────────────────┐       ┌───────────────────────────────┐
│ db/seed_dictionary.py           │       │ Articles & Book Chapters      │
│ (Entities, Aliases, Redirects,  │       └──────────────┬────────────────┘
│  Clusters, Faceted Subtopics)   │                      │
└────────────────┬────────────────┘                      │
                 │                                       ▼
                 ▼                        ┌───────────────────────────────┐
┌─────────────────────────────────┐       │ 4. Article-Level Synthesizer  │
│ 3. apps/ledger (munshi_ledger)  │◀─────┤ (Direct Single-Pass & Map-    │
│ - Authority Builder             │       │  Reduce Chapter Summaries)    │
│ - In-Memory Cache + ZvecResolver│       └──────────────┬────────────────┘
│ - entity_ledger.db (SQLite)     │                      │
└────────────────┬────────────────┘                      │
                 │                                       ▼
                 └──────────────────────────────▶ ┌───────────────────────────────┐
                                                   │ 5. apps/synthesizer           │
                                                   │ (munshi_synthesizer)          │
                                                   │ - Aggregator & Reranker       │
                                                   │ - Jinja2 Template Generators  │
                                                   └──────────────┬────────────────┘
                                                   │
                                                   ▼
                                                   Generated OKF Markdown Pages
                                                   (/content/wiki/{category}/*.md)
                                                   │
                                                   ▼
                                                   Static Presentation (Astro UI)
                                                   & Pagefind / Search Layer

---
 
## 3. Detailed Application Stack

### App 1: Document Processing (`apps/docproc`)
* **Role**: Layout segmentation, reading-order reconstruction, and metadata detection from digitized PDFs.
* **Pipeline Implementation** (`munshi_docproc/pipeline/`):
  * `extract_mupdf.py` / `extract_qwen3vl.py`: Dual-path extraction utilizing PyMuPDF for native text and bounding boxes, routing complex OCR pages to vision-language models (Qwen-VL / Flash models via OpenRouter).
  * `detect_content_area.py`, `detect_rotation.py`, `detect_language.py`: Page pre-processing and coordinate normalisation.
  * `classify_doctype.py`: Distinguishes between journal articles, monograph chapters, indexes, front matter, and book reviews.
  * `detect_footnotes.py` & `link_footnote_refs.py`: Footnote isolation and dynamic bracket linking (`[^N]`).
  * `detect_captions.py` & `detect_figures.py`: Plate/figure extraction and association with caption blocks.
  * `extract_metadata.py`, `enrich_metadata_llm.py`, `enrich_metadata_web.py`: JSTOR / journal front-block parsing.
* **Outputs**: Structured JSONL packages (`documents.jsonl`, `text_blocks.jsonl`, `footnote_refs.jsonl`, `figures.jsonl`).

### App 2: Source Stitcher (`apps/stitcher`)
* **Role**: Deterministic, zero-inference compilation of document processing artifacts into unbroken primary-source Markdown files.
* **Core Script**: `stitcher.py`
* **Key Formatting Guarantees**:
  * **Page Anchoring**: Injects deterministic HTML span tags (`<span id="page-N"></span>`) immediately preceding each page's body text for browser jump targets.
  * **Footnote Consolidation**: Formats linked footnotes into sequential references at the document bottom.
  * **Metadata Hoisting**: Translates JSTOR citation headers and document metadata into clean YAML frontmatter (`doc_id`, `title`, `author`, `journal`, `volume`, `year`, `stable_url`).

### App 3: Authority Index & Occurrence Ledger (`apps/ledger`)
* **Role**: Resolves mentions of historical persons, toponyms, events, and subjects against a curated authority index, tracking occurrences across the corpus.
* **Core Modules** (`munshi_ledger/`):
  * `authority_builder.py`: Compiles `db/seed_dictionary.py` into a standardized `authority_index.json` schema. Handles inflection generation, name permutations, cluster expansion, and faceted relationship linking (`Parent: Subtopic`).
  * `db.py`: Initializes SQLite schema (`entity_ledger.db`) storing canonical entities, aliases, redirects, clusters, and occurrence snippets (`doc_id`, `page_num_1`, `context_snippet`).
  * `parser.py` & `extractor.py`: Tokenizes and extracts candidate entities from source texts (via lookup sweeps and GLiNER).
  * `resolver.py`: Two-tier resolution architecture:
    1. *Exact Cache Match*: Fast $O(1)$ lookup for canonical names and explicit aliases.
    2. *Vector Resolver (`zvec-grep`)*: Embedding fallback using sentence transformers to disambiguate fuzzy matches, OCR noise, and morphologically shifted variants.

### App 4: Article Summaries (Intermediate Knowledge Layer)
* **Role**: Prevents context-window saturation during high-level synthesis by producing pre-computed, atomic summaries for every paper and chapter before synthesizing overarching topics.
* **Workflow**:
  * **Standard Articles (5–35 pages)**: Single-pass direct ingestion into long-context LLMs. Produces structured summaries detailing core thesis, primary sources cited (e.g., VOC records, *Sejarah Melayu*, colonial correspondence), key actors, and subject tags.
  * **Monographs (100–400+ pages)**: Docproc 2.0 folder schema (`chapter-01.md`, `chapter-02.md`, etc.). Individual chapter summaries are mapped independently and concatenated into a master monograph entry via map-reduce.

### App 5: Encyclopedia Synthesizer (`apps/synthesizer`)
* **Role**: Assembles multi-source Open Knowledge Format (OKF v0.2) markdown encyclopedia entries.
* **Core Modules** (`munshi_synthesizer/pipeline/`):
  * `authority.py`: Loads the compiled `authority_index.json` to identify target entities and their cluster/facet dependencies.
  * `aggregator.py`: Queries `entity_ledger.db` and intermediate article summaries to aggregate all primary snippets and citations for a requested entity.
  * `rerank.py` & `zvec.py`: Context window optimization—filters out low-signal mentions and prioritizes substantive discussions.
  * `generator.py`: Executes Jinja2 template rendering using domain-specific prompt wrappers:
    * `person.jinja2`: Biographical trajectory, offices held, contemporary relationships, and bibliography.
    * `place.jinja2`: Geographical scope, historical role, administrative transitions, and key archaeological/historical events.
    * `event.jinja2`: Dates, background, timeline, participants, and historiographical debates.
    * `concept.jinja2`: Cultural, legal (*adat*), religious, or scientific definitions and development across the literature.
    * `group.jinja2`: Ethnic communities, administrative bodies, or institutions.

---

## 4. Controlled Authority Dictionary Architecture (`db/seed_dictionary.py`)

The knowledge graph is guided by a multi-dictionary taxonomy:

1. **`entities`**: Singular, clean canonical strings for unambiguous entities (e.g., `"Sultan Mansur Shah (Malacca)"`, `"Ban Hin Lee Bank"`, `"Orang Asli"`).
2. **`aliases`**: Historical variants, regnal titles, honorific additions, and OCR variations resolving to the canonical entity.
3. **`redirects`**: Lexical normalizations mapping legacy terminology or singular roles to standard headwords (e.g., `"Aborigines" -> "Orang Asli"`, `"Acting" -> "Theatre"`).
4. **`subtopics`**: Faceted topical indices defining regional or conceptual subdivisions (e.g., `"Singapore": ["architecture", "banking", "history"]`).
5. **`clusters`**: Thematic and taxonomic aggregators for synthesis (e.g., `"Aculeata": ["Ants", "Bees", "Wasps"]`, `"Archaeological finds"`). Group related items without requiring artificial standalone entity nodes.
6. **`related`**: Faceted graph edges using qualified notation (`"Babas": ["Peranakan: Dialects", "Chinese: Language and literature"]`) enabling targeted bibliographic retrieval.

---

## 5. Summary of Architectural Decisions

| Domain | Initial Prototype | Current Working Architecture | Rationale |
| :--- | :--- | :--- | :--- |
| **Indexing Strategy** | Bottom-up NER sweep across all raw OCR chunks | Top-down taxonomy grounded in *Index Malaysiana* | Prevents unstructured "bag of words" noise; aligns with established bibliographic scholarship. |
| **Document Processing** | Monolithic PDF chunking | Dual-pass layout analysis (MuPDF + VLM) $\rightarrow$ Stitched Markdown | Produces human-readable primary sources with preserved reading order and `<span id="page-N"></span>` anchors. |
| **Monograph Handling** | Chunked window vectors | Chapter-partitioned folders with two-tier map-reduce summarization | Preserves chapter boundaries and narrative coherence while staying well within LLM context windows. |
| **Entity Resolution** | Direct vector similarity matching | Exact-match alias cache + `zvec-grep` vector fallback | Delivers instant $O(1)$ deterministic lookups while retaining vector resilience for OCR errors. |
| **Attribution** | Stochastic citation via prompt instructions | Deterministic replacement of `[REF-N]` tags with relative anchor links | Eliminates hallucinated citations by anchoring directly to confirmed source page spans. |
| **Synthesis Ingestion** | Raw corpus snippets fed directly to synthesis prompt | Pre-computed Article OKF summaries + Ledger occurrences | Solves context-window bottlenecks and ensures high-signal conceptual synthesis. |