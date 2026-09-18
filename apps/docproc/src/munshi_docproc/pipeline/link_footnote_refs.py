"""Pipeline step: link in-body footnote references to footnote records."""

from __future__ import annotations

import logging
import re
from munshi_docproc.pipeline.extract_mupdf import MuPDFPageData
from munshi_docproc.schema import FootnoteRecord, FootnoteRefRecord, TextBlockRecord
from munshi_docproc.utils.hashing import make_block_id, text_hash

logger = logging.getLogger(__name__)

# Patterns targeting footnote markers
# Priority 1: Caret notation emitted by the VLM prompt
CARET_PATTERN = re.compile(r"\^(\d{1,3})")

# Priority 2: Fallback regexes for messy scans or parenthesized/bracketed styles
FALLBACK_PATTERNS = [
    (re.compile(r"([A-Za-z\)])(\d{1,2})(?=\s|[.,;:]|$)"), "regex_superscript"),
    (re.compile(r"([A-Za-z])\.(\d{1,2})(?=\s|[A-Z]|[.,;:]|$)"), "regex_period_superscript"),
    (re.compile(r"\(([1-9]\d{0,2})\)"), "regex_parens"),
    (re.compile(r"\[([1-9]\d{0,2})\]"), "regex_brackets"),
]


def link_footnote_refs(
    blocks_by_page: dict[int, list[TextBlockRecord]],
    footnotes: list[FootnoteRecord],
    mupdf_data: dict[int, MuPDFPageData],
    doc_id: str,
) -> list[FootnoteRefRecord]:
    """Scan body blocks for footnote reference markers and link to FootnoteRecords."""
    # Index footnotes by page and overall
    fn_index: dict[tuple[int, int], FootnoteRecord] = {}
    for fn in footnotes:
        fn_index[(fn.page_num_1, fn.footnote_number)] = fn

    fn_by_number: dict[int, FootnoteRecord] = {}
    for fn in footnotes:
        fn_by_number[fn.footnote_number] = fn

    all_fn_numbers = set(fn_by_number.keys())
    all_refs: list[FootnoteRefRecord] = []

    for page_num, blocks in blocks_by_page.items():
        page_fn_numbers = {fn.footnote_number for (pn, fn_num), fn in fn_index.items() if pn == page_num}
        body_blocks = [b for b in blocks if b.block_type not in ("footnote", "header", "footer")]

        for block in body_blocks:
            text = block.text_clean or block.text_raw

            # 1. Primary: Match ^N notation
            for m in CARET_PATTERN.finditer(text):
                num = int(m.group(1))
                if num in page_fn_numbers:
                    fn = fn_index.get((page_num, num))
                    match_type = "caret_superscript"
                elif num in all_fn_numbers:
                    fn = fn_by_number.get(num)
                    match_type = "caret_superscript_xpage"
                else:
                    continue

                ref_id = make_block_id(doc_id, page_num, f"ref-{block.block_id}", match_type, text_hash(str(num)))
                all_refs.append(
                    FootnoteRefRecord(
                        ref_id=ref_id,
                        doc_id=doc_id,
                        page_num_1=page_num,
                        parent_block_id=block.block_id,
                        footnote_number=num,
                        footnote_id=fn.footnote_id if fn else None,
                        match_type=match_type,
                        context_snippet=text[max(0, m.start() - 20):min(len(text), m.end() + 20)],
                    )
                )

            # 2. Secondary: Font-size superscript analysis via MuPDF
            mupdf_page = mupdf_data.get(page_num)
            if mupdf_page:
                _find_superscript_refs(
                    block,
                    mupdf_page,
                    page_fn_numbers,
                    all_fn_numbers,
                    fn_index,
                    fn_by_number,
                    page_num,
                    doc_id,
                    all_refs,
                )

            # 3. Tertiary: Fallback patterns (only if confirmed by a real footnote number)
            for pattern, match_type in FALLBACK_PATTERNS:
                for m in pattern.finditer(text):
                    target_group = 2 if "superscript" in match_type else 1
                    try:
                        num = int(m.group(target_group))
                    except (ValueError, IndexError):
                        continue

                    # Only register if this matches an actual extracted footnote
                    if num in page_fn_numbers:
                        fn = fn_index.get((page_num, num))
                        eff_match_type = match_type
                    elif num in all_fn_numbers:
                        fn = fn_by_number.get(num)
                        eff_match_type = match_type + "_xpage"
                    else:
                        continue

                    ref_id = make_block_id(doc_id, page_num, f"ref-{block.block_id}", eff_match_type, text_hash(str(num)))
                    all_refs.append(
                        FootnoteRefRecord(
                            ref_id=ref_id,
                            doc_id=doc_id,
                            page_num_1=page_num,
                            parent_block_id=block.block_id,
                            footnote_number=num,
                            footnote_id=fn.footnote_id if fn else None,
                            match_type=eff_match_type,
                            context_snippet=text[max(0, m.start() - 20):min(len(text), m.end() + 20)],
                        )
                    )

    # Deduplicate refs by (parent_block_id, footnote_number)
    seen: set[tuple[str, int]] = set()
    deduped: list[FootnoteRefRecord] = []
    for ref in all_refs:
        key = (ref.parent_block_id, ref.footnote_number)
        if key not in seen:
            seen.add(key)
            deduped.append(ref)

    logger.info("Linked %d footnote references", len(deduped))
    return deduped


def apply_ref_markup(
    blocks_by_page: dict[int, list[TextBlockRecord]],
    footnote_refs: list[FootnoteRefRecord],
) -> dict[int, list[TextBlockRecord]]:
    """Convert linked footnote numbers into standard [ref:N] tokens."""
    refs_by_block: dict[str, list[FootnoteRefRecord]] = {}
    for ref in footnote_refs:
        refs_by_block.setdefault(ref.parent_block_id, []).append(ref)

    if not refs_by_block:
        return blocks_by_page

    modified = 0
    for page_num, blocks in blocks_by_page.items():
        for block in blocks:
            block_refs = refs_by_block.get(block.block_id)
            if not block_refs:
                continue

            text = block.text_clean
            # Sort descending so replacements do not shift string offsets
            for ref in sorted(block_refs, key=lambda r: r.footnote_number, reverse=True):
                n_str = str(ref.footnote_number)
                target = f"[ref:{ref.footnote_number}]"

                # Replace ^N
                text = re.sub(rf"\^{n_str}\b", target, text)

                # Replace (N) or [N] if linked to this footnote
                if "parens" in ref.match_type:
                    text = re.sub(rf"\({n_str}\)", target, text)
                elif "brackets" in ref.match_type:
                    text = re.sub(rf"\[{n_str}\]", target, text)
                elif "period_superscript" in ref.match_type:
                    text = re.sub(rf"([A-Za-z])\.{n_str}\b", rf"\1 {target}", text)
                else:
                    text = re.sub(rf"([A-Za-z\)]){n_str}\b", rf"\1 {target}", text)

                modified += 1

            block.text_clean = text

    logger.info("Applied [ref:N] markup to %d locations", modified)
    return blocks_by_page


def _find_superscript_refs(
    block: TextBlockRecord,
    mupdf_page: MuPDFPageData,
    page_fn_numbers: set[int],
    all_fn_numbers: set[int],
    fn_index: dict[tuple[int, int], FootnoteRecord],
    fn_by_number: dict[int, FootnoteRecord],
    page_num: int,
    doc_id: str,
    all_refs: list[FootnoteRefRecord],
) -> None:
    """Identify physical superscript spans using font-size ratios from MuPDF."""
    if not mupdf_page.spans:
        return

    sizes = [s.font_size for s in mupdf_page.spans if s.font_size > 0]
    if not sizes:
        return

    sizes.sort()
    median_size = sizes[len(sizes) // 2]

    for span in mupdf_page.spans:
        # Must be smaller than 70% of standard body text size
        if span.font_size <= 0 or span.font_size >= 0.70 * median_size:
            continue

        raw_text = span.text.strip()
        if not raw_text.isdigit():
            continue

        num = int(raw_text)

        if num in page_fn_numbers:
            fn = fn_index.get((page_num, num))
            match_type = "superscript_span"
        elif num in all_fn_numbers:
            fn = fn_by_number.get(num)
            match_type = "superscript_span_xpage"
        else:
            continue

        # Check if span sits inside the block's vertical coordinates
        if block.bbox.y0 - 5 <= span.bbox.y0 and span.bbox.y1 <= block.bbox.y1 + 5:
            ref_id = make_block_id(doc_id, page_num, f"ss-{block.block_id}", match_type, text_hash(str(num)))
            all_refs.append(
                FootnoteRefRecord(
                    ref_id=ref_id,
                    doc_id=doc_id,
                    page_num_1=page_num,
                    parent_block_id=block.block_id,
                    footnote_number=num,
                    footnote_id=fn.footnote_id if fn else None,
                    match_type=match_type,
                    evidence_span_bbox=span.bbox,
                )
            )