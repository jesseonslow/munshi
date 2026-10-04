"""Master Number Registry resolver for JSBRAS and JMBRAS journals."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ROW_RE = re.compile(
    r"^\|\s*\*{0,2}(?P<master>\d+)\*{0,2}\s*\|\s*(?P<series>[A-Z]+)\s*\|\s*(?P<volume>[^|]+?)\s*\|\s*(?P<issue>[^|]+?)\s*\|",
    re.MULTILINE,
)
FILENAME_MASTER_RE = re.compile(
    r"\b(?:jmbras|jsbras|sbras|jmalayanbras)[-_](?P<master>\d+)[-_]",
    re.IGNORECASE,
)


class JournalRegistry:
    _instance: JournalRegistry | None = None

    def __init__(self, wiki_dir: Path):
        self.wiki_dir = wiki_dir
        # Maps (series_code, volume_str, issue_str) -> master_no
        self.vol_issue_to_master: dict[tuple[str, str, str], int] = {}
        # Maps master_no -> (series, volume, issue)
        self.master_to_meta: dict[int, dict[str, str]] = {}
        self._load_registry()

    @classmethod
    def get_instance(cls, wiki_dir: Path) -> JournalRegistry:
        if cls._instance is None or cls._instance.wiki_dir != wiki_dir:
            cls._instance = cls(wiki_dir)
        return cls._instance

    def _clean_field(self, val: str) -> str:
        val = val.strip().replace("—", "").replace("-", "")
        return val.strip()

    def _load_registry(self) -> None:
        registry_file = (
            self.wiki_dir / "journal-of-the-malaysian-branch-of-the-royal-asiatic-society.md"
        )
        if not registry_file.exists():
            return

        text = registry_file.read_text(encoding="utf-8")
        for m in ROW_RE.finditer(text):
            try:
                master = int(m.group("master"))
                series = m.group("series").strip().upper()  # 'SB' or 'MB'
                vol = self._clean_field(m.group("volume"))
                issue = self._clean_field(m.group("issue"))

                self.master_to_meta[master] = {
                    "series": series,
                    "volume": vol,
                    "issue": issue,
                }
                if vol:
                    # Index with exact issue
                    self.vol_issue_to_master[(series, vol, issue)] = master
                    # Index with wildcard/empty issue
                    self.vol_issue_to_master[(series, vol, "")] = master
            except Exception:
                continue

    def extract_master_from_filename(self, filename: str) -> int | None:
        """Extracts Master No. from 'jmbras-207-alattas-...' -> 207."""
        m = FILENAME_MASTER_RE.search(filename)
        if m:
            return int(m.group("master"))
        return None

    def matches_coordinates(
        self,
        filename: str,
        series: str,
        volume: str | int | None,
        issue: str | int | None = None,
    ) -> bool:
        """
        Validates if filename's Master No corresponds to the declared volume/issue.
        """
        file_master = self.extract_master_from_filename(filename)
        if not file_master:
            return False

        meta = self.master_to_meta.get(file_master)
        if not meta:
            return False

        vol_str = str(volume or "").strip()
        issue_str = str(issue or "").strip()

        # If volume matches, it's the authentic issue!
        if vol_str and meta["volume"] == vol_str:
            if not issue_str or not meta["issue"] or meta["issue"] == issue_str:
                return True

        return False