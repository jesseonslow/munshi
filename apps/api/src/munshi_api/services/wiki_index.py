"""In-memory cache for fast graph cross-referencing."""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any
import yaml

FM_SPLIT_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n(.*)$", re.DOTALL)


class WikiGraphIndex:
    _instance: WikiGraphIndex | None = None

    def __init__(self, wiki_dir: Path):
        self.wiki_dir = wiki_dir
        self.docs: dict[str, dict[str, Any]] = {}
        self.last_loaded: float = 0.0
        self.reload()

    @classmethod
    def get_instance(cls, wiki_dir: Path) -> WikiGraphIndex:
        if cls._instance is None or cls._instance.wiki_dir != wiki_dir:
            cls._instance = cls(wiki_dir)
        return cls._instance

    def reload(self) -> None:
        """Parses all wiki files into memory once (takes ~0.5s)."""
        t0 = time.perf_counter()
        loaded = {}
        if not self.wiki_dir.exists():
            self.docs = {}
            return

        for p in self.wiki_dir.glob("*.md"):
            try:
                raw = p.read_text(encoding="utf-8")
                m = FM_SPLIT_RE.match(raw)
                if not m:
                    continue
                fm_raw, body = m.group(1), m.group(2)
                fm = yaml.safe_load(fm_raw) or {}
                loaded[p.stem] = {
                    "slug": p.stem,
                    "path": p,
                    "fm": fm,
                    "body": body,
                }
            except Exception:
                continue

        self.docs = loaded
        self.last_loaded = time.perf_counter()

    def update_doc(self, slug: str, raw_text: str) -> None:
        """Incrementally updates a single document in cache after a mutation."""
        p = self.wiki_dir / f"{slug}.md"
        m = FM_SPLIT_RE.match(raw_text)
        if m:
            self.docs[slug] = {
                "slug": slug,
                "path": p,
                "fm": yaml.safe_load(m.group(1)) or {},
                "body": m.group(2),
            }