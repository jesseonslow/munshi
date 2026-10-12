#!/usr/bin/env python3
"""
utils/wikify.py
High-throughput deterministic inline wikification using an in-memory Keyword Trie.
Leaves MBRAS Sources, References, and Bibliography blocks unlinked.
"""
from __future__ import annotations

import argparse
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any
import yaml
from flashtext import KeywordProcessor

REPO_ROOT = Path(__file__).resolve().parents[1]

def read_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    content = path.read_text(encoding="utf-8")
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            return fm, parts[2]
    return {}, content


def write_file_atomic(file_path: Path, frontmatter: dict[str, Any], body: str) -> None:
    dumped_yaml = yaml.dump(
        frontmatter,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()

    body_clean = body.lstrip("\r\n")
    serialized = f"---\n{dumped_yaml}\n---\n\n{body_clean}" if body_clean else f"---\n{dumped_yaml}\n---\n"

    with tempfile.NamedTemporaryFile("w", dir=file_path.parent, delete=False, encoding="utf-8") as tf:
        tf.write(serialized)
        temp_name = tf.name

    os.replace(temp_name, file_path)


def build_keyword_processor(wiki_dir: Path) -> KeywordProcessor:
    """Loads all titles and aliases into a single-pass Aho-Corasick / FlashText trie."""
    kp = KeywordProcessor(case_sensitive=False)

    for md_path in wiki_dir.glob("*.md"):
        try:
            fm, _ = read_frontmatter(md_path)
            slug = md_path.stem
            
            title = str(fm.get("title") or slug.replace("-", " ")).strip()
            if len(title) >= 4 and title.lower() not in GENERIC_CONCEPT_BLACKLIST:
                kp.add_keyword(title, (title, slug))

            aliases = fm.get("aliases") or []
            if isinstance(aliases, str):
                aliases = [aliases]
            for a in aliases:
                clean_a = str(a).strip()
                if len(clean_a) >= 4 and clean_a.lower() not in GENERIC_CONCEPT_BLACKLIST:
                    kp.add_keyword(clean_a, (clean_a, slug))
        except Exception:
            continue

    return kp


def wikify_body(body: str, kp: KeywordProcessor, current_slug: str) -> tuple[str, list[tuple[str, str]]]:
    """Single-pass token scan per block with deterministic boundary checking."""
    blocks = body.split("\n\n")
    new_blocks = []
    already_linked: set[str] = {current_slug}
    injected: list[tuple[str, str]] = []

    for block in blocks:
        stripped = block.strip()
        
        # Stop processing upon reaching bibliography, sources, or reference sections
        if stripped.startswith(("## MBRAS Sources", "## References", "## Bibliography")):
            new_blocks.append(block)
            new_blocks.extend(blocks[len(new_blocks):])
            break

        # Guard headers, image tags, citation anchors
        if stripped.startswith(("#", "!", "<span", "<!--", ">")):
            new_blocks.append(block)
            continue

        matches = kp.extract_keywords(block, span_info=True)
        if not matches:
            new_blocks.append(block)
            continue

        matches_sorted = sorted(matches, key=lambda m: m[1], reverse=True)

        for payload, start, end in matches_sorted:
            matched_surface_text, target_slug = payload

            if target_slug in already_linked:
                continue

            preceding_text = block[:start]
            following_text = block[end:]
            
            last_open_bracket = preceding_text.rfind("[")
            last_close_bracket = preceding_text.rfind("]")
            if last_open_bracket > last_close_bracket:
                continue

            last_open_paren = preceding_text.rfind("(")
            last_close_paren = preceding_text.rfind(")")
            if last_open_paren > last_close_paren:
                continue

            if following_text.startswith("](") or following_text.startswith("]"):
                continue

            actual_text = block[start:end]
            replacement = f"[{actual_text}](./{target_slug}.md)"
            block = block[:start] + replacement + block[end:]
            
            already_linked.add(target_slug)
            injected.append((actual_text, target_slug))

        new_blocks.append(block)

    return "\n\n".join(new_blocks), injected


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic high-throughput inline wikification.")
    parser.add_argument(
        "--wiki-dir",
        type=Path,
        default=REPO_ROOT / "wiki",
        help="Path to the flat wiki directory",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply modifications in-place to files on disk.",
    )
    args = parser.parse_args()

    wiki_dir: Path = args.wiki_dir.resolve()
    if not wiki_dir.exists():
        print(f"Error: Wiki directory '{wiki_dir}' does not exist.")
        return

    t0 = time.perf_counter()
    print("Building in-memory Trie processor...")
    kp = build_keyword_processor(wiki_dir)
    print(f"Trie constructed in {time.perf_counter() - t0:.2f}s.")

    files = sorted(list(wiki_dir.glob("*.md")))
    total_injected = 0
    modified_files = 0

    print(f"Scanning {len(files)} files ({'EXECUTE' if args.execute else 'DRY RUN'})...\n")

    t1 = time.perf_counter()
    for f in files:
        fm, body = read_frontmatter(f)
        new_body, links = wikify_body(body, kp, f.stem)

        if links:
            total_injected += len(links)
            modified_files += 1
            if args.execute:
                write_file_atomic(f, fm, new_body)

    elapsed = time.perf_counter() - t1
    print("=" * 50)
    print(f"Mode            : {'EXECUTE' if args.execute else 'DRY RUN'}")
    print(f"Files Modified  : {modified_files} / {len(files)}")
    print(f"Links Injected  : {total_injected}")
    print(f"Sweep Completed : {elapsed:.2f} seconds ({len(files)/elapsed:.1f} files/sec)")
    print("=" * 50)


if __name__ == "__main__":
    main()