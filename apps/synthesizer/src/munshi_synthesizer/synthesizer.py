"""Thematic synthesis engine supporting dynamic token budgets, category templates, and live streaming."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from openai import OpenAI
from rich.console import Console

from munshi_synthesizer.config import SynthesizerConfig
from munshi_synthesizer.indexer import process_numbered_citations
from munshi_synthesizer.parser import (
    PublicationParser,
    join_frontmatter,
    split_frontmatter,
)
from munshi_synthesizer.rerank import PublicationReranker
from munshi_synthesizer.schema import PublicationSource

logger = logging.getLogger(__name__)
console = Console()


class TopicSynthesizer:
    """Manages source validation, budget calculation, prompt rendering, and prose synthesis."""

    MIN_SOURCES_PER_SUBTOPIC: int = 2
    MIN_SOURCES_PER_DOCUMENT: int = 2

    def __init__(self, config: SynthesizerConfig):
        self.config = config
        self.parser = PublicationParser()
        self.reranker = PublicationReranker(model_dir=self.config.rerank_model_dir)
        self.client = OpenAI(
            api_key=self.config.openrouter_api_key or "placeholder",
            base_url=self.config.openrouter_base_url,
            timeout=300.0,
            default_headers={
                "HTTP-Referer": "https://github.com/munshi-project",
                "X-Title": "Munshi Synthesizer",
            },
        )
        template_dir = Path(__file__).resolve().parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    
    @staticmethod
    def split_frontmatter(text: str) -> tuple[dict, str]:
        return split_frontmatter(text)

    @staticmethod
    def join_frontmatter(fm: dict, body: str) -> str:
        return join_frontmatter(fm, body)

    def extract_sources_structure(self, topic_body: str) -> tuple[dict[str, list[str]], bool]:
        return self.parser.extract_sources_structure(topic_body, self.config.wiki_dir)

    def _resolve_raw_source_text(self, slug: str) -> str | None:
        return self.parser.resolve_raw_source_text(slug, self.config.wiki_dir)

    def calculate_dynamic_budgets(
        self,
        sources: list[PublicationSource],
        subtopic_count: int,
        is_monograph_fallback: bool = False,
        is_escalated_full_text: bool = False,
        is_macro_cluster: bool = False,
    ) -> tuple[int, int, int]:
        """
        Dynamically calculates (reasoning_budget, max_tokens, target_words)
        strictly tied to informational footprint and source diversity.
        """
        num_sources = len(sources)

        # Tier 1: Single-source topics (even if full primary text is escalated)
        # An isolated natural history note, single memoir, or lone survey should stay compact.
        if num_sources == 1:
            if is_escalated_full_text or is_monograph_fallback:
                target_words = 650
                reasoning_budget = 1024
            else:
                target_words = 400
                reasoning_budget = 1024

        # Tier 2: Macro portals and deep thematic clusters
        elif is_macro_cluster or subtopic_count >= 4 or num_sources > 10:
            target_words = 1600
            reasoning_budget = 2048

        # Tier 3: Limited / Small Multi-Source Topics (2-3 sources)
        elif num_sources <= 3:
            target_words = 600
            reasoning_budget = 1024

        # Tier 4: Standard Substantive Topics (4-10 sources, e.g. Sulu, Germany)
        else:
            target_words = 1000
            reasoning_budget = 1536

        # Token translation: 1 word ~ 1.6 tokens + generous buffer
        expected_output_tokens = int(target_words * 1.6)
        max_tokens = reasoning_budget + expected_output_tokens + 1024

        return reasoning_budget, max_tokens, target_words

    def get_valid_sources(self, slugs: list[str]) -> list[PublicationSource]:
        """Loads and verifies publication sources, filtering out empty or unsummarized stubs."""
        valid_sources: list[PublicationSource] = []
        for slug in slugs:
            pub_path = self.config.wiki_dir / f"{slug}.md"
            pub = self.parser.parse(pub_path)
            if not pub:
                continue

            has_substance = bool(
                (pub.summary and len(pub.summary.strip()) > 50)
                or pub.key_findings
                or (pub.lede and len(pub.lede.strip()) > 50)
            )
            if has_substance:
                valid_sources.append(pub)
        return valid_sources

    def _stream_completion(
        self,
        system_prompt: str,
        user_content: str,
        max_tokens: int = 8192,
        reasoning_budget: int = 1024,
        verbose: bool = False,
        max_retries: int = 4,
    ) -> str:
        messages = [
            {"role": "system", "content": f"<|think_low|>\n{system_prompt}"},
            {"role": "user", "content": user_content},
        ]

        for attempt in range(1, max_retries + 1):
            try:
                if not verbose:
                    resp = self.client.chat.completions.create(
                        model=self.config.synthesis_model_id,
                        temperature=self.config.synthesis_temperature,
                        max_tokens=max_tokens,
                        extra_body={"reasoning": {"max_tokens": reasoning_budget}},
                        messages=messages,
                    )
                    return (resp.choices[0].message.content or "").strip()

                stream_resp = self.client.chat.completions.create(
                    model=self.config.synthesis_model_id,
                    temperature=self.config.synthesis_temperature,
                    max_tokens=max_tokens,
                    extra_body={"reasoning": {"max_tokens": reasoning_budget}},
                    messages=messages,
                    stream=True,
                )

                content_chunks: list[str] = []
                in_thinking_mode = False

                for chunk in stream_resp:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta

                    reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
                    if reasoning:
                        if not in_thinking_mode:
                            console.print("\n[dim magenta]━━━ Agent Reasoning ━━━[/dim magenta]")
                            in_thinking_mode = True
                        print(f"\033[90m{reasoning}\033[0m", end="", flush=True)

                    content = delta.content or ""
                    if content:
                        if in_thinking_mode:
                            console.print("\n\n[bold green]━━━ Drafting Prose ━━━[/bold green]")
                            in_thinking_mode = False
                        print(content, end="", flush=True)
                        content_chunks.append(content)

                print("\n")
                result = "".join(content_chunks).strip()
                if not result:
                    raise APIError("Empty completion returned mid-stream", request=None)
                return result

            except (APIError, APIConnectionError, RateLimitError, APITimeoutError) as exc:
                wait_time = attempt * 5
                console.print(
                    f"\n[bold yellow]Upstream API error ({exc.__class__.__name__}): {exc}. "
                    f"Retrying ({attempt}/{max_retries}) in {wait_time}s...[/bold yellow]"
                )
                if attempt == max_retries:
                    raise
                time.sleep(wait_time)

    def synthesize_prose(
        self,
        topic_name: str,
        category: str,
        sources: list[PublicationSource],
        subtopics: list[str] | None = None,
        body_heading_prefix: str = "##",
        target_words: int = 950,
        reasoning_budget: int = 1024,
        max_tokens: int = 4096,
        verbose: bool = False,
    ) -> str:
        system_template = self.jinja_env.get_template("base.jinja2")
        system_prompt = system_template.render()

        cat_key = category.lower().strip()
        template_name = f"{cat_key}.jinja2"
        available_templates = self.jinja_env.list_templates()

        if template_name not in available_templates:
            template_name = "concept.jinja2"

        template = self.jinja_env.get_template(template_name)
        user_prompt = template.render(
            topic_name=topic_name,
            subtopics=subtopics or [],
            sources=sources,
            body_heading_prefix=body_heading_prefix,
            target_words=target_words,
        )

        return self._stream_completion(
            system_prompt=system_prompt,
            user_content=user_prompt,
            max_tokens=max_tokens,
            reasoning_budget=reasoning_budget,
            verbose=verbose,
        )

    def process_topic_file(
        self,
        topic_file: Path,
        execute: bool = False,
        verbose: bool = False,
        force: bool = False,
    ) -> tuple[str, bool, str]:
        raw_text = topic_file.read_text(encoding="utf-8")
        topic_name = topic_file.stem.replace("-", " ").title()

        fm, body = split_frontmatter(raw_text)
        category = self.parser.resolve_entity_category(fm, topic_name)

        fm["type"] = category
        fm["generated"] = True

        sources_map, has_subtopics = self.parser.extract_sources_structure(body, self.config.wiki_dir)
        if not sources_map:
            return raw_text, False, "No '## MBRAS Sources' section discovered"

        all_slugs = [slug for slugs in sources_map.values() for slug in slugs]
        verified_sources = self.get_valid_sources(all_slugs)

        is_monograph_fallback = False
        is_escalated_full_text = False

        # Single-source escalation check
        if len(verified_sources) == 1:
            single_src = verified_sources[0]
            raw_text_src = self.parser.resolve_raw_source_text(single_src.slug, self.config.wiki_dir)

            # For broad concept topics, a single brief note cannot support a top-level encyclopedic article
            if category == "concept" and (not raw_text_src or len(raw_text_src.strip()) < 15000):
                return (
                    raw_text,
                    False,
                    f"Concept topic '{topic_name}' has only a single brief source ({len(raw_text_src or '')} chars); requires multi-source evidence or monograph for stand-alone synthesis",
                )

            # Requires >= 10,000 raw chars for other categories (person, event, etc.)
            if raw_text_src and len(raw_text_src.strip()) >= 10000:
                single_src.summary = raw_text_src
                is_escalated_full_text = True
                console.print(
                    f"[cyan]Escalated single source '{single_src.title}' "
                    f"to full text ({len(raw_text_src)} chars)[/cyan]"
                )
            else:
                return (
                    raw_text,
                    False,
                    f"Single source '{single_src.title}' lacks sufficient length "
                    f"({len(raw_text_src or '')} chars, requires >= 10,000) for stand-alone synthesis",
                )

        elif len(verified_sources) >= 2:
            anchors, supp = self.reranker.prioritize_sources(
                query=f"{topic_name}: Historical and regional significance",
                sources=verified_sources,
                top_k=self.config.rerank_top_k,
            )
            top_anchor = anchors[0]
            raw_full = self.parser.resolve_raw_source_text(top_anchor.slug, self.config.wiki_dir)
            if raw_full and 1500 < len(raw_full.split()) < 40000:
                top_anchor.summary = raw_full
                is_escalated_full_text = True
                console.print(f"[cyan]Sliding Scale: Escalated top anchor '{top_anchor.title}' to full primary text.[/cyan]")

        # Cap generation sources to avoid context saturation
        if len(verified_sources) > 15:
            anchors, supp = self.reranker.prioritize_sources(
                query=f"{topic_name}: Comprehensive historical, regional, and thematic survey",
                sources=verified_sources,
                top_k=8,
            )
            generation_sources = anchors + supp[:4]
        elif len(verified_sources) >= 2:
            anchors, supp = self.reranker.prioritize_sources(
                query=f"{topic_name}: Historical and regional analysis",
                sources=verified_sources,
                top_k=self.config.rerank_top_k,
            )
            generation_sources = anchors + supp
        else:
            generation_sources = verified_sources

        # Split and preserve document sections
        mbras_split = re.split(r"(?m)^##\s+MBRAS Sources\b", body, maxsplit=1)
        if len(mbras_split) < 2:
            return raw_text, False, "Could not cleanly isolate ## MBRAS Sources"

        pre_mbras = mbras_split[0]
        mbras_content = "## MBRAS Sources" + mbras_split[1]
        mbras_block_clean = re.split(r"(?m)^##\s+References\b", mbras_content, maxsplit=1)[0].strip()

        qualified_subtopics = {
            subtopic: slugs
            for subtopic, slugs in sources_map.items()
            if subtopic != "_flat" and len(self.get_valid_sources(slugs)) >= self.MIN_SOURCES_PER_SUBTOPIC
        }

        is_macro = bool(
            fm.get("is_cluster") is True
            or len(verified_sources) > 12
            or bool(re.search(r"<!--\s*Synthesis engine:", pre_mbras))
        )

        reasoning_budget, max_tokens, target_words = self.calculate_dynamic_budgets(
            sources=generation_sources,
            subtopic_count=len(qualified_subtopics),
            is_monograph_fallback=is_monograph_fallback,
            is_escalated_full_text=is_escalated_full_text,
            is_macro_cluster=is_macro,
        )

        console.print(
            f"[dim]Dynamic Budgeting -> Scale: ~{target_words} words | "
            f"Reasoning: {reasoning_budget} tok | Max Tokens: {max_tokens} tok[/dim]"
        )

        # Dynamic heading prefix: H3 if document already contains structural H2s, otherwise H2
        has_existing_h2 = bool(re.search(r"(?m)^##\s+(?!MBRAS Sources\b|References\b)", pre_mbras))
        body_heading_prefix = "###" if has_existing_h2 else "##"

        if not execute:
            msg = f"Eligible for synthesis ({len(verified_sources)} sources, category: {category})"
            preview_body = (
                f"# {topic_name}\n\n"
                f"*[Dry-run: Single-pass narrative synthesis using {len(generation_sources)} sources (~{target_words} words)]*\n\n"
                f"{mbras_block_clean}\n"
            )
            return join_frontmatter(fm, preview_body), True, msg

        console.print(f"\n[cyan]Synthesizing narrative with {self.config.synthesis_model_id} ({category})...[/cyan]")

        subtopic_headings = list(qualified_subtopics.keys()) if len(qualified_subtopics) >= 2 else None
        raw_prose = self.synthesize_prose(
            topic_name=topic_name,
            category=category,
            sources=generation_sources,
            subtopics=subtopic_headings,
            body_heading_prefix=body_heading_prefix,
            target_words=target_words,
            reasoning_budget=reasoning_budget,
            max_tokens=max_tokens,
            verbose=verbose,
        )

        if not raw_prose.strip():
            return raw_text, False, "Model returned empty completion"

        # Demote headings to H3 only when the topic explicitly requires nested headings
        if body_heading_prefix == "###":
            raw_prose_formatted = re.sub(r"(?m)^##\s+", "### ", raw_prose)
        else:
            raw_prose_formatted = raw_prose

        # Re-index citations and construct the ## References block
        resolved_prose, ref_block, cited = process_numbered_citations(
            raw_prose_formatted, generation_sources
        )

        # Extract any pre-existing ## Members & Sub-Topics section
        members_block = ""
        members_match = re.search(
            r"(?m)(^##\s+Members & Sub-Topics\b.*?)(?=\n##\s+|\n###\s+|\Z)", 
            pre_mbras, 
            re.DOTALL
        )
        if members_match:
            members_block = members_match.group(1).strip()

        # Check for macro placeholders (e.g. folklore.md, malaya.md)
        top_intro_match = re.search(
            r"(<!--\s*Synthesis engine:\s*Insert introductory synthesis.*?-->)", 
            pre_mbras, 
            re.DOTALL
        )

        if top_intro_match:
            # Replace introductory marker with overview synthesis
            intro_placeholder = top_intro_match.group(1)
            updated_pre_mbras = pre_mbras.replace(intro_placeholder, resolved_prose.strip())
            
            # Clean residual empty section headings with unpopulated placeholder comments
            clean_scaffold = re.sub(
                r"(?m)^#{2,4}\s+[^\n]+\n+\s*<!--\s*Synthesis engine:[^>]*-->\n*", 
                "", 
                updated_pre_mbras
            )
            clean_scaffold = re.sub(r"<!--\s*Synthesis engine:[^>]*-->\n*", "", clean_scaffold).strip()
            new_body = f"{clean_scaffold}\n\n{mbras_block_clean}\n\n{ref_block}\n"

        elif members_block:
            # Place Members & Sub-Topics between the opening lede and thematic body
            lede_split = re.split(r"(?m)(?=^#{2,3}\s+)", resolved_prose.strip(), maxsplit=1)
            lede_prose = lede_split[0].strip()
            body_prose = lede_split[1].strip() if len(lede_split) > 1 else ""

            sections = [
                f"# {topic_name}",
                lede_prose,
                members_block,
                body_prose,
                mbras_block_clean,
                ref_block.strip()
            ]
            new_body = "\n\n".join(s for s in sections if s) + "\n"

        else:
            # Standard flat stub: replace with title, synthesis, and references
            sections = [
                f"# {topic_name}",
                resolved_prose.strip(),
                mbras_block_clean,
                ref_block.strip()
            ]
            new_body = "\n\n".join(s for s in sections if s) + "\n"

        return join_frontmatter(fm, new_body), True, f"Synthesized {category} entry with {len(cited)} citations"