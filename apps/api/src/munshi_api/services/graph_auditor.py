"""Unified graph health check engine for wiki/*.md."""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any
import yaml
from rapidfuzz import fuzz

from munshi_api.models.audit import (
    BrokenLinkItem,
    GraphHealthReport,
    SourceMismatchReport,
    SplitAuthorCluster,
)

logger = logging.getLogger(__name__)

PAGE_HEADER_RE = re.compile(r"\bpp?\.?\s*(\d+)(?:[-–—\s]+(\d+))?", re.IGNORECASE)
VOL_HEADER_RE = re.compile(r"\b(?:vol|volume|no|number|part)\.?\s*(\d+)", re.IGNORECASE)
LINK_RE = re.compile(r"\[(?P<title>[^\]]+)\]\(\.?/?(?P<slug>[^)]+?)(?:\.md)?\)")
STOP_WORDS = {"sir", "dato", "datuk", "dr", "prof", "tunku", "raja", "haji"}
AUXILIARY_FRAGMENTS = {"glossary.md", "references.md", "appendix.md", "bibliography.md"}


def _safe_int(val: Any) -> int | None:
    """Safely converts string to int, returning None for Roman numerals or invalid strings."""
    if val is None:
        return None
    cleaned = re.sub(r"[^\d]", "", str(val))
    return int(cleaned) if cleaned else None


class GraphAuditorEngine:
    def __init__(self, wiki_dir: Path, sources_dir: Path | None = None, laya_client: Any = None):
        self.wiki_dir = wiki_dir
        self.sources_dir = sources_dir.resolve() if sources_dir else (wiki_dir.parent / "sources").resolve()
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
                    "title": md_path.stem.replace("-", " "),
                }
            except Exception:
                continue

    def audit_author_attributions(self) -> list[dict[str, Any]]:
        """
        Verifies that publications claimed in an author's bibliography
        match declared frontmatter in the publication stub.
        Ignores ## MBRAS Sources (which are subject references ABOUT the entity).
        """
        author_claims: dict[str, list[str]] = defaultdict(list)
        BIB_LINK_RE = re.compile(r"^\s*-\s*.*?\(\./(?P<slug>[^)]+?)\.md\)", re.MULTILINE)

        for md_path in self.wiki_dir.glob("*.md"):
            try:
                raw = md_path.read_text(encoding="utf-8")
                if not raw.startswith("---"):
                    continue
                parts = raw.split("---", 2)
                if len(parts) < 3:
                    continue

                fm = yaml.safe_load(parts[1]) or {}
                # Only check files that represent authors/contributors
                if not (fm.get("is_contributor") or fm.get("type") in {"author", "person"}):
                    continue

                body = parts[2]

                # Robust regex: matches ## Bibliography, ## Biography & Bibliography, etc.
                # Handles \r\n and optional leading whitespace
                bib_match = re.search(
                    r"(?:\r?\n|^)\s*##\s+[^\r\n]*biblio[^\r\n]*(.*?)(?=(?:\r?\n)\s*##\s+|\Z)",
                    body,
                    re.DOTALL | re.IGNORECASE,
                )
                if not bib_match:
                    continue

                bib_text = bib_match.group(1)
                for m in BIB_LINK_RE.finditer(bib_text):
                    author_claims[m.group("slug")].append(md_path.stem)

            except Exception as e:
                logger.warning("Error reading %s for author attributions: %s", md_path.name, e)
                continue

        mismatches: list[dict[str, Any]] = []

        for pub_slug, claiming_authors in author_claims.items():
            pub_file = self.wiki_dir / f"{pub_slug}.md"
            if not pub_file.exists():
                continue

            try:
                parts = pub_file.read_text(encoding="utf-8").split("---", 2)
                if len(parts) < 3:
                    continue
                pub_fm = yaml.safe_load(parts[1]) or {}

                # Credited people on the publication stub
                stated_authors = pub_fm.get("authors") or []
                stated_editors = pub_fm.get("editors") or []
                stated_contribs = [
                    c.get("name") if isinstance(c, dict) else c
                    for c in (pub_fm.get("contributors") or [])
                ]
                all_credited_names = set(stated_authors) | set(stated_editors) | set(stated_contribs)

                for author_slug in claiming_authors:
                    author_file = self.wiki_dir / f"{author_slug}.md"
                    if not author_file.exists():
                        continue

                    a_parts = author_file.read_text(encoding="utf-8").split("---", 2)
                    a_fm = yaml.safe_load(a_parts[1]) or {}
                    canonical_name = a_fm.get("canonical_name") or a_fm.get("title")

                    # Check aliases as well
                    aliases = set(a_fm.get("aliases") or [])
                    all_author_names = {canonical_name} | aliases if canonical_name else aliases

                    # If author (or alias) is NOT among credited names, it's a true mismatch
                    if not any(name in all_credited_names for name in all_author_names):
                        mismatches.append({
                            "publication_slug": pub_slug,
                            "article_stated_authors": stated_authors,
                            "article_stated_editors": stated_editors,
                            "claimed_by_author_profiles": [author_slug],
                            "claiming_author_name": canonical_name or author_slug.replace("-", " ").title(),
                            "claiming_author_slug": author_slug,
                            "discrepancy_type": "article_frontmatter_mismatch",
                        })

            except Exception as e:
                logger.warning("Error evaluating publication stub %s: %s", pub_slug, e)
                continue

        return mismatches

    def audit_source_paths(self) -> list[SourceMismatchReport]:
        mismatches: list[SourceMismatchReport] = []

        for md_path in self.wiki_dir.glob("*.md"):
            try:
                raw = md_path.read_text(encoding="utf-8")
                parts = raw.split("---", 2)
                if len(parts) < 3:
                    continue

                fm = yaml.safe_load(parts[1]) or {}
                if fm.get("type") != "article":
                    continue

                slug = md_path.stem
                source_path = fm.get("source_path")
                source_doc = fm.get("source_doc")
                wiki_vol = str(fm.get("volume") or "")
                pages = str(fm.get("pages") or "")
                p_m = re.search(r"\d+", pages)
                wiki_start_page = p_m.group(0) if p_m else ""

                if not source_path and not source_doc:
                    mismatches.append(
                        SourceMismatchReport(
                            wiki_slug=slug,
                            current_source_path=None,
                            current_source_doc=None,
                            error_type="missing_source_field",
                            detail="Article contains neither source_path nor source_doc.",
                        )
                    )
                    continue

                resolved_target: Path | None = None
                if source_path:
                    p_rel_wiki = (md_path.parent / source_path).resolve()
                    p_rel_src = (self.sources_dir / source_path).resolve()
                    if p_rel_wiki.is_file() and p_rel_wiki.exists():
                        resolved_target = p_rel_wiki
                    elif p_rel_src.is_file() and p_rel_src.exists():
                        resolved_target = p_rel_src

                if not resolved_target and source_doc and source_doc in self.sources_index:
                    resolved_target = self.sources_index[source_doc]["path"]

                if not resolved_target:
                    mismatches.append(
                        SourceMismatchReport(
                            wiki_slug=slug,
                            current_source_path=source_path,
                            current_source_doc=source_doc,
                            error_type="file_not_found",
                            detail=f"Target source file does not exist on disk: '{source_path or source_doc}'",
                        )
                    )
                    continue

                if resolved_target.name.lower() in AUXILIARY_FRAGMENTS:
                    parent_dir = resolved_target.parent
                    suggested_file = None
                    for candidate in ("frontmatter.md", f"{parent_dir.name}.md"):
                        if (parent_dir / candidate).exists():
                            suggested_file = parent_dir / candidate
                            break

                    mismatches.append(
                        SourceMismatchReport(
                            wiki_slug=slug,
                            current_source_path=source_path,
                            current_source_doc=source_doc,
                            error_type="fragment_target",
                            detail=f"Points to auxiliary fragment '{resolved_target.name}' instead of article body.",
                            suggested_source_path=f"../sources/{suggested_file.relative_to(self.sources_dir)}"
                            if suggested_file
                            else None,
                            suggested_doc_id=parent_dir.name,
                            confidence=0.95,
                        )
                    )
                    continue

                src_info = self.sources_index.get(resolved_target.stem, {})
                src_vol = src_info.get("volume", "")
                src_page = src_info.get("start_page", "")

                vol_mismatch = bool(src_vol and wiki_vol and src_vol != wiki_vol)

                # SAFE INTEGER CONVERSION: protects against Roman numerals (iv, xxi)
                s_page_int = _safe_int(src_page)
                w_page_int = _safe_int(wiki_start_page)
                page_mismatch = False
                if s_page_int is not None and w_page_int is not None:
                    page_mismatch = abs(s_page_int - w_page_int) > 3

                if vol_mismatch or page_mismatch:
                    mismatches.append(
                        SourceMismatchReport(
                            wiki_slug=slug,
                            current_source_path=source_path,
                            current_source_doc=source_doc,
                            error_type="coordinate_mismatch",
                            detail=f"Coordinate clash: Wiki=(Vol {wiki_vol}, p.{wiki_start_page}) vs Source=(Vol {src_vol}, p.{src_page})",
                        )
                    )

            except Exception as e:
                logger.warning("Error auditing source path for %s: %s", md_path.name, e)
                continue

        return mismatches

    def run_health_audit(self) -> GraphHealthReport:
        files_by_slug: dict[str, Path] = {}
        author_clusters: dict[tuple[str, str], list[str]] = defaultdict(list)
        entities: dict[str, dict[str, Any]] = {}

        for md_path in self.wiki_dir.glob("*.md"):
            slug = md_path.stem
            files_by_slug[slug] = md_path
            raw = md_path.read_text(encoding="utf-8")
            parts = raw.split("---", 2)
            if len(parts) < 3:
                continue

            fm = yaml.safe_load(parts[1]) or {}
            title = fm.get("title") or slug
            entities[slug] = {"fm": fm, "body": parts[2]}

            if fm.get("is_contributor") or fm.get("type") in {"author", "person"}:
                tokens = [t for t in title.lower().split() if t not in STOP_WORDS]
                if tokens:
                    surname = tokens[0] if "," in title else tokens[-1]
                    initial = tokens[0][0] if tokens else ""
                    author_clusters[(surname, initial)].append(slug)

        missing_index: dict[str, set[str]] = defaultdict(set)
        total_broken = 0
        for slug, data in entities.items():
            if data["fm"].get("type") in {"journal_issue", "person", "author"} or data["fm"].get("is_contributor"):
                for m in LINK_RE.finditer(data["body"]):
                    target = Path(m.group("slug")).stem
                    if target not in files_by_slug:
                        total_broken += 1
                        missing_index[target].add(slug)

        broken_links = [
            BrokenLinkItem(
                target_slug=k,
                referenced_in=sorted(list(v))[:5],
                hit_count=len(v),
            )
            for k, v in missing_index.items()
        ]
        broken_links.sort(key=lambda x: x.hit_count, reverse=True)

        split_reports = [
            SplitAuthorCluster(cluster_key=f"{surname.title()}, {initial.upper()}.", slugs=slugs)
            for (surname, initial), slugs in author_clusters.items()
            if len(slugs) > 1
        ]

        source_mismatches = self.audit_source_paths()

        return GraphHealthReport(
            total_entities=len(entities),
            broken_link_count=total_broken,
            broken_links=broken_links[:50],
            potential_split_authors=split_reports,
            source_mismatches=source_mismatches,
        )