"""Pipeline step: detect and remove header/footer boilerplate."""

from __future__ import annotations

import logging
import re
from collections import Counter

from munshi_docproc.config import PipelineConfig
from munshi_docproc.schema import TextBlockRecord
from munshi_docproc.utils.geometry import is_in_zone
from munshi_docproc.utils.text import normalize_for_frequency

logger = logging.getLogger(__name__)

# Known platform headings that appear on cover pages (not real document content)
PLATFORM_HEADINGS = {"PROJECT MUSE", "JSTOR"}

# Standalone Arabic digits or Roman numerals with optional parentheses, brackets, or dots
PAGE_NUM_PATTERN = re.compile(r"^[\(\[]?\s*(?:[ivxlcdmIVXLCDM]+|\d{1,4})\s*[\)\]\.]?$")


def _is_running_header_candidate(block: TextBlockRecord, page_h: float, header_zone_bottom: float) -> bool:
    """Check whether a block sitting in the header zone looks like a running header."""
    if not is_in_zone(block.bbox, page_h, 0.0, header_zone_bottom):
        return False

    text = (block.text_clean or block.text_raw).strip()
    if not text:
        return False

    # Running headers are typically short (<= 10 words)
    words = text.split()
    if len(words) > 10:
        return False

    # Running headers rarely end with terminal sentence punctuation (. ! ?)
    # unless it's a period after an abbreviated word or page number
    if re.search(r"[!?:;]$", text):
        return False

    # Filter out multi-line narrative blocks that happen to touch the margin
    lines = text.splitlines()
    if len(lines) > 2:
        return False

    return True


def detect_boilerplate(
    blocks_by_page: dict[int, list[TextBlockRecord]],
    page_heights: dict[int, float],
    config: PipelineConfig,
) -> tuple[dict[int, list[TextBlockRecord]], list[TextBlockRecord]]:
    """Detect and remove header/footer boilerplate.

    Phase 1: classify blocks in header/footer zones by geometry.
    Phase 2: compute normalized-line frequencies, mark lines appearing
             on > threshold fraction of pages as boilerplate.
    Phase 3: detect chapter titles / running headers in the top zone that
             repeat across multiple consecutive pages.

    Returns:
        (filtered_blocks_by_page, removed_blocks)
    """
    total_pages = len(blocks_by_page)
    if total_pages == 0:
        return blocks_by_page, []

    # Phase 1: Classify blocks by zone
    for page_num, blocks in blocks_by_page.items():
        page_h = page_heights.get(page_num, 800.0)
        for block in blocks:
            if block.block_type in ("header", "footer"):
                continue  # Already classified by extraction stage
            if is_in_zone(block.bbox, page_h, 0.0, config.header_zone_bottom):
                block.block_type = "header"
            elif is_in_zone(block.bbox, page_h, config.footer_zone_top, 1.0):
                block.block_type = "footer"

    # Phase 2: Frequency-based boilerplate detection
    line_page_counts: Counter[str] = Counter()
    header_zone_candidates: Counter[str] = Counter()

    for page_num, blocks in blocks_by_page.items():
        page_h = page_heights.get(page_num, 800.0)
        page_lines: set[str] = set()

        for block in blocks:
            for line in block.text_clean.splitlines():
                normalized = normalize_for_frequency(line)
                if normalized and len(normalized) > 3:
                    page_lines.add(normalized)

            # Track candidates specifically located in the header zone
            if _is_running_header_candidate(block, page_h, config.header_zone_bottom):
                norm_header = normalize_for_frequency(block.text_clean)
                if norm_header:
                    header_zone_candidates[norm_header] += 1

        for line in page_lines:
            line_page_counts[line] += 1

    # Standard frequency threshold for whole-document lines (e.g. journal title on 30%+ pages)
    threshold = max(2, int(total_pages * config.boilerplate_threshold))
    boilerplate_lines = {line for line, count in line_page_counts.items() if count >= threshold}

    # Lower threshold (>= 2 pages) for candidate lines sitting strictly in the header margin.
    # This catches chapter titles that only appear on 3-10 pages within their specific chapter.
    running_chapter_headers = {line for line, count in header_zone_candidates.items() if count >= 2}

    if boilerplate_lines:
        logger.info(
            "Found %d boilerplate line patterns (threshold=%d/%d pages)",
            len(boilerplate_lines),
            threshold,
            total_pages,
        )

    # Mark and remove boilerplate blocks
    removed: list[TextBlockRecord] = []
    filtered: dict[int, list[TextBlockRecord]] = {}

    for page_num, blocks in blocks_by_page.items():
        kept: list[TextBlockRecord] = []
        page_h = page_heights.get(page_num, 800.0)

        boilerplate_flags: list[bool] = []
        for block in blocks:
            is_bp = False
            raw_text = block.text_clean.strip()

            # Check if block text matches document-wide boilerplate patterns
            for line in block.text_clean.splitlines():
                normalized = normalize_for_frequency(line)
                if normalized in boilerplate_lines:
                    is_bp = True
                    break

            # Remove known platform headings (e.g. "PROJECT MUSE®" on cover pages)
            if not is_bp:
                text_normalized = re.sub(r"[^\w\s]", "", raw_text).strip().upper()
                is_bp = text_normalized in {p.upper() for p in PLATFORM_HEADINGS}

            # Remove pre-classified header/footer zone blocks
            if block.block_type in ("header", "footer"):
                is_bp = True

            # Catch standalone Roman numeral and Arabic page numbers in margins
            if not is_bp:
                in_margin = (
                    is_in_zone(block.bbox, page_h, 0.0, config.header_zone_bottom)
                    or is_in_zone(block.bbox, page_h, config.footer_zone_top, 1.0)
                )
                if in_margin and PAGE_NUM_PATTERN.match(raw_text):
                    block.block_type = "page_number"
                    is_bp = True

            # Catch repeated chapter headings in the top zone
            if not is_bp and _is_running_header_candidate(block, page_h, config.header_zone_bottom):
                norm_cand = normalize_for_frequency(raw_text)
                if norm_cand in running_chapter_headers:
                    block.block_type = "header"
                    is_bp = True

            boilerplate_flags.append(is_bp)

        # Classify removed blocks by position
        first_content = next((i for i, bp in enumerate(boilerplate_flags) if not bp), len(blocks))
        last_content = next((i for i in range(len(blocks) - 1, -1, -1) if not boilerplate_flags[i]), -1)

        for idx, (block, is_boilerplate) in enumerate(zip(blocks, boilerplate_flags)):
            if is_boilerplate:
                if block.block_type not in ("header", "footer", "page_number"):
                    if idx <= first_content:
                        block.block_type = "header"
                    elif idx >= last_content:
                        block.block_type = "footer"
                removed.append(block)
            else:
                kept.append(block)

        filtered[page_num] = kept

    logger.info("Removed %d boilerplate blocks, kept %d", len(removed), sum(len(v) for v in filtered.values()))
    return filtered, removed