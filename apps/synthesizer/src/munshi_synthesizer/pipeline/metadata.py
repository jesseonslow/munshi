from __future__ import annotations

import re
from pathlib import Path
import yaml
from pydantic import BaseModel


class DocMetadata(BaseModel):
    doc_id: str
    title: str = "Unknown Title"
    author: str = "Unknown Author"
    year: int | str = "n.d."
    journal_ref: str | None = None

    @property
    def citation_label(self) -> str:
        """Returns clean academic label: e.g., 'Cowan (1951)' or 'Swettenham (1906)'"""
        surname = self.author.split(",")[-1].strip().split()[-1] if self.author else "Anon"
        return f"{surname} ({self.year})"


class MetadataResolver:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._cache: dict[str, DocMetadata] = {}
        self._index_frontmatters()

    def _index_frontmatters(self) -> None:
        if not self.data_dir.exists():
            return

        for md_file in self.data_dir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
                if match:
                    data = yaml.safe_load(match.group(1)) or {}
                    doc_id = str(data.get("doc_id", md_file.stem))
                    meta = DocMetadata(
                        doc_id=doc_id,
                        title=data.get("title", md_file.stem),
                        author=data.get("author", "Unknown Author"),
                        year=data.get("year", "n.d."),
                        journal_ref=data.get("journal_ref"),
                    )
                    self._cache[doc_id] = meta
                    self._cache[md_file.stem] = meta
            except Exception:
                continue

    def get(self, doc_id: str) -> DocMetadata:
        return self._cache.get(
            doc_id,
            DocMetadata(doc_id=doc_id, title=doc_id, author="Unknown", year="n.d."),
        )