import click
from rich.console import Console
from rich.table import Table
from munshi_api.config import ApiConfig
from munshi_api.services.graph_auditor import GraphAuditorEngine

console = Console()


@click.group()
def main():
    """Munshi API CLI Controller."""
    pass


@main.command("audit")
def audit():
    """Run full graph audit from terminal."""
    config = ApiConfig()
    engine = GraphAuditorEngine(config.wiki_dir, config.sources_dir)
    report = engine.run_health_audit()

    console.print(f"\n[bold green]Entities Scanned:[/bold green] {report.total_entities}")
    console.print(f"[bold red]Broken Link Hits:[/bold red] {report.broken_link_count}")
    console.print(f"[bold yellow]Split Author Clusters:[/bold yellow] {len(report.potential_split_authors)}\n")

    table = Table(title="Top Broken Link Targets")
    table.add_column("Missing Slug", style="cyan")
    table.add_column("Hits", style="magenta")
    table.add_column("Referenced In (Sample)", style="white")

    for item in report.broken_links[:15]:
        table.add_row(item.target_slug, str(item.hit_count), ", ".join(item.referenced_in[:2]))

    console.print(table)


@main.command("audit-sources")
def audit_sources():
    """Scan wiki articles for invalid or fragmented source paths."""
    config = ApiConfig()
    engine = GraphAuditorEngine(config.wiki_dir, config.sources_dir)
    mismatches = engine.audit_source_paths()

    console.print(f"\n[bold red]Source Path Mismatches Found:[/bold red] {len(mismatches)}\n")

    table = Table(title="Source Path Anomalies")
    table.add_column("Article Slug", style="cyan")
    table.add_column("Error Type", style="magenta")
    table.add_column("Diagnostic Detail", style="white")
    table.add_column("Suggested Target", style="green")

    for m in mismatches[:20]:
        table.add_row(
            m.wiki_slug,
            m.error_type,
            m.detail,
            m.suggested_source_path or "-",
        )

    console.print(table)


if __name__ == "__main__":
    main()