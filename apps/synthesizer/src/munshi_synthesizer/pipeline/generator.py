from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from openai import OpenAI
from rich.console import Console

from munshi_synthesizer.config import SynthesizerConfig
from munshi_synthesizer.pipeline.metadata import MetadataResolver
from munshi_synthesizer.schema import GeneratedArticle, SynthesisPayload

console = Console()


class SynthesisGenerator:
    """Generates strictly-grounded OKF Markdown articles via Jinja templates and OpenRouter."""

    def __init__(self, config: SynthesizerConfig):
        self.config = config
        api_key = self.config.openrouter_api_key or "dry-run-placeholder"

        self.client = OpenAI(
            api_key=api_key,
            base_url=self.config.openrouter_base_url,
            timeout=240.0,
            default_headers={
                "HTTP-Referer": "https://github.com/munshi-project",
                "X-Title": "Munshi Synthesizer",
            },
        )

        # Initialize the metadata resolver pointing to the raw markdown directory
        self.metadata_resolver = MetadataResolver(self.config.zvec_data_dir)

        template_dir = Path(__file__).resolve().parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def _render_prompt(self, payload: SynthesisPayload) -> str:
        cat = payload.target.category
        template_name = f"{cat}.jinja2"

        if template_name not in self.jinja_env.list_templates():
            template_name = "concept.jinja2"

        template = self.jinja_env.get_template(template_name)
        return template.render(
            target=payload.target,
            occurrences=payload.occurrences,
            authority=payload.authority,
            custom_instructions=payload.custom_instructions,
            metadata_resolver=self.metadata_resolver,
        )

    def generate(
        self, payload: SynthesisPayload, log_dir: Path | None = None
    ) -> GeneratedArticle:
        prompt_content = self._render_prompt(payload)
        slug = re.sub(r"[^a-z0-9]+", "-", payload.target.canonical_name.lower()).strip("-")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            prompt_log_file = log_dir / f"{slug}_{timestamp}_prompt.md"
            prompt_log_file.write_text(prompt_content, encoding="utf-8")
            console.print(f"[dim]Saved prompt log to: {prompt_log_file}[/dim]")

        # Stream OpenRouter completion with bounded reasoning
        stream_resp = self.client.chat.completions.create(
            model=self.config.synthesis_model_id,
            temperature=self.config.synthesis_temperature,
            max_tokens=8192,
            extra_body={
                "reasoning": {
                    "max_tokens": 2048
                }
            },
            messages=[
                {"role": "user", "content": prompt_content},
            ],
            stream=True,
        )

        reasoning_chunks: list[str] = []
        content_chunks: list[str] = []
        in_thinking_mode = False

        console.print("[bold cyan]Connected to model stream...[/bold cyan]")

        for chunk in stream_resp:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # Capture thinking tokens
            reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
            if reasoning:
                if not in_thinking_mode:
                    console.print("\n[dim magenta]Thinking...[/dim magenta]\n", end="")
                    in_thinking_mode = True
                print(f"\033[90m{reasoning}\033[0m", end="", flush=True)
                reasoning_chunks.append(reasoning)

            # Capture synthesized markdown prose
            content = delta.content or ""
            if content:
                if in_thinking_mode:
                    console.print("\n\n[bold green]Generating Markdown Synthesis:[/bold green]\n")
                    in_thinking_mode = False
                content_chunks.append(content)
                print(content, end="", flush=True)

        print("\n")
        raw_reasoning = "".join(reasoning_chunks)
        raw_output = "".join(content_chunks)

        if log_dir:
            if raw_reasoning:
                reasoning_log_file = log_dir / f"{slug}_{timestamp}_reasoning.log"
                reasoning_log_file.write_text(raw_reasoning, encoding="utf-8")
                console.print(f"[dim]Saved reasoning log to: {reasoning_log_file}[/dim]")

            raw_resp_file = log_dir / f"{slug}_{timestamp}_response.md"
            raw_resp_file.write_text(raw_output, encoding="utf-8")

        doc_ids_referenced = list(set(occ.doc_id for occ in payload.occurrences))

        frontmatter = (
            f"---\n"
            f'title: "{payload.target.canonical_name}"\n'
            f'entity_id: "{payload.target.entity_id}"\n'
            f'category: "{payload.target.category}"\n'
            f'tier: "{payload.target.tier}"\n'
            f"mention_count: {payload.target.mention_count}\n"
            f"sources:\n"
            + "".join(f'  - "{doc}"\n' for doc in doc_ids_referenced)
            + f"---\n\n"
        )

        return GeneratedArticle(
            entity_id=payload.target.entity_id,
            slug=slug,
            markdown_content=frontmatter + raw_output.strip() + "\n",
            sources_referenced=doc_ids_referenced,
        )