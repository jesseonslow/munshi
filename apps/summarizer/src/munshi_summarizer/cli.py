"""CLI entrypoint for publication summarization."""
from __future__ import annotations

import asyncio
from pathlib import Path
import random
import click
from rich.console import Console

from munshi_summarizer.config import SummarizerConfig
from munshi_summarizer.summarizer import PublicationSummarizer

console = Console()


async def run_batch_async(
    engine: PublicationSummarizer,
    articles: list[Path],
    concurrency: int,
    force: bool,
    execute: bool,
) -> None:
    """Executes article summarization concurrently with graceful error containment."""
    semaphore = asyncio.Semaphore(concurrency)
    console.print(
        f"[bold cyan]Queueing {len(articles)} articles across {concurrency} async workers...[/bold cyan]\n"
    )

    tasks = [
        engine.process_wiki_article_async(
            wiki_path=f,
            semaphore=semaphore,
            force=force,
            execute=execute,
            stream_to_console=False,
        )
        for f in articles
    ]

    success, failed = 0, 0
    total = len(articles)

    for i, fut in enumerate(asyncio.as_completed(tasks), 1):
        try:
            ok = await fut
            if ok:
                success += 1
            console.print(
                f"[{i}/{total}] {'[green]PROCESSED[/green]' if ok else '[dim]SKIPPED[/dim]'}"
            )
        except Exception as e:
            console.print(f"[red]Failed during batch execution: {e}[/red]")
            failed += 1

    console.print(f"\n[bold green]Batch Complete:[/bold green] {success} succeeded, {failed} failed.")


@click.command()
@click.option("--target", "-t", type=str, help="Specific wiki article slug or file path")
@click.option("--all", "-a", "run_all", is_flag=True, help="Batch process all articles")
@click.option("--random", "-r", "run_random", is_flag=True, help="Pick a random unsummarized article for testing")
@click.option("--from-source", "-s", type=click.Path(exists=True, path_type=Path), help="Generate a new wiki page from source markdown")
@click.option("--force", "-f", is_flag=True, help="Re-summarize even if summarized: true")
@click.option("--model", "-m", type=str, help="Override default LLM model slug")
@click.option("--concurrency", "-c", type=int, default=6, help="Parallel worker concurrency for batch mode")
@click.option("--execute", is_flag=True, default=False, help="Perform live LLM API call")
def main(
    target: str | None,
    run_all: bool,
    run_random: bool,
    from_source: Path | None,
    force: bool,
    model: str | None,
    concurrency: int,
    execute: bool,
) -> None:
    """MBRAS Publication Summarizer CLI."""
    config = SummarizerConfig()
    if model:
        config.summarizer_model_id = model

    engine = PublicationSummarizer(config)

    # 1. Pipeline Append Mode: Create new wiki article from source file
    if from_source:
        engine.create_from_source(from_source, execute=execute)
        return

    # 2. Target Specific Article
    if target:
        wiki_file = Path(target)
        if not wiki_file.suffix:
            wiki_file = config.wiki_dir / f"{target}.md"
        if not wiki_file.exists():
            console.print(f"[red]Error: Article file '{wiki_file}' does not exist.[/red]")
            return
        asyncio.run(
            engine.process_wiki_article_async(
                wiki_file,
                semaphore=asyncio.Semaphore(1),
                force=force,
                execute=execute,
                stream_to_console=True,
            )
        )
        return

    # Collect eligible candidates: filter on type: article and article_type: article
    all_articles: list[Path] = []
    for f in config.wiki_dir.glob("*.md"):
      try:
          raw = f.read_text(encoding="utf-8")
          fm, _ = engine.split_frontmatter(raw)
          
          # 1. Strictly target your legacy type
          if fm.get("type") == "article":
              subtype = str(fm.get("article_type") or "article").lower()
              
              # 2. Exclude only non-summarizable formats
              if subtype not in {"obituary", "index", "book_review", "review", "bibliography"}:
                  is_done = fm.get("summarized") is True or fm.get("summarised") is True
                  if force or not is_done:
                      all_articles.append(f)
      except Exception:
          continue

    if not all_articles:
        console.print("[yellow]No unsummarized articles found matching criteria.[/yellow]")
        return

    # 3. Random Article Selection
    if run_random:
        chosen = random.choice(all_articles)
        console.print(f"[bold magenta]Randomly selected candidate:[/bold magenta] {chosen.name}")
        asyncio.run(
            engine.process_wiki_article_async(
                chosen,
                semaphore=asyncio.Semaphore(1),
                force=force,
                execute=execute,
                stream_to_console=True,
            )
        )
        return

    # 4. Batch Process All
    if run_all:
        asyncio.run(
            run_batch_async(
                engine=engine,
                articles=all_articles,
                concurrency=concurrency,
                force=force,
                execute=execute,
            )
        )
        return

    console.print("[yellow]No action specified. Use --target, --random, --all, or --from-source.[/yellow]")


if __name__ == "__main__":
    main()