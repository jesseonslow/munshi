# Munshi Publication Summarizer (`munshi-summarizer`)

An automated publication summarization and metadata extraction engine for the **Mat Munshi** digital historical encyclopedia. 

The engine ingests processed primary-source Markdown files from the *Journal of the Malayan/Malaysian Branch of the Royal Asiatic Society* (JMBRAS/JSBRAS), deterministically extracts modern frontmatter metadata (abstracts, keywords), calls high-context LLMs to generate page-anchored historiographical syntheses, and injects the resulting text into flat wiki stubs.

---

## Features

- **Grounded Attribution**: Directly cites source documents using relative anchor links (`([p. X](/sources/{doc_id}#page-X))`) derived from embedded `<span id="page-X"></span>` markers.
- **Two-Tier Summaries**: Outputs an introductory lede paragraph beneath the title, followed by an in-depth `## Summary` (with `### Key Findings` and `### Conclusion`) and a `## Context` block covering archival apparatus, colonial biases, and corpus nuances.
- **Deterministic Metadata Hoisting**: Automatically parses post-2015 `## Abstract` and `## Keywords` directly from source text and hoists them into YAML frontmatter without wasting LLM tokens.
- **Graceful Failure Handling**: Skips articles lacking source markdown without throwing exceptions, allowing incremental `docproc` batching.
- **Docproc Append Mode**: Can ingest raw source files directly to initialize brand-new wiki stubs with populated summaries.
- **Index Identification**: Automatically routes bibliographic indices to descriptive taxonomy overviews rather than narrative summaries.

---

## Directory Layout

apps/summarizer/
├── pyproject.toml
├── README.md
└── src/
    └── munshi_summarizer/
        ├── __init__.py
        ├── cli.py               # Click CLI entrypoint
        ├── config.py            # Pydantic BaseSettings loading from root .env
        ├── summarizer.py        # Core metadata harvester and injection pipeline
        └── templates/
            └── summarize_publication.jinja2 # Jinja2   payload rendering template