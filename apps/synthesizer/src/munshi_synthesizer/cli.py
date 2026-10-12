"""Command Line Interface for munshi-synthesizer."""
from __future__ import annotations

import random
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table

from munshi_synthesizer.config import SynthesizerConfig
from munshi_synthesizer.synthesizer import TopicSynthesizer

console = Console()


def _is_publication_or_stub(text: str) -> bool:
    """Detects whether a markdown file is an article/monograph rather than a topic concept."""
    header = text[:500].lower()
    return any(
        marker in header
        for marker in (
            "type: publication",
            "type: article",
            "type: monograph",
            "type: reprint",
            "publication_type:",
        )
    )


def _find_eligible_topic_files(
    synthesizer: TopicSynthesizer, wiki_dir: Path, force: bool = False
) -> list[Path]:
    """Finds ungenerated topic files with eligible on-disk MBRAS sources."""
    eligible: list[Path] = []
    for f in sorted(wiki_dir.glob("*.md")):
        try:
            raw_text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if "## MBRAS Sources" not in raw_text:
            continue

        if _is_publication_or_stub(raw_text):
            continue

        fm, body = synthesizer.split_frontmatter(raw_text)

        if fm.get("generated") is True and not force:
            continue

        sources_map, _ = synthesizer.extract_sources_structure(body)
        total_valid = {
            slug
            for slugs in sources_map.values()
            for slug in slugs
            if (wiki_dir / f"{slug}.md").is_file()
        }

        # Allow: >= 2 valid sources OR single source eligible for escalation/monograph
        if len(total_valid) >= 2:
            eligible.append(f)
        elif len(total_valid) == 1:
            single_slug = next(iter(total_valid))
            # Fast check if substantive text or primary source exists
            if synthesizer._resolve_raw_source_text(single_slug):
                eligible.append(f)
            else:
                pub_path = wiki_dir / f"{single_slug}.md"
                pub = synthesizer.parser.parse(pub_path)
                if pub and pub.summary and len(pub.summary.strip()) >= 500:
                    eligible.append(f)

    return eligible


@click.group()
def main() -> None:
    """Munshi Synthesizer CLI - Open Knowledge Format Topic Compiler."""
    pass


@main.command()
@click.argument("slug", required=False, default=None)
@click.option(
    "--random",
    "-r",
    "use_random",
    is_flag=True,
    default=False,
    help="Select and synthesize a random ungenerated topic file.",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Force re-synthesis even if 'generated: true' is already set.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Stream model reasoning and drafting live to the console.",
)
@click.option(
    "--wiki-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to wiki directory containing markdown pages.",
)
@click.option("--model", default=None, help="OpenRouter model identifier.")
@click.option("--execute", is_flag=True, default=False, help="Execute live API synthesis.")
def synthesize_topic(
    slug: str | None,
    use_random: bool,
    force: bool,
    verbose: bool,
    wiki_dir: Path | None,
    model: str | None,
    execute: bool,
) -> None:
    """Synthesizes a topic markdown page by slug or picks a random ungenerated candidate."""
    config = SynthesizerConfig()
    if wiki_dir:
        config.wiki_dir = wiki_dir
    if model:
        config.synthesis_model_id = model

    synthesizer = TopicSynthesizer(config)

    if not config.wiki_dir.exists():
        console.print(f"[bold red]Wiki directory '{config.wiki_dir}' does not exist.[/bold red]")
        return

    # Handle random selection
    if use_random:
        with console.status("[cyan]Scanning wiki for ungenerated topic candidates...[/cyan]"):
            candidates = _find_eligible_topic_files(synthesizer, config.wiki_dir, force=force)

        if not candidates:
            console.print("[yellow]No eligible, ungenerated topic candidates found.[/yellow]")
            return

        topic_file = random.choice(candidates)
        console.print(
            f"[bold magenta]Randomly selected ungenerated topic ({len(candidates)} remaining):[/bold magenta] {topic_file.name}"
        )
    elif slug:
        clean_slug = slug.removesuffix(".md")
        topic_file = config.wiki_dir / f"{clean_slug}.md"
        if not topic_file.exists():
            console.print(f"[bold red]Topic file '{topic_file}' not found.[/bold red]")
            return
        console.print(f"[bold cyan]Processing targeted topic page:[/bold cyan] {topic_file.name}")
    else:
        console.print("[yellow]Please supply a topic SLUG or use --random / -r to pick an ungenerated file.[/yellow]")
        return

    new_content, success, msg = synthesizer.process_topic_file(
        topic_file, execute=execute, verbose=verbose, force=force
    )

    if not success:
        console.print(f"[bold yellow]Skipped:[/bold yellow] {msg}")
        return

    if execute:
        topic_file.write_text(new_content, encoding="utf-8")
        console.print(f"\n[bold green]Successfully updated:[/bold green] {topic_file.name} - {msg}")
    else:
        console.print("\n[bold yellow]--- DRY RUN: OUTPUT PREVIEW ---[/bold yellow]")
        console.print(new_content[:1800] + "\n[dim]... [truncated][/dim]")
        console.print(f"\n[cyan]{msg}[/cyan]")
        console.print("\nAdd [bold]--execute[/bold] to run live completions and write changes.")


@main.command()
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Force re-synthesis even if already marked as generated.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Stream model reasoning and drafting live to console.",
)
@click.option(
    "--wiki-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to wiki directory containing markdown pages.",
)
@click.option("--model", default=None, help="OpenRouter model identifier.")
@click.option("--execute", is_flag=True, default=False, help="Execute live API synthesis.")
@click.option("--limit", type=int, default=None, help="Limit number of eligible files to process.")
@click.option("--shuffle/--no-shuffle", "shuffle_files", default=None, help="Randomize candidate evaluation order.")
@click.option("--seed", type=int, default=None, help="RNG seed for reproducible batch sampling.")
def batch(
    force: bool,
    verbose: bool,
    wiki_dir: Path | None,
    model: str | None,
    execute: bool,
    limit: int | None,
    shuffle_files: bool | None,
    seed: int | None,
) -> None:
    """Batch-synthesizes all eligible topic pages."""
    config = SynthesizerConfig()
    if wiki_dir:
        config.wiki_dir = wiki_dir
    if model:
        config.synthesis_model_id = model

    synthesizer = TopicSynthesizer(config)
    wiki_files = sorted(config.wiki_dir.glob("*.md"))

    should_shuffle = shuffle_files if shuffle_files is not None else (limit is not None)
    if should_shuffle:
        if seed is not None:
            random.seed(seed)
        random.shuffle(wiki_files)

    table = Table(title="Munshi Batch Synthesis Candidate Evaluation")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Detail", style="dim")

    processed = 0
    skipped = 0

    for f in wiki_files:
        try:
            raw_text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if "## MBRAS Sources" not in raw_text:
            continue

        if _is_publication_or_stub(raw_text):
            continue

        fm, _ = synthesizer.split_frontmatter(raw_text)
        if fm.get("generated") is True and not force:
            continue

        new_content, success, msg = synthesizer.process_topic_file(
            f, execute=execute, verbose=verbose, force=force
        )

        if success:
            processed += 1
            table.add_row(
                f.name,
                "[green]ELIGIBLE[/green]" if not execute else "[bold green]SYNTHESIZED[/bold green]",
                msg,
            )
            if execute:
                f.write_text(new_content, encoding="utf-8")
        else:
            skipped += 1
            table.add_row(f.name, "[yellow]SKIPPED[/yellow]", msg)

        if limit and processed >= limit:
            break

    if not verbose:
        console.print(table)
    console.print(
        f"\nCompleted. Evaluated files: [green]{processed} eligible[/green], [yellow]{skipped} skipped[/yellow]."
    )


if __name__ == "__main__":
    main()