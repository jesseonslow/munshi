"""Safe frontmatter extraction and atomic file writing utilities."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any
import yaml


def read_wiki_page(file_path: Path) -> tuple[dict[str, Any], str]:
    """Splits a Markdown file into frontmatter dict and raw body text."""
    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) >= 3:
        fm = yaml.safe_load(parts[1]) or {}
        return fm, parts[2]
    return {}, content


def reset_to_stub_body(title: str) -> str:
    """Restores the canonical blank stub body without the injected summary."""
    return f"# {title}\n\n## References\n<!-- Grounded occurrences and citations -->\n"


def write_wiki_page_atomic(file_path: Path, frontmatter: dict[str, Any], body: str) -> None:
    """Safely updates frontmatter and atomic-swaps to disk."""
    dumped_yaml = yaml.dump(
        frontmatter,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()

    body_clean = body.lstrip("\r\n")
    serialized = f"---\n{dumped_yaml}\n---\n\n{body_clean}" if body_clean else f"---\n{dumped_yaml}\n---\n"

    temp_dir = file_path.parent
    with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
        tf.write(serialized)
        temp_name = tf.name

    os.replace(temp_name, file_path)


def apply_frontmatter_patch(
    file_path: Path,
    patch: dict[str, Any] | None = None,
    keys_to_remove: list[str] | None = None,
    reset_body: bool = False,
) -> dict[str, Any]:
    """Applies structured patch updates, key deletions, and optional body reset."""
    fm, body = read_wiki_page(file_path)

    if keys_to_remove:
        for k in keys_to_remove:
            fm.pop(k, None)

    # Defensively verify patch is a dict before updating
    if patch and isinstance(patch, dict):
        fm.update(patch)

    if reset_body:
        title = fm.get("title", file_path.stem)
        body = reset_to_stub_body(title)

    write_wiki_page_atomic(file_path, fm, body)
    return fm