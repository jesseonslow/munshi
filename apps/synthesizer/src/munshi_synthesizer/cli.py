from __future__ import annotations

from pathlib import Path
import click
from rich.console import Console
from rich.table import Table

from munshi_synthesizer.config import SynthesizerConfig
from munshi_synthesizer.pipeline.aggregator import LedgerAggregator
from munshi_synthesizer.pipeline.authority import AuthorityResolver
from munshi_synthesizer.pipeline.generator import SynthesisGenerator
from munshi_synthesizer.schema import SynthesisPayload

console = Console()


@click.group()
def main() -> None:
    """Munshi Synthesizer CLI - Open Knowledge Format Wiki Compiler."""
    pass


@main.command()
@click.argument("target")
@click.option("--db-path", type=click.Path(path_type=Path), default=None, help="SQLite ledger path")
@click.option("--authority", type=click.Path(path_type=Path), default=None, help="Authority JSON path")
@click.option("--zvec-dir", type=click.Path(path_type=Path), default=None, help="Data directory with .zvec-grep index")
@click.option("--zvec-top-k", type=int, default=None, help="Max vector matches to retrieve")
@click.option("--no-zvec", is_flag=True, default=False, help="Disable parallel zvec-grep retrieval")
@click.option("--model", default=None, help="OpenRouter model slug")
@click.option(
    "--log",
    "enable_log",
    is_flag=True,
    default=False,
    help="Dump full prompt and reasoning stream to logs/ directory",
)
@click.option("--out-dir", type=click.Path(path_type=Path), default=None, help="Output folder")
@click.option("--execute", is_flag=True, default=False, help="Call OpenRouter API instead of dry run")
def synthesize(
    target: str,
    db_path: Path | None,
    authority: Path | None,
    zvec_dir: Path | None,
    zvec_top_k: int | None,
    no_zvec: bool,
    model: str | None,
    out_dir: Path | None,
    execute: bool,
    enable_log: bool,
) -> None:
    """Synthesizes a single entity wiki page by Name or ID."""
    config = SynthesizerConfig()
    if db_path:
        config.ledger_db_path = db_path
    if authority:
        config.authority_index_path = authority
    if zvec_dir:
        config.zvec_data_dir = zvec_dir
    if zvec_top_k:
        config.zvec_top_k = zvec_top_k
    if no_zvec:
        config.enable_zvec = False
    if model:
        config.synthesis_model_id = model
    if out_dir:
        config.wiki_out_dir = out_dir

    try:
        aggregator = LedgerAggregator(
            db_path=config.ledger_db_path,
            zvec_data_dir=config.zvec_data_dir,
            zvec_top_k=config.zvec_top_k,
            enable_zvec=config.enable_zvec,
        )
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return

    entity = aggregator.fetch_entity(target)
    if not entity:
        console.print(f"[bold red]Target '{target}' not found in ledger database.[/bold red]")
        return

    with console.status(f"[cyan]Aggregating evidence for '{entity.canonical_name}' (SQLite + zvec)...[/cyan]"):
        occurrences = aggregator.fetch_all_occurrences_parallel(entity)

    resolver = AuthorityResolver(config.authority_index_path)
    auth_data = resolver.resolve(entity.canonical_name)

    payload = SynthesisPayload(
        target=entity,
        occurrences=occurrences,
        authority=auth_data,
    )

    ledger_count = sum(1 for o in occurrences if o.source_type == "ledger")
    zvec_count = sum(1 for o in occurrences if o.source_type == "zvec_vector")

    console.print(f"[bold green]Target Found:[/bold green] {entity.canonical_name} ({entity.entity_id})")
    console.print(f"Category: {entity.category} | Tier: {entity.tier}")
    console.print(f"Evidence Collected: [cyan]{len(occurrences)} total[/cyan] ({ledger_count} ledger, {zvec_count} zvec semantic)")
    console.print(f"Authority Index Matched: {'Yes' if auth_data else 'No'}")

    generator = SynthesisGenerator(config)
    log_dir = Path("logs") if enable_log else None

    if not execute:
        console.print("\n[bold yellow]--- DRY RUN: PROMPT PREVIEW ---[/bold yellow]")
        rendered_prompt = generator._render_prompt(payload)
        console.print(f"[dim]{rendered_prompt[:1200]}...\n[truncated][/dim]")
        
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            slug = re.sub(r"[^a-z0-9]+", "-", entity.canonical_name.lower()).strip("-")
            dry_log_file = log_dir / f"{slug}_dry_run_prompt.md"
            dry_log_file.write_text(rendered_prompt, encoding="utf-8")
            console.print(f"\n[bold green]Saved dry-run prompt to:[/bold green] {dry_log_file}")
            
        console.print("\nTo trigger live synthesis with OpenRouter, add the [bold]--execute[/bold] flag.")
        return

    if not config.openrouter_api_key:
        console.print("[bold red]OPENROUTER_API_KEY is not set in environment or config.[/bold red]")
        return

    console.print(f"\n[bold cyan]Synthesizing with {config.synthesis_model_id}...[/bold cyan]")
    result = generator.generate(payload, log_dir=log_dir)

    config.wiki_out_dir.mkdir(parents=True, exist_ok=True)
    out_file = config.wiki_out_dir / f"{result.slug}.md"
    out_file.write_text(result.markdown_content, encoding="utf-8")
    console.print(f"[bold green]Successfully generated wiki article:[/bold green] {out_file}")

@main.command()
@click.option("--db-path", type=click.Path(path_type=Path), default=None)
def list_candidates(db_path: Path | None) -> None:
    """Lists curated or Tier A entities ready for synthesis."""
    config = SynthesizerConfig()
    if db_path:
        config.ledger_db_path = db_path

    try:
        aggregator = LedgerAggregator(config.ledger_db_path)
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return

    candidates = aggregator.list_curated_or_tier_a()
    table = Table(title=f"Synthesis Candidates in {config.ledger_db_path.name}")
    table.add_column("Entity ID", style="cyan")
    table.add_column("Canonical Name", style="white")
    table.add_column("Category", style="magenta")
    table.add_column("Tier", style="yellow")
    table.add_column("Mentions", justify="right")
    table.add_column("Curated", justify="center")

    for c in candidates[:50]:
        table.add_row(
            c.entity_id,
            c.canonical_name,
            c.category,
            c.tier,
            str(c.mention_count),
            "✓" if c.is_curated else "—",
        )

    console.print(table)


if __name__ == "__main__":
    main()