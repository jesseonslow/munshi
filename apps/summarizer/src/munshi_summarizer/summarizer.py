"""
munshi_summarizer.summarizer

Core pipeline for extracting frontmatter metadata, executing streaming LLM syntheses,
and injecting publication summaries into MBRAS wiki markdown articles.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import random
import re
from typing import Any
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from openai import AsyncOpenAI  # <-- FIXED: Import AsyncOpenAI
from rich.console import Console

from munshi_summarizer.config import SummarizerConfig

console = Console()

EXCLUDED_SECTION_NAMES = {
    "index",
    "bibliography",
    "references",
    "list_of_plates",
    "list_of_figures",
    "abbreviations",
}


async def call_llm_with_retry(
    client: AsyncOpenAI,
    payload_kwargs: dict[str, Any],
    max_retries: int = 5,
) -> Any:
    """Executes completion with exponential backoff on 429/5xx errors."""
    delay = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            return await client.chat.completions.create(**payload_kwargs)
        except Exception as e:
            err_str = str(e).lower()
            retryable = any(
                code in err_str
                for code in ["429", "502", "503", "504", "timeout", "rate limit", "connection reset"]
            )
            if attempt < max_retries and retryable:
                sleep_time = delay + random.uniform(0.1, 0.4)
                await asyncio.sleep(sleep_time)
                delay *= 2.0
            else:
                raise e


class PublicationSummarizer:
    """Orchestrates source resolution, metadata hoisting, and LLM-driven summary injection."""

    def __init__(self, config: SummarizerConfig):
        self.config = config
        # FIXED: Instantiate AsyncOpenAI client
        self.client = AsyncOpenAI(
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
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            return fm, parts[2]
        return {}, text

    def join_frontmatter(self, fm: dict[str, Any], body: str) -> str:
        yaml_str = yaml.dump(fm, sort_keys=False, allow_unicode=True)
        return f"---\n{yaml_str}---\n{body.lstrip()}"

    def resolve_source_files(self, wiki_file: Path, fm: dict[str, Any]) -> list[Path]:
        source_path = fm.get("source_path")
        source_doc = fm.get("source_doc")
        sources_root = self.config.sources_dir.resolve()

        if source_doc:
            candidate_dir = (self.config.sources_dir / source_doc).resolve()
            if candidate_dir.is_dir() and candidate_dir != sources_root:
                all_mds = [
                    p for p in candidate_dir.glob("*.md")
                    if p.stem.lower() not in EXCLUDED_SECTION_NAMES
                ]
                if all_mds:
                    def file_sort_key(p: Path) -> int:
                        stem = p.stem.lower()
                        if stem in {"frontmatter", "article", "references"}:
                            return 0
                        if stem == "glossary":
                            return 1
                        return 2

                    return sorted(all_mds, key=file_sort_key)

        if source_path:
            p_rel_wiki = (wiki_file.parent / source_path).resolve()
            p_rel_src = (self.config.sources_dir / source_path).resolve()

            for target in (p_rel_wiki, p_rel_src):
                if target.is_file() and target.exists():
                    parent_dir = target.parent.resolve()
                    if parent_dir != sources_root and parent_dir != wiki_file.parent.resolve():
                        sub_mds = [
                            p for p in parent_dir.glob("*.md")
                            if p.stem.lower() not in EXCLUDED_SECTION_NAMES
                        ]
                        if len(sub_mds) > 1:
                            def sub_sort_key(p: Path) -> int:
                                stem = p.stem.lower()
                                if stem in {"frontmatter", "article", "references"}:
                                    return 0
                                if stem == "glossary":
                                    return 1
                                return 2
                            return sorted(sub_mds, key=sub_sort_key)
                    return [target]

        if source_doc:
            flat_file = (self.config.sources_dir / f"{source_doc}.md").resolve()
            if flat_file.is_file() and flat_file.exists():
                return [flat_file]

        return []

    def load_bundled_source_text(self, files: list[Path]) -> str:
        if len(files) == 1:
            return files[0].read_text(encoding="utf-8")

        parts: list[str] = []
        for f in files:
            content = f.read_text(encoding="utf-8")
            parts.append(
                f'<source_file name="{f.name}">\n{content.strip()}\n</source_file>'
            )
        return "\n\n".join(parts)

    def extract_frontmatter_metadata(self, source_text: str) -> dict[str, Any]:
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
    # 2. Async LLM Synthesis
    # -------------------------------------------------------------------------
    async def generate_summary_async(
        self,
        metadata: dict[str, Any],
        doc_id: str,
        source_text: str,
        has_abstract: bool,
        semaphore: asyncio.Semaphore,
        stream_to_console: bool = False,
    ) -> str:
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
                "- Non-English words and abbreviations must be defined when first mentioned."
            )
        elif is_short_item:
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
                "- Do NOT generate a '## Context' section unless there is an extraordinary provenance issue.\n"
                "- Attribute citations using plain text markers: (p. X). Do NOT generate web links.\n"
                "- NEVER output '# H1' or '## References'."
            )
        else:
            lede_instruction = (
                "Do NOT generate an introductory lede paragraph or overview sentence above '## Summary', "
                "as the article already contains an official author abstract. Begin your output IMMEDIATELY "
                "with the heading '## Summary'."
                if has_abstract
                else (
                    "Begin your output immediately with an introductory LEDE PARAGRAPH (2-3 sentences) "
                    "directly stating the author, publication year, historical setting, and overarching thesis. "
                    "Follow this directly with '## Summary'."
                )
            )

            system_prompt = (
                "<|think_low|>\n"
                "You are an expert digital archivist and historiographer for the Malaysian Branch "
                "of the Royal Asiatic Society (MBRAS).\n"
                "Your mission is to produce an information-dense, proportionate summary of this publication.\n\n"
                f"### OPENING DIRECTIVE:\n{lede_instruction}\n\n"
                "### FORMAT & PROPORTIONALITY RULES:\n"
                "- Write in clear, natural prose. Avoid clinical academic subheadings.\n"
                "1. '## Summary': A concise narrative of 2 to 3 focused paragraphs.\n"
                "2. '### Key Findings': 4-6 concise bullet points containing concrete empirical evidence.\n"
                "3. '### Conclusion': 1 concise paragraph on the author's definitive historical takeaway.\n"
                "4. '## Context': (OPTIONAL): 1-2 brief bullets on colonial role or archival collections.\n\n"
                "### CITATION RULES:\n"
                "- Ground claims with plain-text parenthetical citations: (p. X) or (pp. X–Y).\n"
                "- NEVER output '# H1' or '## References'."
            )

        template = self.jinja_env.get_template("summarize_publication.jinja2")
        user_content = template.render(
            metadata=metadata,
            doc_id=doc_id,
            source_text=source_text,
            has_abstract=has_abstract,
            has_conclusion=has_conclusion,
        )

        # Retain your configured reasoning budget (256 for short, 1024 for long)
        thinking_budget = 256 if is_short_item else 1024

        payload_kwargs = {
            "model": self.config.summarizer_model_id,
            "temperature": self.config.temperature,
            "max_tokens": 8192,
            "extra_body": {"reasoning": {"max_tokens": thinking_budget}},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }

        async with semaphore:
            if stream_to_console:
                payload_kwargs["stream"] = True
                stream_resp = await call_llm_with_retry(self.client, payload_kwargs)
                content_chunks = []
                async for chunk in stream_resp:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    if delta.content:
                        print(delta.content, end="", flush=True)
                        content_chunks.append(delta.content)
                print("\n")
                return "".join(content_chunks).strip()
            else:
                resp = await call_llm_with_retry(self.client, payload_kwargs)
                return (resp.choices[0].message.content or "").strip()

    # -------------------------------------------------------------------------
    # 3. Body Splicing & Frontmatter Update
    # -------------------------------------------------------------------------
    def inject_summary_into_article(
        self,
        article_text: str,
        generated_output: str,
        extracted_meta: dict[str, Any],
    ) -> str:
        fm, body = self.split_frontmatter(article_text)
        fm["summarized"] = True

        if extracted_meta.get("keywords") and not fm.get("keywords"):
            fm["keywords"] = extracted_meta["keywords"]

        fm.pop("abstract", None)
        body = re.sub(r"<!--\s*(Synthesis engine|Summarizer):.*?\s*-->\n?", "", body)

        h1_match = re.search(r"^(#\s+[^\n]+)", body, flags=re.MULTILINE)
        h1_line = h1_match.group(1) if h1_match else ""

        cleaned_body = re.sub(
            r"##\s+(Abstract|Overview|Summary|Context).*?(?=\n##\s+|\Z)",
            "",
            body,
            flags=re.DOTALL,
        ).strip()

        abstract_block = ""
        source_abstract = extracted_meta.get("abstract")
        if source_abstract:
            abstract_block = f"## Abstract\n\n{source_abstract}\n\n"

        output_body = f"{h1_line}\n\n{abstract_block}{generated_output.strip()}\n"

        if "## References" in cleaned_body:
            parts = cleaned_body.split("## References", 1)
            trailing = "## References" + parts[1]
            new_body = f"{output_body}\n{trailing.strip()}\n"
        else:
            new_body = f"{output_body}\n## References\n<!-- Grounded occurrences and citations -->\n"

        return self.join_frontmatter(fm, new_body)

    # -------------------------------------------------------------------------
    # 4. Article Processing Gateways
    # -------------------------------------------------------------------------
    async def process_wiki_article_async(
        self,
        wiki_path: Path,
        semaphore: asyncio.Semaphore,
        force: bool = False,
        execute: bool = True,
        stream_to_console: bool = False,
    ) -> bool:
        raw_content = wiki_path.read_text(encoding="utf-8")
        fm, _ = self.split_frontmatter(raw_content)

        if fm.get("type") not in ("article", "publication"):
            return False

        article_type = (fm.get("article_type") or fm.get("publication_type") or "article").lower()
        if article_type in {"index", "obituary", "review"}:
            return False

        if (fm.get("summarized") is True or fm.get("summarised") is True) and not force:
            return False

        source_files = self.resolve_source_files(wiki_path, fm)
        if not source_files:
            return False

        source_text = self.load_bundled_source_text(source_files)
        doc_id = fm.get("source_doc") or source_files[0].stem

        extracted_meta = self.extract_frontmatter_metadata(source_text)
        has_abstract = bool(extracted_meta.get("abstract"))

        if not execute:
            return True

        generated_blocks = await self.generate_summary_async(
            metadata=fm,
            doc_id=doc_id,
            source_text=source_text,
            has_abstract=has_abstract,
            semaphore=semaphore,
            stream_to_console=stream_to_console,
        )

        new_content = self.inject_summary_into_article(
            article_text=raw_content,
            generated_output=generated_blocks,
            extracted_meta=extracted_meta,
        )
        wiki_path.write_text(new_content, encoding="utf-8")
        return True

    async def create_from_source_async(self, source_path: Path, execute: bool = True) -> Path:
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
            "published": False,
        }

        if extracted_meta.get("abstract"):
            metadata["abstract"] = extracted_meta["abstract"]
        if extracted_meta.get("keywords"):
            metadata["keywords"] = extracted_meta["keywords"]

        generated_blocks = "<!-- Summarizer: Insert publication summary here -->"
        if execute:
            console.print(f"[cyan]Generating initial summary for new doc: {slug}...[/cyan]")
            generated_blocks = await self.generate_summary_async(
                metadata=metadata,
                doc_id=slug,
                source_text=source_text,
                has_abstract=has_abstract,
                semaphore=asyncio.Semaphore(1),
                stream_to_console=True,
            )
            metadata["summarized"] = True

        abstract_block = ""
        if metadata.get("abstract"):
            abstract_block = f"## Abstract\n\n{metadata['abstract']}\n\n"

        stub_content = (
            f"# {metadata['title']}\n\n"
            f"{abstract_block}{generated_blocks}\n\n"
            f"## References\n<!-- Grounded occurrences and citations -->\n"
        )
        final_md = self.join_frontmatter(metadata, stub_content)
        target_wiki.parent.mkdir(parents=True, exist_ok=True)
        target_wiki.write_text(final_md, encoding="utf-8")
        console.print(f"[bold green]Created new wiki article:[/bold green] {target_wiki.name}")
        return target_wiki