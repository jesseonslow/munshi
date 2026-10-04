"""
munshi_summarizer.summarizer

Core pipeline for extracting frontmatter metadata, executing streaming LLM syntheses,
and injecting publication summaries into MBRAS wiki markdown articles.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from openai import OpenAI
from rich.console import Console

from munshi_summarizer.config import SummarizerConfig

console = Console()


class PublicationSummarizer:
    """Orchestrates source resolution, metadata hoisting, and LLM-driven summary injection."""

    def __init__(self, config: SummarizerConfig):
        self.config = config
        self.client = OpenAI(
            api_key=self.config.openrouter_api_key or "dry-run-key",
            base_url=self.config.openrouter_base_url,
            timeout=300.0,
            default_headers={
                "HTTP-Referer": "https://github.com/munshi-project",
                "X-Title": "Munshi Publication Summarizer",
            },
        )
        template_dir = Path(__file__).resolve().parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    # -------------------------------------------------------------------------
    # 1. Frontmatter & Source Resolution
    # -------------------------------------------------------------------------
    def split_frontmatter(self, text: str) -> tuple[dict[str, Any], str]:
        """Separates YAML frontmatter from the Markdown body."""
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            return fm, parts[2]
        return {}, text

    def join_frontmatter(self, fm: dict[str, Any], body: str) -> str:
        """Serializes updated YAML frontmatter back onto the Markdown body."""
        yaml_str = yaml.dump(fm, sort_keys=False, allow_unicode=True)
        return f"---\n{yaml_str}---\n{body.lstrip()}"

    def resolve_source_files(self, wiki_file: Path, fm: dict[str, Any]) -> list[Path]:
        """
        Resolves one or more source markdown files.
        - Single-file publications (sitting directly in sources/) return [file].
        - Multi-part publications (in their own dedicated subfolder) return [frontmatter, glossary, etc.].
        - Guaranteed never to glob the root sources_dir.
        """
        source_path = fm.get("source_path")
        source_doc = fm.get("source_doc")
        sources_root = self.config.sources_dir.resolve()

        # ---------------------------------------------------------------------
        # 1. Check if source_doc points to a dedicated subfolder
        #    e.g. sources/jmbras-253-laderman-mainpeterisynopses-1987-7225e09bb3f3/
        # ---------------------------------------------------------------------
        if source_doc:
            candidate_dir = (self.config.sources_dir / source_doc).resolve()
            if candidate_dir.is_dir() and candidate_dir != sources_root:
                all_mds = sorted(candidate_dir.glob("*.md"))
                if all_mds:
                    def file_sort_key(p: Path) -> int:
                        stem = p.stem.lower()
                        if stem in {"frontmatter", "article", "references"}:
                            return 0
                        if stem == "glossary":
                            return 1
                        if stem in {"bibliography", "index"}:
                            return 2
                        return 3

                    return sorted(all_mds, key=file_sort_key)

        # ---------------------------------------------------------------------
        # 2. Check if source_path explicitly points to an existing file
        # ---------------------------------------------------------------------
        if source_path:
            p_rel_wiki = (wiki_file.parent / source_path).resolve()
            p_rel_src = (self.config.sources_dir / source_path).resolve()

            for target in (p_rel_wiki, p_rel_src):
                if target.is_file() and target.exists():
                    parent_dir = target.parent.resolve()
                    # If this file lives inside a dedicated subfolder (not the root sources folder),
                    # bundle the subfolder's markdown files (e.g. frontmatter.md + glossary.md)
                    if parent_dir != sources_root and parent_dir != wiki_file.parent.resolve():
                        sub_mds = sorted(parent_dir.glob("*.md"))
                        if len(sub_mds) > 1:
                            def sub_sort_key(p: Path) -> int:
                                stem = p.stem.lower()
                                if stem in {"frontmatter", "article", "references"}:
                                    return 0
                                if stem == "glossary":
                                    return 1
                                return 2
                            return sorted(sub_mds, key=sub_sort_key)
                    # Otherwise, it's a standalone flat file in the root sources directory
                    return [target]

        # ---------------------------------------------------------------------
        # 3. Check for standalone flat files matching source_doc in sources root
        #    e.g. sources/{source_doc}.md
        # ---------------------------------------------------------------------
        if source_doc:
            flat_file = (self.config.sources_dir / f"{source_doc}.md").resolve()
            if flat_file.is_file() and flat_file.exists():
                return [flat_file]

        return []

    def load_bundled_source_text(self, files: list[Path]) -> str:
        """Concatenates multiple related source files into a unified context payload."""
        if len(files) == 1:
            return files[0].read_text(encoding="utf-8")

        parts: list[str] = []
        for f in files:
            content = f.read_text(encoding="utf-8")
            parts.append(
                f'<source_file name="{f.name}">\n{content.strip()}\n</source_file>'
            )
        return "\n\n".join(parts)

    # -------------------------------------------------------------------------
    # 2. Deterministic Metadata Extraction
    # -------------------------------------------------------------------------
    def extract_frontmatter_metadata(self, source_text: str) -> dict[str, Any]:
        """Deterministically extracts Abstract and Keywords from source markdown."""
        head_text = source_text[:4000]
        extracted: dict[str, Any] = {"abstract": None, "keywords": []}

        abstract_match = re.search(
            r"##\s+Abstract\s*\n+(.*?)(?=\n+##|\Z)",
            head_text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if abstract_match:
            clean_abstract = abstract_match.group(1).strip()
            if len(clean_abstract.split()) <= 450:
                extracted["abstract"] = clean_abstract

        kw_match = re.search(
            r"##\s+Keywords\s*\n+(.*?)(?=\n+##|\Z)",
            head_text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if kw_match:
            raw_kw_block = kw_match.group(1).strip()
            if raw_kw_block.startswith("[") and raw_kw_block.endswith("]"):
                raw_kw_block = raw_kw_block[1:-1]

            tokens = re.split(r"[,;\n]\s*", raw_kw_block)
            keywords: list[str] = []
            for t in tokens:
                cleaned_item = re.sub(r"^[-*]\s*", "", t).strip().strip('"\'')
                if cleaned_item:
                    keywords.append(cleaned_item)

            if keywords:
                extracted["keywords"] = keywords

        return extracted

    # -------------------------------------------------------------------------
    # 3. LLM Synthesis Generation (Streaming & Adaptive Length)
    # -------------------------------------------------------------------------
    def generate_summary(
        self,
        metadata: dict[str, Any],
        doc_id: str,
        source_text: str,
        has_abstract: bool,
    ) -> str:
        """Streams synthesis from OpenRouter with real-time reasoning and token tracking."""
        word_count = len(source_text.split())
        page_anchors = re.findall(r'<span id="page-(\d+)"></span>', source_text)
        page_count = len(set(page_anchors)) or 1
        is_short_item = word_count < 1500 or page_count <= 2

        has_conclusion = bool(
            re.search(r"##\s+Conclusion\b", source_text, re.IGNORECASE)
        )
        is_index = (
            metadata.get("article_type") == "index"
            or metadata.get("document_type") == "index"
            or "index" in metadata.get("title", "").lower()
            or "index" in doc_id.lower()
        )

        console.print(
            f"[dim]Metrics: ~{word_count} words | {page_count} pages detected | "
            f"Mode: {'Index' if is_index else ('Concise' if is_short_item else 'Full Synthesis')}[/dim]"
        )

        if is_index:
            system_prompt = (
                "<|think_low|>\n"
                "You are an expert digital archivist for the Malaysian Branch of the Royal Asiatic Society (MBRAS).\n"
                "The target document is a BIBLIOGRAPHIC OR TOPICAL INDEX, not an essay.\n\n"
                "### OUTPUT FORMAT RULES:\n"
                "1. LEDE PARAGRAPH: Begin immediately with 2-3 sentences explaining what this index compiles, "
                "its date/volume range, and its overall taxonomic scheme.\n"
                "2. '## Summary': A structured functional description detailing Scope, Organization, and Usage.\n"
                "3. '## Context': Optional. Include only if compilation quirks or unique boundaries warrant note.\n\n"
                "### CITATION RULES:\n"
                "- Attribute page references using plain text citation markers: (p. X) or (pp. X–Y). Do NOT use web links.\n\n"
                "### STYLE GUIDE:\n"
                "- Write with British English spellings and use the Oxford Comma.\n"
                "- Use the Oxford Comma.\n"
                "- Non-English words and abbreviations must be defined when first mentioned"
            )
        elif is_short_item:
            # Calibrated prompt for short notes, fragments, and glossaries
            system_prompt = (
                "<|think_low|>\n"
                "You are an expert digital archivist for the Malaysian Branch of the Royal Asiatic Society (MBRAS).\n"
                "The target document is a SHORT NOTE, BRIEF NOTICE, OR TEXTUAL FRAGMENT.\n\n"
                "### CALIBRATED PROPORTIONALITY RULES:\n"
                "- Keep the summary concise and proportionate to the brief source text. Do NOT pad with filler.\n"
                "- Output EXACTLY:\n"
                "  1. LEDE PARAGRAPH: 1-2 sentences stating the document's precise subject and author.\n"
                "  2. '## Summary': 1-2 focused paragraphs covering what is contained, argued, or documented.\n"
                "- Do NOT generate '### Key Findings' or '### Conclusion' subheadings for short items.\n"
                "- Do NOT generate a '## Context' section unless there is an extraordinary colonial bias or provenance issue.\n"
                "- Attribute citations using plain text markers: (p. X). Do NOT generate web links.\n"
                "- NEVER output '# H1' or '## References'."
            )
        else:
            # Full synthesis prompt for substantive publications
            system_prompt = (
                "<|think_low|>\n"
                "You are an expert digital archivist and historiographer for the Malaysian Branch "
                "of the Royal Asiatic Society (MBRAS). Your mission is to produce an information-dense, "
                "rigorously grounded synthesis of this publication to serve as source material for topic syntheses.\n\n"
                "### SOURCE STRUCTURE HINTS:\n"
                f"- Explicit '## Abstract' present: {'YES' if has_abstract else 'NO'}.\n"
                f"- Explicit '## Conclusion' present: {'YES' if has_conclusion else 'NO'}.\n\n"
                "### OUTPUT FORMAT RULES:\n"
                "1. LEDE PARAGRAPH: Begin immediately with a concise 2-3 sentence overview (subject, author, historical scope).\n"
                "2. '## Summary': An analytical synthesis containing:\n"
                "   - Running prose analyzing core arguments, primary apparatus, and historical arcs.\n"
                "   - '### Key Findings': 3-6 concrete, specific assertions (dates, treaties, figures).\n"
                "   - '### Conclusion': A succinct analysis of the author's definitive historical takeaway.\n"
                "3. '## Context': (OPTIONAL). Include ONLY if there is genuine archival apparatus, colonial bias, "
                "or notable historiographical debates. If standard, omit this section entirely.\n\n"
                "### CITATION RULES:\n"
                "- Ground all claims, quotes, and findings with plain in-text page citations: (p. X) or (pp. X–Y).\n"
                "- NEVER use web links (no markdown brackets linking to /sources/ paths).\n"
                "- NEVER output '# H1' or '## References'. Begin directly with the lede paragraph."
            )

        template = self.jinja_env.get_template("summarize_publication.jinja2")
        user_content = template.render(
            metadata=metadata,
            doc_id=doc_id,
            source_text=source_text,
            has_abstract=has_abstract,
            has_conclusion=has_conclusion,
        )

        # Stream OpenRouter response with reasoning tokens
        stream_resp = self.client.chat.completions.create(
            model=self.config.summarizer_model_id,
            temperature=self.config.temperature,
            max_tokens=4096,
            extra_body={"reasoning": {"max_tokens": 1024}},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            stream=True,
        )

        reasoning_chunks: list[str] = []
        content_chunks: list[str] = []
        in_thinking_mode = False

        console.print("[bold cyan]Streaming response from model...[/bold cyan]")
        for chunk in stream_resp:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            # Stream thinking/reasoning tokens
            reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
            if reasoning:
                if not in_thinking_mode:
                    console.print("\n[dim magenta]Thinking...[/dim magenta]\n", end="")
                    in_thinking_mode = True
                print(f"\033[90m{reasoning}\033[0m", end="", flush=True)
                reasoning_chunks.append(reasoning)

            # Stream finalized markdown content
            content = delta.content or ""
            if content:
                if in_thinking_mode:
                    console.print("\n\n[bold green]Generating Publication Summary:[/bold green]\n")
                    in_thinking_mode = False
                content_chunks.append(content)
                print(content, end="", flush=True)

        print("\n")
        return "".join(content_chunks).strip()

    # -------------------------------------------------------------------------
    # 4. Body Splicing & Frontmatter Update
    # -------------------------------------------------------------------------
    def inject_summary_into_article(
        self,
        article_text: str,
        generated_output: str,
        extracted_meta: dict[str, Any],
    ) -> str:
        """Splices generated summary into the article body while preserving references."""
        fm, body = self.split_frontmatter(article_text)
        fm["summarized"] = True

        if extracted_meta.get("keywords") and not fm.get("keywords"):
            fm["keywords"] = extracted_meta["keywords"]

        if extracted_meta.get("abstract") and not fm.get("abstract"):
            fm["abstract"] = extracted_meta["abstract"]

        body = re.sub(r"<!--\s*(Synthesis engine|Summarizer):.*?\s*-->\n?", "", body)

        h1_match = re.search(r"^(#\s+[^\n]+)", body, flags=re.MULTILINE)
        h1_line = h1_match.group(1) if h1_match else ""

        cleaned_body = re.sub(
            r"##\s+(Overview|Summary|Context).*?(?=\n##\s+|\Z)",
            "",
            body,
            flags=re.DOTALL,
        ).strip()

        if "## References" in cleaned_body:
            parts = cleaned_body.split("## References", 1)
            trailing = "## References" + parts[1]
            new_body = f"{h1_line}\n\n{generated_output.strip()}\n\n{trailing.strip()}\n"
        else:
            new_body = (
                f"{h1_line}\n\n{generated_output.strip()}\n\n"
                f"## References\n<!-- Grounded occurrences and citations -->\n"
            )

        return self.join_frontmatter(fm, new_body)

    # -------------------------------------------------------------------------
    # 5. Article Processing Gateways
    # -------------------------------------------------------------------------
    def process_wiki_article(
        self, wiki_path: Path, force: bool = False, execute: bool = True
    ) -> bool:
        """Processes an existing wiki article file."""
        raw_content = wiki_path.read_text(encoding="utf-8")
        fm, _ = self.split_frontmatter(raw_content)

        if fm.get("type") != "article":
            return False

        article_type = fm.get("article_type", "article").lower()
        allowed_types = {"article", "note", "notes_and_queries"}
        if article_type not in allowed_types:
            return False

        if (fm.get("summarized") is True or fm.get("summarised") is True) and not force:
            console.print(f"[dim]Skipping already summarized: {wiki_path.name}[/dim]")
            return False

        source_files = self.resolve_source_files(wiki_path, fm)
        if not source_files:
            console.print(
                f"[yellow]Warning: Source missing for {wiki_path.name}. Skipping gracefully.[/yellow]"
            )
            return False

        file_names = ", ".join(f.name for f in source_files)
        source_text = self.load_bundled_source_text(source_files)
        doc_id = fm.get("source_doc") or source_files[0].stem

        extracted_meta = self.extract_frontmatter_metadata(source_text)
        has_abstract = bool(extracted_meta.get("abstract"))
        kw_count = len(extracted_meta.get("keywords", []))

        console.print(
            f"[cyan]Targeting [{article_type}]: {wiki_path.name} -> [{file_names}] "
            f"(Abstract: {'Yes' if has_abstract else 'No'}, Keywords: {kw_count})[/cyan]"
        )

        if not execute:
            console.print("[yellow]Dry-run: Validated source. Skipping LLM API call.[/yellow]")
            return True

        generated_blocks = self.generate_summary(
            metadata=fm,
            doc_id=doc_id,
            source_text=source_text,
            has_abstract=has_abstract,
        )
        new_content = self.inject_summary_into_article(
            article_text=raw_content,
            generated_output=generated_blocks,
            extracted_meta=extracted_meta,
        )
        wiki_path.write_text(new_content, encoding="utf-8")
        console.print(f"[bold green]Successfully summarized:[/bold green] {wiki_path.name}")
        return True

    def create_from_source(self, source_path: Path, execute: bool = True) -> Path:
        """Direct Ingestion Mode: Creates a new wiki stub from raw source markdown."""
        source_text = source_path.read_text(encoding="utf-8")
        src_fm, _ = self.split_frontmatter(source_text)

        slug = src_fm.get("doc_id") or source_path.stem
        target_wiki = self.config.wiki_dir / f"{slug}.md"

        extracted_meta = self.extract_frontmatter_metadata(source_text)
        has_abstract = bool(extracted_meta.get("abstract"))

        metadata: dict[str, Any] = {
            "id": slug,
            "work_id": src_fm.get("work_id", slug),
            "title": src_fm.get("title", source_path.stem),
            "type": "article",
            "article_type": src_fm.get("document_type", "article"),
            "authors": [src_fm.get("author")] if src_fm.get("author") else [],
            "year": src_fm.get("year", "n.d."),
            "journal_code": src_fm.get("journal", "JMBRAS"),
            "volume": src_fm.get("volume"),
            "issue": src_fm.get("issue"),
            "pages": src_fm.get("pages"),
            "source_doc": slug,
            "source_path": f"../sources/{source_path.name}",
            "summarized": False,
            "status": "stub",
            "published": false,
        }

        if extracted_meta.get("abstract"):
            metadata["abstract"] = extracted_meta["abstract"]
        if extracted_meta.get("keywords"):
            metadata["keywords"] = extracted_meta["keywords"]

        generated_blocks = "<!-- Summarizer: Insert publication summary here -->"
        if execute:
            console.print(f"[cyan]Generating initial summary for new doc: {slug}...[/cyan]")
            generated_blocks = self.generate_summary(
                metadata=metadata,
                doc_id=slug,
                source_text=source_text,
                has_abstract=has_abstract,
            )
            metadata["summarized"] = True

        stub_content = (
            f"# {metadata['title']}\n\n"
            f"{generated_blocks}\n\n"
            f"## References\n<!-- Grounded occurrences and citations -->\n"
        )
        final_md = self.join_frontmatter(metadata, stub_content)
        target_wiki.parent.mkdir(parents=True, exist_ok=True)
        target_wiki.write_text(final_md, encoding="utf-8")
        console.print(f"[bold green]Created new wiki article:[/bold green] {target_wiki.name}")
        return target_wiki