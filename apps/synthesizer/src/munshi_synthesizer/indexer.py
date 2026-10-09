"""Sequential citation numbering, hyperlinking, and references compilation."""
from __future__ import annotations

import re
from munshi_synthesizer.schema import PublicationSource


def process_numbered_citations(
    generated_text: str,
    source_pool: list[PublicationSource],
) -> tuple[str, str, list[PublicationSource]]:
    """
    Scans generated text for citations:
      - Single: [1] or [1, p. 45] or [1, pp. 12-14]
      - Compound: [1, 2] or [10, 12, 16] or [1, p. 4; 2, p. 12]
    Re-indexes sequentially, converts to markdown links, and constructs the ## References block.
    """
    bracket_re = re.compile(r"\[([0-9][^\]]*?)\]")

    source_to_final_num: dict[int, int] = {}
    ordered_used_sources: list[PublicationSource] = []

    def _resolve_compound(match: re.Match) -> str:
        inner = match.group(1).strip()
        
        # Split multiple items separated by semicolon or comma (when followed by a number)
        items = re.split(r";|\s*,\s*(?=\d+)", inner)
        resolved_links: list[str] = []

        for item in items:
            item = item.strip().rstrip(".")
            m = re.match(r"^(\d+)(?:,\s*(pp?\.?\s*[\d\u2013\-,\s]+))?$", item)
            if not m:
                continue

            prompt_idx = int(m.group(1)) - 1
            page_info = m.group(2)

            if prompt_idx < 0 or prompt_idx >= len(source_pool):
                continue

            if prompt_idx not in source_to_final_num:
                assigned_num = len(source_to_final_num) + 1
                source_to_final_num[prompt_idx] = assigned_num
                ordered_used_sources.append(source_pool[prompt_idx])
            else:
                assigned_num = source_to_final_num[prompt_idx]

            label = f"{assigned_num}, {page_info}" if page_info else str(assigned_num)
            resolved_links.append(f"[[{label}]](#ref-{assigned_num})")

        return ", ".join(resolved_links) if resolved_links else match.group(0)

    resolved_body = bracket_re.sub(_resolve_compound, generated_text)

    # Build References block
    ref_lines: list[str] = ["## References\n"]
    for idx, src in enumerate(ordered_used_sources, 1):
        journal = f" {src.journal_citation}." if src.journal_citation else "."
        badge = f" {src.aggregator_badge}" if src.aggregator_badge else ""
        entry = (
            f'{idx}. <span id="ref-{idx}"></span> {src.author_display} ({src.year}). '
            f'[{src.title}](./{src.slug}.md){journal}{badge}'
        )
        ref_lines.append(entry)

    references_block = "\n".join(ref_lines)
    return resolved_body, references_block, ordered_used_sources