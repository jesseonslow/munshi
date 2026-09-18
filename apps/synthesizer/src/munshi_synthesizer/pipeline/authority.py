from __future__ import annotations

import json
from pathlib import Path
from munshi_synthesizer.schema import AuthorityRecord


class AuthorityResolver:
    """Loads and resolves entities against the compiled Index Malaysiana authority."""

    def __init__(self, authority_json_path: Path):
        self.authority_path = authority_json_path
        self._index_by_name: dict[str, AuthorityRecord] = {}
        self._index_by_alias: dict[str, AuthorityRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.authority_path.exists():
            return

        with open(self.authority_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            record = AuthorityRecord(**item)
            self._index_by_name[record.canonical_name.strip().lower()] = record
            for alias in record.aliases:
                self._index_by_alias[alias.strip().lower()] = record

    def resolve(self, name_or_alias: str) -> AuthorityRecord | None:
        """Finds matching authority data for an entity."""
        clean = name_or_alias.strip().lower()
        if clean in self._index_by_name:
            return self._index_by_name[clean]
        if clean in self._index_by_alias:
            return self._index_by_alias[clean]
        return None