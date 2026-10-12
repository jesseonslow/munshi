#!/usr/bin/env python3
"""Repairs heading levels, removes body H1s, prunes orphaned headings,

and relocates cluster blocks in generated topic files.
"""

from __future__ import annotations

import pathlib
import re
import yaml


def prune_empty_headings(text: str) -> str:
    """Recursively removes headings (H2-H4) that have no body prose before

    the next heading or EOF.
    """
    pattern = re.compile(r"(?m)^#{2,4}\s+[^\n]+\s*(?=\n+#{2,4}\s+|\Z)")
    while True:
        cleaned = pattern.sub("", text).strip()
        if cleaned == text.strip():
            break
        text = cleaned
    return text


def repair_file(file_path: pathlib.Path) -> bool:
    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return False

    parts = content.split("---", 2)
    if len(parts) < 3:
        return False

    try:
        fm = yaml.safe_load(parts[1]) or {}
    except Exception:
        return False

    # Target only generated topic files
    if not fm.get("generated"):
        return False

    body = parts[2].strip()

    # Split body into pre-MBRAS content and MBRAS/References block
    mbras_split = re.split(r"(?m)^##\s+MBRAS Sources\b", body, maxsplit=1)
    if len(mbras_split) < 2:
        return False

    pre_mbras = mbras_split[0].strip()
    mbras_tail = "## MBRAS Sources\n\n" + mbras_split[1].strip()

    # 1. Clean synthesis comments and scaffolds
    pre_mbras_clean = re.sub(
        r"(?m)^##\s+[^\n]+\n+\s*<!--\s*(?:Synthesis engine|Summarizer):[^>]*-->\n*",
        "",
        pre_mbras,
    )
    pre_mbras_clean = re.sub(
        r"<!--\s*(?:Synthesis engine|Summarizer):[^>]*-->\n*", "", pre_mbras_clean
    ).strip()

    # 2. Strip any H1 titles from body prose
    pre_mbras_clean = re.sub(r"(?m)^#\s+[^\n]+\n*", "", pre_mbras_clean).strip()

    # 3. Extract ## Members & Sub-Topics if present
    members_block = ""
    members_match = re.search(
        r"(?m)(^##\s+Members & Sub-Topics\b.*?)(?=\n##\s+|\n###\s+|\Z)",
        pre_mbras_clean,
        re.DOTALL,
    )
    if members_match:
        members_block = members_match.group(1).strip()
        pre_mbras_clean = pre_mbras_clean.replace(members_match.group(0), "").strip()

    # 4. Prune orphaned headings (headers with no text beneath them)
    pre_mbras_clean = prune_empty_headings(pre_mbras_clean)

    # 5. Heading Normalisation:
    # Detect if any substantive H2 exists (excluding conclusion/meta headers)
    conclusion_headers = r"(Research and Documentation|Historiography and Sources|Legacy and Documentation)"
    substantive_h2_pattern = rf"(?m)^##\s+(?!{conclusion_headers}\b)[^\n]+"

    has_substantive_h2 = bool(re.search(substantive_h2_pattern, pre_mbras_clean))

    if not has_substantive_h2:
        # Flat stub: promote ### body headings to ##
        pre_mbras_clean = re.sub(r"(?m)^###\s+", "## ", pre_mbras_clean)

    # 6. Separate Lede from Body and splice ## Members & Sub-Topics
    # Find the first H2 or H3 heading
    first_heading_match = re.search(r"(?m)^#{2,3}\s+", pre_mbras_clean)
    if first_heading_match:
        lede_part = pre_mbras_clean[: first_heading_match.start()].strip()
        body_rest = pre_mbras_clean[first_heading_match.start() :].strip()

        sections = []
        if lede_part:
            sections.append(lede_part)
        if members_block:
            sections.append(members_block)
        if body_rest:
            sections.append(body_rest)
    else:
        # Document with no subheadings
        sections = [pre_mbras_clean]
        if members_block:
            sections.append(members_block)

    sections.append(mbras_tail)
    new_body = "\n\n".join(s for s in sections if s).strip() + "\n"

    rebuilt = f"---\n{parts[1].strip()}\n---\n\n{new_body}"
    if rebuilt != content:
        file_path.write_text(rebuilt, encoding="utf-8")
        return True

    return False


def main() -> None:
    wiki_dir = pathlib.Path("wiki")
    updated_count = 0
    checked_count = 0

    for path in sorted(wiki_dir.glob("*.md")):
        checked_count += 1
        if repair_file(path):
            updated_count += 1
            print(f"[REPAIRED] {path.name}")

    print(
        f"\nScan complete. Repaired {updated_count} files out of {checked_count} checked."
    )


if __name__ == "__main__":
    main()