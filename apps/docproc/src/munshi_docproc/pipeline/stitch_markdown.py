"""Pipeline step: compile structured docproc records into clean, anchored archival Markdown."""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from pathlib import Path

from munshi_docproc.schema import (
    DocumentRecord,
    FigureRecord,
    FootnoteRecord,
    FootnoteRefRecord,
    PlateRecord,
    TextBlockRecord,
)

logger = logging.getLogger(__name__)

CHAPTER_RE = re.compile(r"(?i)^(?:chapter|ch\.)\s+([ivxlcdm\d]+)(?:\s*[:.-]\s*(.*))?")
BACKMATTER_RE = re.compile(r"(?i)^(?:bibliography|references|index|glossary|appendi(?:x|ces))\b")


def _clean_yaml_val(val: str | int | float | None) -> str:
    if val is None:
        return '""'
    if isinstance(val, (int, float)):
        return str(val)
    return json.dumps(str(val))


def _build_frontmatter(doc: DocumentRecord, section_title: str | None = None) -> list[str]:
    lines = ["---"]
    lines.append(f"doc_id: {_clean_yaml_val(doc.doc_id)}")
    
    title = doc.title or "Unknown"
    if section_title:
        lines.append(f'title: "{title} — {section_title}"')
    else:
        lines.append(f"title: {_clean_yaml_val(title)}")

    lines.append(f"author: {_clean_yaml_val(doc.author or '')}")
    if doc.year:
        lines.append(f"year: {doc.year}")
    if doc.document_type:
        lines.append(f"document_type: {_clean_yaml_val(doc.document_type)}")
    lines.append("---\n")
    return lines


def _format_block(block: TextBlockRecord) -> str:
    text = (block.text_clean or block.text_raw).strip()
    if not text:
        return ""
    if block.block_type == "heading":
        raw = block.text_raw.strip()
        return raw if raw.startswith("#") else f"## {text}"
    elif block.block_type == "list_item":
        return text
    elif block.block_type == "caption":
        return f"> *{text}*"
    elif block.block_type == "blockquote":
        return "\n".join(f"> {line}" for line in text.splitlines())
    return text


def _detect_sections(blocks_by_page: dict[int, list[TextBlockRecord]]) -> list[dict]:
    """Identify page partitions for frontmatter, chapters, and backmatter."""
    sections = []
    current_sec = {"name": "frontmatter", "slug": "frontmatter", "start_page": 1, "title": "Front Matter"}
    
    all_pages = sorted(blocks_by_page.keys())
    ch_idx = 1

    for page_num in all_pages:
        for block in blocks_by_page[page_num]:
            if block.block_type == "heading":
                txt = (block.text_clean or block.text_raw).strip()
                ch_match = CHAPTER_RE.match(txt)
                bm_match = BACKMATTER_RE.match(txt)
                
                if ch_match:
                    sections.append(current_sec)
                    slug = f"chapter-{ch_idx:02d}"
                    subtitle = ch_match.group(2) or txt
                    current_sec = {"name": slug, "slug": slug, "start_page": page_num, "title": subtitle.strip()}
                    ch_idx += 1
                    break
                elif bm_match:
                    sections.append(current_sec)
                    slug = re.sub(r"[^a-z0-9]+", "-", bm_match.group(0).lower()).strip("-")
                    current_sec = {"name": slug, "slug": slug, "start_page": page_num, "title": txt}
                    break

    sections.append(current_sec)
    
    # Assign end_page bounds
    for i in range(len(sections) - 1):
        sections[i]["end_page"] = sections[i + 1]["start_page"] - 1
    sections[-1]["end_page"] = all_pages[-1] if all_pages else 1

    return sections


def _compile_section_markdown(
    section: dict,
    document: DocumentRecord,
    blocks_by_page: dict[int, list[TextBlockRecord]],
    fn_map: dict[str, str],
    refs_by_block: dict[str, list[FootnoteRefRecord]],
    figs_by_page: dict[int, list[FigureRecord]],
    plates_by_page: dict[int, list[PlateRecord]],
) -> str:
    """Compile Markdown text for a specific page range."""
    md_lines = _build_frontmatter(document, section.get("title"))
    doc_footnotes: list[str] = []
    footnote_id_to_num: dict[str, int] = {}
    rendered_figures: set[str] = set()

    for page_num in range(section["start_page"], section["end_page"] + 1):
        if page_num not in blocks_by_page:
            continue

        page_blocks = sorted(blocks_by_page[page_num], key=lambda b: b.reading_order)
        anchor_injected = False

        for block in page_blocks:
            text = (block.text_clean or block.text_raw).strip()

            # Resolve references within this section
            if block.block_id in refs_by_block:
                refs = sorted(refs_by_block[block.block_id], key=lambda r: r.footnote_number)
                for ref in refs:
                    f_id = ref.footnote_id
                    if not f_id or f_id not in fn_map:
                        continue

                    # Reset note numbers cleanly within this chapter scope
                    if f_id not in footnote_id_to_num:
                        assigned_num = len(footnote_id_to_num) + 1
                        footnote_id_to_num[f_id] = assigned_num
                        clean_fn = re.sub(r"^\d+[\s.)]+", "", fn_map[f_id]).strip()
                        doc_footnotes.append(f"[^{assigned_num}]: {clean_fn}")

                    num = footnote_id_to_num[f_id]
                    text = text.replace(f"[ref:{ref.footnote_number}]", f"[^{num}]")

            block.text_clean = text
            formatted = _format_block(block)

            if formatted:
                if not anchor_injected:
                    if block.block_type == "heading":
                        hashes, _, rest = formatted.partition(" ")
                        formatted = f'{hashes} <span id="page-{page_num}"></span> {rest}'
                    else:
                        formatted = f'<span id="page-{page_num}"></span> {formatted}'
                    anchor_injected = True
                md_lines.append(formatted)

        if not anchor_injected and (figs_by_page.get(page_num) or plates_by_page.get(page_num)):
            md_lines.append(f'<span id="page-{page_num}"></span>')

        # Plates and figures
        for plate in plates_by_page.get(page_num, []):
            label = plate.plate_label or "Plate"
            note = plate.plate_note_text_clean.strip()
            md_lines.append(f"### {label}")
            if note and note != label:
                md_lines.append(f"> *{note}*")

        for fig in figs_by_page.get(page_num, []):
            if fig.figure_id in rendered_figures:
                continue
            caption = (fig.caption_text_clean or fig.caption_text_raw or "Figure").strip()
            img_path = Path(fig.asset_jpg_path).name if fig.asset_jpg_path else Path(fig.asset_original_path or "").name
            if img_path:
                md_lines.append(f"![{caption}](assets/{img_path})")
            rendered_figures.add(fig.figure_id)

    if doc_footnotes:
        md_lines.append("---\n\n## References & Footnotes")
        md_lines.extend(f"{fn}" for fn in doc_footnotes)

    return "\n\n".join(line.strip() for line in md_lines if line.strip()) + "\n"


def stitch_source_markdown(
    doc_dir: Path,
    doc_id: str,
    document: DocumentRecord,
    blocks_by_page: dict[int, list[TextBlockRecord]],
    footnotes: list[FootnoteRecord],
    footnote_refs: list[FootnoteRefRecord],
    figures: list[FigureRecord],
    plates: list[PlateRecord],
) -> Path:
    """Stitch extracted records into anchored, full-text Markdown.
    
    If chapters are detected, emits a folder containing individual markdown files.
    Otherwise, writes a single {doc_id}.md file.
    """
    fn_map = {fn.footnote_id: (fn.text_clean or fn.text_raw) for fn in footnotes}
    refs_by_block = defaultdict(list)
    for ref in footnote_refs:
        refs_by_block[ref.parent_block_id].append(ref)

    figs_by_page = defaultdict(list)
    for fig in figures:
        figs_by_page[fig.page_num_1].append(fig)

    plates_by_page = defaultdict(list)
    for plate in plates:
        plates_by_page[plate.page_num_1].append(plate)

    sections = _detect_sections(blocks_by_page)

    # Multi-chapter split: write into a dedicated subdirectory
    if len(sections) > 1:
        sources_dir = doc_dir / doc_id
        sources_dir.mkdir(parents=True, exist_ok=True)

        for sec in sections:
            # Skip empty frontmatter if page ranges don't contain real text
            if sec["start_page"] > sec["end_page"]:
                continue
            content = _compile_section_markdown(
                sec, document, blocks_by_page, fn_map, refs_by_block, figs_by_page, plates_by_page
            )
            out_file = sources_dir / f"{sec['slug']}.md"
            out_file.write_text(content, encoding="utf-8")

        logger.info("Compiled multi-chapter Markdown to %s (%d sections)", sources_dir, len(sections))
        return sources_dir

    # Single-document fallback (journal articles, short items)
    single_sec = {"name": doc_id, "slug": doc_id, "start_page": min(blocks_by_page.keys(), default=1), "end_page": max(blocks_by_page.keys(), default=1)}
    content = _compile_section_markdown(single_sec, document, blocks_by_page, fn_map, refs_by_block, figs_by_page, plates_by_page)
    output_path = doc_dir / f"{doc_id}.md"
    output_path.write_text(content, encoding="utf-8")
    logger.info("Compiled source Markdown: %s", output_path)
    return output_path