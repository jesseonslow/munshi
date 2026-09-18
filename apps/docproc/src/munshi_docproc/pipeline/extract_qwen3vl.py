"""Pipeline step: extract structured content via OpenRouter vision model."""
from __future__ import annotations

import base64
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import fitz
from openai import OpenAI

from munshi_docproc.config import PipelineConfig
from munshi_docproc.schema import BBox, TextBlockRecord
from munshi_docproc.utils.hashing import make_block_id, text_hash

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 5
MAX_IMAGE_BYTES = 3_700_000
JPEG_QUALITY = 85
DPI_FALLBACKS = (200, 150)


def _render_page_to_image_bytes(pdf_path: str, page_index: int, dpi: int) -> tuple[bytes, float, float]:
    """Render a PDF page to JPEG bytes, reducing DPI if needed to keep payload size optimal."""
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_index]
        page_width = page.rect.width
        page_height = page.rect.height
        for current_dpi in (dpi, *DPI_FALLBACKS):
            zoom = current_dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("jpeg", jpg_quality=JPEG_QUALITY)
            if len(img_bytes) <= MAX_IMAGE_BYTES:
                return img_bytes, page_width, page_height
        return img_bytes, page_width, page_height
    finally:
        doc.close()


def _call_openrouter(
    api_key: str,
    base_url: str,
    model_id: str,
    image_bytes: bytes,
    max_tokens: int,
    system_prompt: str,
) -> str:
    """Call OpenRouter OpenAI-compatible API with page image."""
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        default_headers={
            "HTTP-Referer": "https://github.com/munshi-docproc",
            "X-Title": "munshi-docproc",
        },
    )
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                            {"type": "text", "text": "Convert this page to Markdown following the system instructions."},
                        ],
                    },
                ],
                max_tokens=max_tokens,
                temperature=0.0,
            )
            text = response.choices[0].message.content or ""
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
            text = re.sub(r"^```(?:markdown)?\s*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
            return text
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise
            delay = RETRY_BASE_DELAY * (2**attempt)
            logger.warning("OpenRouter VLM call failed (attempt %d/%d), retrying in %ds: %s", attempt + 1, MAX_RETRIES, delay, e)
            time.sleep(delay)
    raise RuntimeError("unreachable")


def _parse_markdown_to_blocks(
    markdown: str,
    page_width: float,
    page_height: float,
    doc_id: str,
    page_num: int,
) -> tuple[list[TextBlockRecord], list[str]]:
    """Parse Markdown response into TextBlockRecords."""
    blocks: list[TextBlockRecord] = []
    figure_descriptions: list[str] = []
    full_bbox = BBox(x0=0, y0=0, x1=page_width, y1=page_height)

    parts = re.split(r"\n---+\n", markdown, maxsplit=1)
    main_text = parts[0]
    footnote_text = parts[1] if len(parts) > 1 else ""
    reading_order = 0

    for paragraph in re.split(r"\n{2,}", main_text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        fig_match = re.match(r"^!\[([^\]]*)\]\(([^)]*)\)\s*$", paragraph)
        if fig_match:
            desc = fig_match.group(2) or fig_match.group(1)
            if desc and not re.search(r"\bblank\b", desc, re.IGNORECASE):
                figure_descriptions.append(desc)
            continue

        if paragraph.startswith("#"):
            block_type = "heading"
            text = re.sub(r"^#+\s*", "", paragraph)
        elif paragraph.startswith(">"):
            block_type = "paragraph"
            text = re.sub(r"^>\s*", "", paragraph, flags=re.MULTILINE)
        elif re.match(r"^[-*]\s+", paragraph) or re.match(r"^\d+\.\s+", paragraph):
            block_type = "list_item"
            text = paragraph
        else:
            block_type = "paragraph"
            text = paragraph

        # Keep ^N as-is! (Do not convert to <sup>)
        if not text.strip():
            continue

        t_hash = text_hash(text)
        bbox_str = f"0.0,0.0,{page_width:.1f},{page_height:.1f}"
        block_id = make_block_id(doc_id, page_num, bbox_str, block_type, t_hash)
        blocks.append(
            TextBlockRecord(
                block_id=block_id,
                doc_id=doc_id,
                page_num_1=page_num,
                bbox=full_bbox,
                text_raw=text,
                block_type=block_type,
                reading_order=reading_order,
            )
        )
        reading_order += 1

    if footnote_text.strip():
        for line in footnote_text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # Keep line as-is! (Do not convert to <sup>)
            t_hash = text_hash(line)
            bbox_str = f"0.0,0.0,{page_width:.1f},{page_height:.1f}"
            block_id = make_block_id(doc_id, page_num, bbox_str, "footnote", t_hash)
            blocks.append(
                TextBlockRecord(
                    block_id=block_id,
                    doc_id=doc_id,
                    page_num_1=page_num,
                    bbox=full_bbox,
                    text_raw=line,
                    block_type="footnote",
                    reading_order=reading_order,
                )
            )
            reading_order += 1

    return blocks, figure_descriptions


def _process_page(
    config: PipelineConfig,
    doc_id: str,
    page_num: int,
    img_bytes: bytes,
    page_width: float,
    page_height: float,
) -> tuple[int, list[TextBlockRecord], list[str]]:
    """Call OpenRouter and parse response for a single page."""
    markdown = _call_openrouter(
        config.openrouter_api_key,
        config.openrouter_base_url,
        config.openrouter_ocr_model_id,
        img_bytes,
        config.qwen3vl_max_tokens,
        config.qwen3vl_system_prompt,
    )
    blocks, figure_descriptions = _parse_markdown_to_blocks(markdown, page_width, page_height, doc_id, page_num)
    return page_num, blocks, figure_descriptions


def extract_with_qwen3vl(
    config: PipelineConfig,
    doc_id: str,
) -> tuple[dict[int, list[TextBlockRecord]], dict[int, list[str]]]:
    """Extract structured text blocks from PDF using OpenRouter Vision Model."""
    logger.info("Running Vision extraction on %s (model=%s)", config.pdf_path.name, config.openrouter_ocr_model_id)
    pdf_path = str(config.pdf_path)
    page_range = config.parse_page_range()
    max_pages = config.max_pages

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    pages_to_process: list[int] = []
    for page_idx in range(total_pages):
        page_num = page_idx + 1
        if page_range is not None and page_idx not in page_range:
            continue
        if max_pages is not None and page_num > max_pages:
            break
        pages_to_process.append(page_num)

    t0 = time.time()
    rendered: dict[int, tuple[bytes, float, float]] = {}
    for page_num in pages_to_process:
        img_bytes, page_width, page_height = _render_page_to_image_bytes(pdf_path, page_num - 1, config.qwen3vl_dpi)
        rendered[page_num] = (img_bytes, page_width, page_height)

    logger.info("Rendered %d pages in %.1fs", len(rendered), time.time() - t0)

    t0 = time.time()
    blocks_by_page: dict[int, list[TextBlockRecord]] = {}
    figures_by_page: dict[int, list[str]] = {}

    with ThreadPoolExecutor(max_workers=config.qwen3vl_max_workers) as executor:
        futures = {
            executor.submit(_process_page, config, doc_id, page_num, *rendered[page_num]): page_num
            for page_num in pages_to_process
        }
        for future in as_completed(futures):
            page_num = futures[future]
            try:
                pn, blocks, fig_descs = future.result()
                if blocks:
                    blocks_by_page[pn] = blocks
                if fig_descs:
                    figures_by_page[pn] = fig_descs
                logger.info("Page %d complete — %d blocks, %d figures", pn, len(blocks), len(fig_descs))
            except Exception:
                logger.exception("Failed on page %d", page_num)

    logger.info("API calls completed in %.1fs (max_workers=%d)", time.time() - t0, config.qwen3vl_max_workers)
    return blocks_by_page, figures_by_page