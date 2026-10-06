"""Source alignment service integrating coordinate heuristics and Laya arbitration."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
import yaml
from munshi_api.models.sources import SourceValidationReport

PAGE_HEADER_RE = re.compile(r"\bpp?\.?\s*(\d+)(?:[-–—\s]+(\d+))?", re.IGNORECASE)
VOL_HEADER_RE = re.compile(r"\b(?:vol|volume|no|number|part)\.?\s*(\d+)", re.IGNORECASE)


class SourceMatcherEngine:
    def __init__(self, wiki_dir: Path, sources_dir: Path, laya_client: Any = None):
        self.wiki_dir = wiki_dir
        self.sources_dir = sources_dir.resolve()
        self.laya = laya_client
        self.sources_index: dict[str, dict[str, Any]] = {}
        self._index_sources()

    def _index_sources(self) -> None:
        if not self.sources_dir.exists():
            return

        for md_path in self.sources_dir.rglob("*.md"):
            try:
                raw = md_path.read_text(encoding="utf-8")
                header = " ".join(raw.splitlines()[:35])
                p_m = PAGE_HEADER_RE.search(header)
                v_m = VOL_HEADER_RE.search(header)

                self.sources_index[md_path.stem] = {
                    "path": md_path,
                    "rel_path": str(md_path.relative_to(self.sources_dir)),
                    "start_page": p_m.group(1) if p_m else "",
                    "volume": v_m.group(1) if v_m else "",
                    "snippet": raw[:1200],
                }
            except Exception:
                continue

    def validate_publication_source(self, slug: str) -> SourceValidationReport:
        wiki_file = self.wiki_dir / f"{slug}.md"
        if not wiki_file.exists():
            return SourceValidationReport(
                wiki_slug=slug,
                current_source_path=None,
                is_valid=False,
                reason="Wiki file does not exist",
            )

        parts = wiki_file.read_text(encoding="utf-8").split("---", 2)
        fm = yaml.safe_load(parts[1]) if len(parts) >= 3 else {}

        current_path = fm.get("source_path")
        current_doc = fm.get("source_doc")

        # 1. Resolve Target File on Disk
        target_file = None
        if current_path:
            p = (wiki_file.parent / current_path).resolve()
            if p.exists() and p.is_file():
                target_file = p
        elif current_doc and current_doc in self.sources_index:
            target_file = self.sources_index[current_doc]["path"]

        if not target_file:
            return SourceValidationReport(
                wiki_slug=slug,
                current_source_path=current_path,
                is_valid=False,
                reason="Source path points to missing file",
            )

        src_meta = self.sources_index.get(target_file.stem, {})
        wiki_vol = str(fm.get("volume") or "")

        # 2. Coordinate Heuristic Verification
        if src_meta.get("volume") and wiki_vol and src_meta["volume"] != wiki_vol:
            return SourceValidationReport(
                wiki_slug=slug,
                current_source_path=current_path,
                is_valid=False,
                reason=f"Volume mismatch: Wiki={wiki_vol}, Source={src_meta['volume']}",
            )

        # 3. Laya Neural Arbitration Gate (if active)
        if self.laya:
            context = (
                f"Source Header: {src_meta.get('snippet', '')}\n"
                f"Target Article: {fm.get('title')}\nAuthor: {fm.get('authors')}"
            )
            prob = self.laya.noul(
                context=context,
                question="Is this source document the authentic primary text for this publication?",
            )
            if prob < 0.25:
                return SourceValidationReport(
                    wiki_slug=slug,
                    current_source_path=current_path,
                    is_valid=False,
                    reason=f"Laya rejected source match (P={prob:.2f})",
                    confidence=prob,
                )

        return SourceValidationReport(
            wiki_slug=slug,
            current_source_path=current_path,
            is_valid=True,
            reason="Verified coordinates and content match",
            confidence=1.0,
        )