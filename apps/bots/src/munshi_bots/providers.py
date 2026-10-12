"""Data and Candidate Providers for Bot Policies."""
from __future__ import annotations

import re
import subprocess
import json
from pathlib import Path
from typing import Any
from rapidfuzz import fuzz

from munshi_bots.file_utils import read_wiki_page

ROW_RE = re.compile(
    r"^\|\s*\*{0,2}(?P<master>\d+)\*{0,2}\s*\|\s*(?P<series>[A-Z]+)\s*\|\s*(?P<volume>[^|]+?)\s*\|\s*(?P<issue>[^|]+?)\s*\|",
    re.MULTILINE,
)
FILENAME_MASTER_RE = re.compile(
    r"\b(?:jmbras|jsbras|sbras|jmalayanbras)[-_](?P<master>\d+)[-_]",
    re.IGNORECASE,
)


def clean_num(val: Any) -> str:
    """Normalizes volumes/issues: None -> '', 51 -> '51', '051' -> '51'."""
    if val is None:
        return ""
    s = str(val).strip().replace("—", "").replace("-", "")
    return str(int(s)) if s.isdigit() else s


class SourceCandidateProvider:
    """Indexes sources/ and resolves candidate files for a wiki stub."""

    def __init__(self, wiki_dir: Path, sources_dir: Path):
        self.wiki_dir = wiki_dir
        self.sources_dir = sources_dir.resolve()
        print(f"[DEBUG] SourceCandidateProvider scanning: {self.sources_dir}")
        print(f"[DEBUG] Found {len(list(self.sources_dir.rglob('*.md')))} markdown source files.")
        self.vol_issue_to_master: dict[tuple[str, str, str], int] = {}
        self.sources_index: dict[str, dict[str, Any]] = {}
        self._load_registry()
        self._index_sources()

    def _load_registry(self) -> None:
        reg_file = self.wiki_dir / "journal-of-the-malaysian-branch-of-the-royal-asiatic-society.md"
        if not reg_file.exists():
            return

        text = reg_file.read_text(encoding="utf-8")
        for m in ROW_RE.finditer(text):
            try:
                master = int(m.group("master"))
                raw_series = m.group("series").strip().upper()
                series = "MB" if ("MB" in raw_series or "JMBRAS" in raw_series) else "SB"
                vol = clean_num(m.group("volume"))
                issue = clean_num(m.group("issue"))

                if vol:
                    self.vol_issue_to_master[(series, vol, issue)] = master
                    self.vol_issue_to_master[(series, vol, "")] = master
            except Exception:
                continue

    def _index_sources(self) -> None:
        if not self.sources_dir.exists():
            return

        # In SourceCandidateProvider._index_sources in providers.py:

        for md_path in self.sources_dir.rglob("*.md"):
            try:
                # If this file is inside a multi-file publication directory:
                is_nested = md_path.parent != self.sources_dir
                
                # In nested folders, favor frontmatter.md or main chapter files
                # Skip secondary backmatter during primary alignment indexing
                if is_nested and md_path.stem.lower() in {
                    "appendix",
                    "glossary",
                    "bibliography",
                    "index",
                    "references",
                }:
                    continue

                fm, body = read_wiki_page(md_path)
                doc_id = str(fm.get("doc_id") or (md_path.parent.name if is_nested else md_path.stem))
                
                m_match = FILENAME_MASTER_RE.search(doc_id) or FILENAME_MASTER_RE.search(md_path.name)
                master_no = int(m_match.group("master")) if m_match else None

                rel_from_sources = md_path.relative_to(self.sources_dir)

                self.sources_index[doc_id] = {
                    "doc_id": doc_id,
                    "title": str(fm.get("title", "")),
                    "author": str(fm.get("author", "")),
                    "master_no": master_no,
                    "rel_path": f"../sources/{rel_from_sources.as_posix()}",
                    "path": md_path,
                }
            except Exception:
                continue

    def get_candidates(self, wiki_fm: dict[str, Any], wiki_stem: str) -> tuple[dict[str, Any] | None, str]:
        """Returns (deterministic_match, formatted_candidates_str)."""
        raw_jcode = str(wiki_fm.get("journal_code") or "").upper()
        series = "MB" if ("MB" in raw_jcode or "JMBRAS" in raw_jcode) else "SB"
        vol = clean_num(wiki_fm.get("volume"))
        issue = clean_num(wiki_fm.get("issue"))
        authors = wiki_fm.get("authors") or []
        title = str(wiki_fm.get("title") or wiki_stem)

        surnames = [
            parts[-1].lower()
            for a in authors
            if (parts := re.findall(r"[A-Za-z]+", str(a)))
        ]

        target_master = self.vol_issue_to_master.get((series, vol, issue)) or self.vol_issue_to_master.get((series, vol, ""))

        scored = []
        for doc_id, src in self.sources_index.items():
            score = 0
            # 1. Master Issue Match
            if target_master and src["master_no"] == target_master:
                score += 50

            # 2. Surname Match
            doc_lower = doc_id.lower()
            author_lower = src["author"].lower()
            if any(s in doc_lower or s in author_lower for s in surnames):
                score += 30

            # 3. Title Token Match
            t_sim = fuzz.token_set_ratio(title, src["title"])
            score += (t_sim * 0.4)

            if score >= 40:
                scored.append((score, src))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Deterministic Fast Path (Master Issue + Surname + Title Sim >= 50%)
        if scored:
            top_score, top_src = scored[0]
            if target_master and top_src["master_no"] == target_master:
                has_surname = any(s in top_src["doc_id"].lower() or s in top_src["author"].lower() for s in surnames)
                if has_surname and fuzz.token_set_ratio(title, top_src["title"]) >= 50.0:
                    return top_src, ""

        top_candidates = [c[1] for c in scored[:4]]
        if not top_candidates:
            return None, "(No candidate source documents found in sources/ matching issue coordinates or author)"

        formatted = []
        for i, c in enumerate(top_candidates, 1):
            formatted.append(
                f"[{i}] doc_id: {c['doc_id']}\n"
                f"    Title: {c['title']}\n"
                f"    Author: {c['author']}\n"
                f"    source_path: {c['rel_path']}"
            )
        return None, "\n\n".join(formatted)


def get_candidate_provider(name: str, wiki_dir: Path, root: Path):
    if name == "source_matcher":
        sources_candidate = root / "sources" if (root / "sources").exists() else root / "content" / "sources"
        return SourceCandidateProvider(wiki_dir=wiki_dir, sources_dir=sources_candidate)
    elif name == "surface_mention_linker":
        return SurfaceMentionCandidateProvider(wiki_dir=wiki_dir)
    return None

class SurfaceMentionCandidateProvider:
    """Pre-filters candidate wiki pages by matching titles/aliases against body text."""

    def __init__(self, wiki_dir: Path):
        self.wiki_dir = wiki_dir.resolve()
        # surface_form (lower) -> list of target entity dicts
        self.surface_lookup: dict[str, list[dict[str, str]]] = {}
        self._build_surface_index()

    def _build_surface_index(self) -> None:
        """Loads all wiki entities into an in-memory dictionary once at startup."""
        for md_path in self.wiki_dir.glob("*.md"):
            try:
                fm, _ = read_wiki_page(md_path)
                slug = md_path.stem
                title = str(fm.get("title") or slug.replace("-", " ")).strip()
                aliases = fm.get("aliases") or []
                if isinstance(aliases, str):
                    aliases = [aliases]

                entity_info = {
                    "slug": slug,
                    "title": title,
                    "type": str(fm.get("type", "concept")),
                }

                # Index canonical title (min length >= 4 to avoid tiny noise words)
                if len(title) >= 4:
                    self.surface_lookup.setdefault(title.lower(), []).append(entity_info)

                # Index aliases
                for a in aliases:
                    clean_a = str(a).strip()
                    if len(clean_a) >= 4:
                        self.surface_lookup.setdefault(clean_a.lower(), []).append(entity_info)
            except Exception:
                continue

    def get_candidates(self, wiki_fm: dict[str, Any], wiki_stem: str) -> tuple[None, str]:
        """Scans the page body text and surfaces candidates whose names appear in the prose."""
        target_file = self.wiki_dir / f"{wiki_stem}.md"
        if not target_file.exists():
            return None, "(No candidate entities found)"

        _, body = read_wiki_page(target_file)
        body_lower = body.lower()

        matched_candidates: list[dict[str, str]] = []
        seen_slugs: set[str] = {wiki_stem}  # Ignore self-links

        # Sort surface terms by length descending (match "tin mining" before "tin")
        for term, entities in sorted(self.surface_lookup.items(), key=lambda x: len(x[0]), reverse=True):
            if term in body_lower:
                for ent in entities:
                    if ent["slug"] not in seen_slugs:
                        seen_slugs.add(ent["slug"])
                        matched_candidates.append({
                            "surface_mention": term,
                            "slug": ent["slug"],
                            "title": ent["title"],
                            "type": ent["type"],
                        })
                        if len(matched_candidates) >= 15:
                            break
            if len(matched_candidates) >= 15:
                break

        if not matched_candidates:
            return None, "(No candidate entity mentions detected in body text)"

        formatted = []
        for i, c in enumerate(matched_candidates, 1):
            formatted.append(
                f"[{i}] Mention in text: \"{c['surface_mention']}\"\n"
                f"    Target Slug: {c['slug']}\n"
                f"    Canonical Title: {c['title']} ({c['type']})"
            )
        return None, "\n\n".join(formatted)