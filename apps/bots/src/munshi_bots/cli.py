"""CLI entrypoint for Mat Munshi Wiki Bots."""
from __future__ import annotations

import os
from pathlib import Path
import click
from openai import OpenAI

from munshi_bots.bots.taxonomy import TaxonomyNormalizerBot
from munshi_bots.runner import WikiBotRunner

ROOT = Path(__file__).resolve().parents[3]
WIKI_DIR = ROOT / "wiki"
TRIAGE_DIR = ROOT / "triage"


@click.group()
def cli():
    """Munshi Wiki Bot Runner Suite."""
    pass


@cli.command("normalize-taxonomy")
@click.option("--limit", type=int, default=None, help="Limit number of pages to process.")
@click.option("--confidence", type=float, default=0.85, help="Confidence threshold to apply patch.")
@click.option("--model", type=str, default="google/gemini-2.5-flash", help="OpenRouter model name.")
@click.option("--execute", is_flag=True, default=False, help="Apply patches directly to disk.")
def normalize_taxonomy(limit: int | None, confidence: float, model: str, execute: bool):
    """Audits missing_type and normalizes publication taxonomy."""
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    )
    bot = TaxonomyNormalizerBot(client=client, model=model)
    runner = WikiBotRunner(
        wiki_dir=WIKI_DIR,
        triage_dir=TRIAGE_DIR,
        confidence_threshold=confidence
    )
    runner.run(bot=bot, limit=limit, dry_run=not execute)


if __name__ == "__main__":
    cli()