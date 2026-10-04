"""CLI entrypoint for publication summarization."""
from __future__ import annotations

from pathlib import Path
import random
import click
from rich.console import Console

from munshi_summarizer.config import SummarizerConfig
from munshi_summarizer.summarizer import PublicationSummarizer

console = Console()


@click.command()
@click.option("--target", "-t", type=str, help="Specific wiki article slug or file path")
@click.option("--all", "-a", "run_all", is_flag=True, help="Batch process all articles")
@click.option("--random", "-r", "run_random", is_flag=True, help="Pick a random unsummarized article for testing")
@click.option("--from-source", "-s", type=click.Path(exists=True, path_type=Path), help="Generate a new wiki page from source markdown")
@click.option("--force", "-f", is_flag=True, help="Re-summarize even if summarized: true")
@click.option("--model", "-m", type=str, help="Override default LLM model slug")
@click.option("--execute", is_flag=True, default=False, help="Perform live LLM API call")
def main(
    target: str | None,
    run_all: bool,
    run_random: bool,
    from_source: Path | None,
    force: bool,
    model: str | None,
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
        engine.process_wiki_article(wiki_file, force=force, execute=execute)
        return

    # Collect eligible candidates: filter on type: article and article_type: article
    all_articles: list[Path] = []
    for f in config.wiki_dir.glob("*.md"):
        try:
            raw = f.read_text(encoding="utf-8")
            fm, _ = engine.split_frontmatter(raw)
            if fm.get("type") == "article":
                # Only target substantive articles (skipping obituaries, book reviews, etc.)
                if fm.get("article_type", "article").lower() == "article":
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
        engine.process_wiki_article(chosen, force=force, execute=execute)
        return

    # 4. Batch Process All
    if run_all:
        console.print(f"[bold cyan]Starting batch run on {len(all_articles)} articles...[/bold cyan]")
        success, failed = 0, 0
        for f in all_articles:
            try:
                ok = engine.process_wiki_article(f, force=force, execute=execute)
                if ok:
                    success += 1
            except Exception as e:
                console.print(f"[red]Failed processing {f.name}: {e}[/red]")
                failed += 1
        console.print(f"\n[bold green]Batch Complete:[/bold green] {success} succeeded, {failed} failed.")
        return

    console.print("[yellow]No action specified. Use --target, --random, --all, or --from-source.[/yellow]")


if __name__ == "__main__":
    main()