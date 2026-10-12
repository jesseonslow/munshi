#!/usr/bin/env python3
"""Repairs heading levels, moves cluster lists, and removes residual boilerplate in generated files."""

from __future__ import annotations

import pathlib
import re
import yaml


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

    # 1. Clean residual boilerplate scaffolds and empty HTML comments
    pre_mbras_clean = re.sub(
        r"(?m)^##\s+[^\n]+\n+\s*<!--\s*Synthesis engine:[^>]*-->\n*",
        "",
        pre_mbras,
    )
    pre_mbras_clean = re.sub(r"<!--\s*Synthesis engine:[^>]*-->\n*", "", pre_mbras_clean).strip()

    # 2. Extract ## Members & Sub-Topics if present
    members_block = ""
    members_match = re.search(
        r"(?m)(^##\s+Members & Sub-Topics\b.*?)(?=\n##\s+|\n###\s+|\Z)",
        pre_mbras_clean,
        re.DOTALL,
    )
    if members_match:
        members_block = members_match.group(1).strip()
        pre_mbras_clean = pre_mbras_clean.replace(members_match.group(0), "").strip()

    # 3. Heading Normalisation:
    # If there are no structural H2 sections remaining in the body (excluding Title and References),
    # body sections should be H2 ('##'), not H3 ('###')
    has_structural_h2 = bool(
        re.search(
            r"(?m)^##\s+(?!Research and Documentation\b|Historiography and Sources\b|Legacy and Documentation\b)",
            re.sub(r"^#\s+[^\n]+\n*", "", pre_mbras_clean, count=1),
        )
    )

    if not has_structural_h2:
        # Promote internal ### headings to ##
        pre_mbras_clean = re.sub(r"(?m)^###\s+", "## ", pre_mbras_clean)

    # 4. Extract H1 Title and Lede
    title_match = re.match(r"^(#\s+[^\n]+\n*)(.*?)(?=\n##\s+|\n###\s+|\Z)", pre_mbras_clean, re.DOTALL)
    if title_match:
        header_part = title_match.group(1).strip()
        lede_part = title_match.group(2).strip()
        body_rest = pre_mbras_clean[title_match.end() :].strip()

        sections = [header_part]
        if lede_part:
            sections.append(lede_part)
        if members_block:
            sections.append(members_block)
        if body_rest:
            sections.append(body_rest)
    else:
        sections = [pre_mbras_clean]
        if members_block:
            sections.insert(1, members_block)

    sections.append(mbras_tail)
    new_body = "\n\n".join(s for s in sections if s).strip() + "\n"

    # Reassemble frontmatter and body
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

    print(f"\nScan complete. Repaired {updated_count} files out of {checked_count} checked.")


if __name__ == "__main__":
    main()