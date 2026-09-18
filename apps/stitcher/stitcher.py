#!/usr/bin/env python3
"""Batch stitch JSONL document folders into clean, anchored Markdown using stitch_markdown.py."""

from __future__ import annotations

import argparse
import json
import logging
import re
from collections import defaultdict
from pathlib import Path

# Adjust this import to match your package structure
from munshi_docproc.pipeline.stitch_markdown import stitch_source_markdown
from munshi_docproc.schema import (
    DocumentRecord,
    FigureRecord,
    FootnoteRecord,
    FootnoteRefRecord,
    PlateRecord,
    TextBlockRecord,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_latest_version_path(path: Path) -> Path:
    """Detects and returns the latest vX folder if present, else returns original path."""
    versions = []
    if not path.is_dir():
        return path

    for item in path.iterdir():
        if item.is_dir():
            match = re.match(r"^v(\d+)$", item.name)
            if match:
                versions.append((int(match.group(1)), item))

    if versions:
        versions.sort(key=lambda x: x[0])
        return versions[-1][1]

    return path


def load_records_from_folder(folder: Path):
    """Deserialize JSONL files into their respective Pydantic record types."""
    # 1. Document Record
    doc_path = folder / "documents.jsonl"
    if not doc_path.exists():
        return None

    document: DocumentRecord | None = None
    with open(doc_path, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
        if first_line:
            document = DocumentRecord.model_validate_json(first_line)

    if not document:
        return None

    # 2. Text Blocks
    blocks_by_page: dict[int, list[TextBlockRecord]] = defaultdict(list)
    blocks_path = folder / "text_blocks.jsonl"
    if blocks_path.exists():
        with open(blocks_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = TextBlockRecord.model_validate_json(line)
                    blocks_by_page[rec.page_num_1].append(rec)

    # 3. Footnotes
    footnotes: list[FootnoteRecord] = []
    fn_path = folder / "footnotes.jsonl"
    if fn_path.exists():
        with open(fn_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    footnotes.append(FootnoteRecord.model_validate_json(line))

    # 4. Footnote Refs
    footnote_refs: list[FootnoteRefRecord] = []
    refs_path = folder / "footnote_refs.jsonl"
    if refs_path.exists():
        with open(refs_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    footnote_refs.append(FootnoteRefRecord.model_validate_json(line))

    # 5. Figures
    figures: list[FigureRecord] = []
    figs_path = folder / "figures.jsonl"
    if figs_path.exists():
        with open(figs_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    figures.append(FigureRecord.model_validate_json(line))

    # 6. Plates
    plates: list[PlateRecord] = []
    plates_path = folder / "plates.jsonl"
    if plates_path.exists():
        with open(plates_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    plates.append(PlateRecord.model_validate_json(line))

    return document, blocks_by_page, footnotes, footnote_refs, figures, plates


def process_single_folder(target_dir: Path, output_dir: Path):
    """Processes a resolved folder containing docproc JSONL files."""
    data = load_records_from_folder(target_dir)
    if not data:
        logger.warning("Skipping %s (missing or invalid records)", target_dir)
        return False

    document, blocks_by_page, footnotes, footnote_refs, figures, plates = data
    doc_id = document.doc_id

    # Run the existing pipeline stitcher
    output_dir.mkdir(parents=True, exist_ok=True)
    stitch_source_markdown(
        doc_dir=output_dir,
        doc_id=doc_id,
        document=document,
        blocks_by_page=blocks_by_page,
        footnotes=footnotes,
        footnote_refs=footnote_refs,
        figures=figures,
        plates=plates,
    )
    return True


def main():
    parser = argparse.ArgumentParser(description="Batch stitch JSONL folders to Markdown.")
    parser.add_argument("input_path", type=Path, help="Base JSONL directory or single document folder.")
    parser.add_argument("--output", type=Path, default=Path("compiled_sources"), help="Output directory.")
    args = parser.parse_args()

    input_path: Path = args.input_path
    output_dir: Path = args.output

    if not input_path.exists():
        logger.error("Path does not exist: %s", input_path)
        return

    # Case 1: Single folder passed directly (or versioned folder)
    target_folder = get_latest_version_path(input_path)
    if (target_folder / "documents.jsonl").exists():
        process_single_folder(target_folder, output_dir)
        return

    # Case 2: Parent directory containing multiple document folders
    count = 0
    for child in sorted(input_path.iterdir()):
        if child.is_dir():
            doc_folder = get_latest_version_path(child)
            if (doc_folder / "documents.jsonl").exists():
                logger.info("Processing: %s", child.name)
                if process_single_folder(doc_folder, output_dir):
                    count += 1

    logger.info("Batch stitching complete. Successfully compiled %d document(s).", count)


if __name__ == "__main__":
    main()