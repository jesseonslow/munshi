from pathlib import Path
import warnings
import click
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# Suppress harmless upstream deprecation notices
warnings.filterwarnings("ignore", category=FutureWarning, module=r"torch\.jit\._script")
warnings.filterwarnings("ignore", category=UserWarning, module=r"huggingface_hub\.utils\._validators")

ROOT = Path(__file__).resolve().parents[4]
console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context):
    """GLiNER2 entity ledger & authority processing tool."""
    env_path = ROOT / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    if ctx.invoked_subcommand is None:
        ctx.invoke(sweep)


@main.command(name="build-authority")
@click.option(
    "--subject-index",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to subject index markdown (default: data/index.md)",
)
@click.option(
    "--author-index",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to contributor index markdown (default: data/authors.md)",
)
@click.option(
    "--out-file",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to output JSON (defaults to AUTHORITY_INDEX from .env)",
)
def build_authority(subject_index: Path | None, author_index: Path | None, out_file: Path | None):
    """Compile Index Malaysiana markdown files into canonical authority_index.json."""
    from .authority_builder import build_authority_catalog
    from .config import LedgerConfig

    cfg = LedgerConfig()

    src_subject = subject_index or (cfg.data_dir / "index-1878-2025-je-0083c6100c8f/index.md")
    src_author = author_index or (cfg.data_dir / "index-1878-2025-je-0083c6100c8f/authors.md")
    dest = out_file or cfg.authority_index_path

    console.print(f"[cyan]Compiling subject concepts from:[/] {src_subject}")
    if src_author.exists():
        console.print(f"[cyan]Merging contributor bibliographies from:[/] {src_author}")

    count = build_authority_catalog(src_subject, src_author, dest)
    console.print(f"[bold green]Successfully compiled {count} authority records to:[/] {dest.resolve()}")


@main.command(name="sweep")
@click.option("--data-dir", type=click.Path(exists=True, path_type=Path), default=None, help="Directory containing source markdown")
@click.option("--db-path", type=click.Path(path_type=Path), default=None, help="SQLite ledger database path")
@click.option("--zvec-path", type=click.Path(path_type=Path), default=None, help="Zvec index directory path")
def sweep(data_dir: Path | None, db_path: Path | None, zvec_path: Path | None):
    """Run GLiNER2 entity and relational tuplet extraction sweep."""
    from .config import LedgerConfig
    from .db import init_db, finalize_ledger_tiers, seed_authority_index
    from .parser import extract_paragraphs_by_page, clean_canonical_name, slugify
    from .extractor import Gliner2Extractor
    from .resolver import ZvecResolver

    cfg = LedgerConfig()

    target_data_dir = data_dir or cfg.data_dir
    target_db_path = db_path or cfg.ledger_db_path
    target_zvec_path = zvec_path or cfg.zvec_index_path

    console.rule("[bold blue]GLiNER2 Entity & Tuplet Sweep[/bold blue]")

    conn = init_db(target_db_path)
    extractor = Gliner2Extractor(model_name=cfg.gliner_model)
    resolver = ZvecResolver(target_zvec_path)

    # 1. Pre-seed authority entities & known aliases into SQLite
    authority_path = cfg.authority_index_path
    if authority_path.exists():
        seeded = seed_authority_index(conn, authority_path)
        console.print(f"[green]Seeded {seeded} authority records into database from {authority_path.resolve()}.[/green]")

    # 2. Build in-memory alias dictionary for O(1) matching
    cur = conn.execute("SELECT alias, entity_id FROM entity_aliases")
    alias_cache: dict[str, str] = {row[0].lower(): row[1] for row in cur.fetchall()}
    console.print(f"[green]Loaded {len(alias_cache)} known aliases into in-memory lookup cache.[/green]")

    console.print(f"[yellow]Data directory:[/] {target_data_dir.resolve()}")
    console.print(f"[yellow]Database path:[/]  {target_db_path.resolve()}")
    console.print(f"[yellow]Zvec index path:[/] {target_zvec_path.resolve()}")

    md_files = list(target_data_dir.rglob("*.md"))
    console.print(f"[yellow]Found markdown files:[/] {len(md_files)}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning corpus...", total=len(md_files))

        for md_path in md_files:
            doc_id = md_path.stem
            progress.update(task, description=f"Scanning [cyan]{doc_id}[/cyan]")

            paragraphs = extract_paragraphs_by_page(md_path)

            for p_num, paragraph in paragraphs:
                if len(paragraph.split()) > 220:
                    continue

                extracted = extractor.extract(paragraph)

                # Process Entities
                for ent in extracted["entities"]:
                    raw_clean = ent["text"].strip(" ,.:;'\"")
                    canonical = clean_canonical_name(raw_clean)
                    if not canonical:
                        continue

                    cat = ent.get("label", "concept")

                    # 1. Fast path: check in-memory alias cache (pre-seeded from authority index)
                    target_id = alias_cache.get(raw_clean.lower())

                    # 2. Slow path: fallback to Zvec semantic resolution or create new entity
                    if not target_id:
                        resolved_id = resolver.resolve_unmatched_entity(raw_clean, paragraph, cat, conn)
                        if resolved_id:
                            target_id = resolved_id
                        else:
                            target_id = f"{cat}:{slugify(canonical)}"
                            with conn:
                                conn.execute(
                                    "INSERT OR IGNORE INTO entities (entity_id, canonical_name, category, primary_slug) VALUES (?, ?, ?, ?)",
                                    (target_id, canonical, cat, slugify(canonical)),
                                )
                                conn.execute(
                                    "INSERT OR IGNORE INTO entity_aliases (alias, entity_id) VALUES (?, ?)",
                                    (raw_clean, target_id),
                                )
                        alias_cache[raw_clean.lower()] = target_id

                    # Record Occurrence
                    with conn:
                        conn.execute(
                            "INSERT INTO occurrences (entity_id, doc_id, page_num, context_paragraph) VALUES (?, ?, ?, ?)",
                            (target_id, doc_id, p_num, paragraph),
                        )

                # Process Relations / Tuplets
                for rel in extracted["relations"]:
                    with conn:
                        conn.execute(
                            """
                            INSERT INTO entity_tuplets (subject_id, predicate, raw_object_text, doc_id, page_num, evidence_text)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (rel["subject_id"], rel["predicate"], rel["object_text"], doc_id, p_num, paragraph),
                        )

            progress.advance(task)

    finalize_ledger_tiers(conn)
    console.print("[bold green]Sweep Complete![/bold green]")


if __name__ == "__main__":
    main()