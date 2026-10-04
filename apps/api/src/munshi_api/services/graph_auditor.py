"""High-performance, inverted-index graph health and source audit engine."""
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
from munshi_api.services.journal_registry import JournalRegistry

logger = logging.getLogger(__name__)

PAGE_HEADER_RE = re.compile(r"\bpp?\.?\s*(\d+)(?:[-–—\s]+(\d+))?", re.IGNORECASE)
VOL_HEADER_RE = re.compile(r"\b(?:vol|volume|no|number|part)\.?\s*(\d+)", re.IGNORECASE)
SPAN_PAGE_RE = re.compile(r'<span\s+id=["\']page-(\d+)["\']\s*>', re.IGNORECASE)
AUXILIARY_FRAGMENTS = {"glossary.md", "references.md", "appendix.md", "bibliography.md"}


def _safe_int(val: Any) -> int | None:
    if val is None:
        return None
    cleaned = re.sub(r"[^\d]", "", str(val))
    return int(cleaned) if cleaned else None


def _clean_word_tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"\b[a-z]{3,}\b", text.lower()) if w not in {"the", "and", "for", "with"}]


class GraphAuditorEngine:
    def __init__(self, wiki_dir: Path, sources_dir: Path | None = None, laya_client: Any = None):
        self.wiki_dir = wiki_dir
        self.sources_dir = sources_dir.resolve() if sources_dir else (wiki_dir.parent / "sources").resolve()
        self.laya = laya_client
        self.registry = JournalRegistry.get_instance(self.wiki_dir)

        # In-memory indices
        self.sources_index: dict[str, dict[str, Any]] = {}
        self.sources_by_master: dict[int, list[str]] = defaultdict(list)
        self.sources_by_vol: dict[str, list[str]] = defaultdict(list)
        self.sources_by_word: dict[str, list[str]] = defaultdict(list)
        self.author_alias_cache: dict[str, set[str]] = defaultdict(set)

        self._build_author_cache()
        self._index_sources()

    def audit_author_attributions(self) -> list[dict[str, Any]]:
        """
        Verifies that publications claimed in an author's bibliography
        match declared frontmatter in the publication stub.
        Ignores ## MBRAS Sources (which are subject references ABOUT the entity).
        """
        author_claims: dict[str, list[str]] = defaultdict(list)
        BIB_LINK_RE = re.compile(r"^\s*-\s*.*?\(\./(?P<slug>[^)]+?)\.md\)", re.MULTILINE)

        def _extract_names(items: Any) -> list[str]:
            if not items:
                return []
            if isinstance(items, str):
                return [items.strip()]
            if not isinstance(items, list):
                return []
            names: list[str] = []
            for it in items:
                if isinstance(it, str) and it.strip():
                    names.append(it.strip())
                elif isinstance(it, dict):
                    val = it.get("name") or it.get("canonical_name") or it.get("id")
                    if val and isinstance(val, str):
                        names.append(val.strip())
            return names

        # Pass 1: Collect claims from author bibliographies
        for md_path in self.wiki_dir.glob("*.md"):
            try:
                raw = md_path.read_text(encoding="utf-8")
                if not raw.startswith("---"):
                    continue
                parts = raw.split("---", 2)
                if len(parts) < 3:
                    continue

                fm = yaml.safe_load(parts[1])
                if not isinstance(fm, dict):
                    continue

                if not (fm.get("is_contributor") or fm.get("type") in {"author", "person"}):
                    continue

                body = parts[2]
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
            except Exception:
                continue

        # Pass 2: Reconcile against publication frontmatter
        mismatches: list[dict[str, Any]] = []

        for pub_slug, claiming_authors in author_claims.items():
            pub_file = self.wiki_dir / f"{pub_slug}.md"
            if not pub_file.exists():
                continue

            try:
                parts = pub_file.read_text(encoding="utf-8").split("---", 2)
                if len(parts) < 3:
                    continue
                pub_fm = yaml.safe_load(parts[1])
                if not isinstance(pub_fm, dict):
                    continue

                stated_authors = _extract_names(pub_fm.get("authors"))
                stated_editors = _extract_names(pub_fm.get("editors"))
                stated_contribs = _extract_names(pub_fm.get("contributors"))

                all_credited_names = set(stated_authors) | set(stated_editors) | set(stated_contribs)

                for author_slug in claiming_authors:
                    author_file = self.wiki_dir / f"{author_slug}.md"
                    if not author_file.exists():
                        continue

                    a_parts = author_file.read_text(encoding="utf-8").split("---", 2)
                    if len(a_parts) < 3:
                        continue
                    a_fm = yaml.safe_load(a_parts[1])
                    if not isinstance(a_fm, dict):
                        continue

                    canonical_name = a_fm.get("canonical_name") or a_fm.get("title")
                    aliases = _extract_names(a_fm.get("aliases"))
                    all_author_names = set(aliases)
                    if canonical_name and isinstance(canonical_name, str):
                        all_author_names.add(canonical_name.strip())

                    # Flag true discrepancies where the author or aliases are absent
                    if not any(name in all_credited_names for name in all_author_names):
                        mismatches.append({
                            "publication_slug": pub_slug,
                            "article_stated_authors": stated_authors,
                            "article_stated_editors": stated_editors,
                            "claimed_by_author_profiles": [author_slug],
                            "claiming_author_name": (canonical_name if isinstance(canonical_name, str) else None)
                            or author_slug.replace("-", " ").title(),
                            "claiming_author_slug": author_slug,
                            "discrepancy_type": "article_frontmatter_mismatch",
                        })
            except Exception:
                continue

        return mismatches

    def _build_author_cache(self) -> None:
        """Indexes all author profiles and aliases once into memory to eliminate disk globbing."""
        for md_path in self.wiki_dir.glob("*.md"):
            try:
                raw = md_path.read_text(encoding="utf-8")
                if not raw.startswith("---"):
                    continue
                fm = yaml.safe_load(raw.split("---", 2)[1]) or {}
                if not (fm.get("is_contributor") or fm.get("type") in {"author", "person"}):
                    continue

                names = [fm.get("title") or md_path.stem]
                names.extend(fm.get("aliases") or [])
                tokens: set[str] = set()

                for n in names:
                    if not n:
                        continue
                    clean = str(n).lower().strip()
                    tokens.add(clean)
                    words = re.findall(r"\b[a-z]+\b", clean)
                    if words:
                        tokens.add(words[-1])  # Surname
                        initials = "".join(w[0] for w in words)
                        tokens.add(initials)
                        tokens.add(f"-{words[-1][0]}-")

                # Map by surname and slug
                for t in tokens:
                    self.author_alias_cache[t].update(tokens)
            except Exception:
                continue

    def _index_sources(self) -> None:
        """Builds in-memory inverted buckets across primary sources."""
        if not self.sources_dir.exists():
            return

        for md_path in self.sources_dir.rglob("*.md"):
            try:
                raw = md_path.read_text(encoding="utf-8")
                fm: dict[str, Any] = {}
                body = raw
                if raw.startswith("---"):
                    parts = raw.split("---", 2)
                    if len(parts) >= 3:
                        try:
                            fm = yaml.safe_load(parts[1]) or {}
                            body = parts[2]
                        except Exception:
                            pass

                fm_title = fm.get("title")
                fm_author = fm.get("author") or fm.get("authors")
                if isinstance(fm_author, list):
                    source_author_str = " ".join(str(a) for a in fm_author if a)
                else:
                    source_author_str = str(fm_author or "")

                pages = [int(p) for p in SPAN_PAGE_RE.findall(body)]
                start_p = pages[0] if pages else None
                end_p = pages[-1] if pages else None

                header = " ".join(body.splitlines()[:35])
                p_m = PAGE_HEADER_RE.search(header)
                v_m = VOL_HEADER_RE.search(header)

                if start_p is None and p_m:
                    start_p = _safe_int(p_m.group(1))

                vol_str = str(fm.get("volume") or (v_m.group(1) if v_m else "")).strip()
                title_str = str(fm_title) if fm_title else md_path.stem.replace("-", " ")
                stem = md_path.stem

                self.sources_index[stem] = {
                    "path": md_path,
                    "rel_path": str(md_path.relative_to(self.sources_dir)),
                    "start_page": start_p,
                    "end_page": end_p,
                    "volume": vol_str,
                    "title": title_str,
                    "author": source_author_str,
                }

                # Populate Inverted Buckets
                m_no = self.registry.extract_master_from_filename(stem)
                if m_no:
                    self.sources_by_master[m_no].append(stem)
                if vol_str:
                    self.sources_by_vol[vol_str].append(stem)

                for token in _clean_word_tokens(title_str) + _clean_word_tokens(source_author_str):
                    self.sources_by_word[token].append(stem)
            except Exception:
                continue

    def _resolve_candidate(
        self,
        title: str,
        wiki_vol: str,
        wiki_issue: str,
        expected_master: int | None,
        author_variants: set[str],
        w_page_int: int | None,
        exclude_stem: str | None = None,
    ) -> tuple[dict[str, Any] | None, float]:
        """Prunes search space using inverted buckets before running fuzzy matching."""
        candidate_stems: set[str] = set()

        # 1. Master number bucket
        if expected_master and expected_master in self.sources_by_master:
            candidate_stems.update(self.sources_by_master[expected_master])

        # 2. Volume bucket
        if wiki_vol and wiki_vol in self.sources_by_vol:
            candidate_stems.update(self.sources_by_vol[wiki_vol])

        # 3. Keyword / Author tokens
        for token in _clean_word_tokens(title)[:4]:
            if token in self.sources_by_word:
                candidate_stems.update(self.sources_by_word[token])

        for variant in author_variants:
            if variant in self.sources_by_word:
                candidate_stems.update(self.sources_by_word[variant])

        if exclude_stem:
            candidate_stems.discard(exclude_stem)

        # Fallback to general index only if buckets found nothing
        pool = [self.sources_index[s] for s in candidate_stems] if candidate_stems else list(self.sources_index.values())

        best_cand: dict[str, Any] | None = None
        best_score = 0.0

        for s_info in pool:
            score = 0.0
            src_name = s_info["path"].name.lower()
            src_title = s_info["title"].lower()
            src_author = s_info["author"].lower()

            # Title Similarity
            title_sim = fuzz.token_set_ratio(title.lower(), src_title)
            if title_sim >= 70:
                score += (title_sim * 0.65)

            # Master / Volume Match
            c_master = self.registry.extract_master_from_filename(src_name)
            if expected_master and c_master == expected_master:
                score += 25.0
            elif wiki_vol and (
                self.registry.matches_coordinates(src_name, "MB", wiki_vol, wiki_issue)
                or self.registry.matches_coordinates(src_name, "SB", wiki_vol, wiki_issue)
            ):
                score += 20.0

            # Author Overlap
            if any(v in src_name or v in src_author for v in author_variants):
                score += 20.0

            # Page Range Proximity
            s_start = s_info.get("start_page")
            s_end = s_info.get("end_page")
            if w_page_int and s_start:
                if abs(w_page_int - s_start) <= 2 or (s_end and s_start <= w_page_int <= s_end):
                    score += 15.0

            if score > best_score and score >= 45.0:
                best_score = score
                best_cand = s_info

        conf = round(min(best_score / 100.0, 0.99), 2) if best_cand else 0.0
        return best_cand, conf

    def audit_source_paths(self) -> list[SourceMismatchReport]:
        mismatches: list[SourceMismatchReport] = []

        for md_path in self.wiki_dir.glob("*.md"):
            try:
                raw = md_path.read_text(encoding="utf-8")
                if not raw.startswith("---"):
                    continue
                parts = raw.split("---", 2)
                if len(parts) < 3:
                    continue

                fm = yaml.safe_load(parts[1])
                if not isinstance(fm, dict) or fm.get("type") != "article":
                    continue

                slug = md_path.stem
                source_path = fm.get("source_path")
                source_doc = fm.get("source_doc")
                wiki_vol = str(fm.get("volume") or "").strip()
                wiki_issue = str(fm.get("issue") or "").strip()
                pages = str(fm.get("pages") or "")
                title = str(fm.get("title") or slug.replace("-", " "))

                raw_wiki_authors = fm.get("authors") or fm.get("author") or []
                wiki_authors = [raw_wiki_authors] if isinstance(raw_wiki_authors, str) else [str(a) for a in raw_wiki_authors if a]

                author_variants: set[str] = set()
                for a in wiki_authors:
                    for token in re.findall(r"\b[a-z]+\b", a.lower()):
                        author_variants.update(self.author_alias_cache.get(token, {token}))

                p_m = re.search(r"\d+", pages)
                w_page_int = _safe_int(p_m.group(0)) if p_m else None

                expected_master = (
                    self.registry.vol_issue_to_master.get(("MB", wiki_vol, wiki_issue))
                    or self.registry.vol_issue_to_master.get(("SB", wiki_vol, wiki_issue))
                    or self.registry.vol_issue_to_master.get(("MB", wiki_vol, ""))
                    or self.registry.vol_issue_to_master.get(("SB", wiki_vol, ""))
                )

                # Case 1: Missing Source Field
                if not source_path and not source_doc:
                    cand, conf = self._resolve_candidate(
                        title, wiki_vol, wiki_issue, expected_master, author_variants, w_page_int
                    )
                    mismatches.append(
                        SourceMismatchReport(
                            wiki_slug=slug,
                            current_source_path=None,
                            current_source_doc=None,
                            error_type="missing_source_field",
                            detail="Article contains neither source_path nor source_doc.",
                            suggested_source_path=f"../sources/{cand['rel_path']}" if cand else None,
                            suggested_doc_id=cand["path"].stem if cand else None,
                            confidence=conf,
                        )
                    )
                    continue

                # Resolve Declared Path
                resolved_target: Path | None = None
                if source_path:
                    p_rel_wiki = (md_path.parent / source_path).resolve()
                    p_rel_src = (self.sources_dir / source_path).resolve()
                    if p_rel_wiki.is_file():
                        resolved_target = p_rel_wiki
                    elif p_rel_src.is_file():
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

                # Case 2: Fragment Target
                if resolved_target.name.lower() in AUXILIARY_FRAGMENTS:
                    parent_dir = resolved_target.parent
                    suggested_file = next(
                        (parent_dir / c for c in ("frontmatter.md", f"{parent_dir.name}.md") if (parent_dir / c).exists()),
                        None,
                    )
                    mismatches.append(
                        SourceMismatchReport(
                            wiki_slug=slug,
                            current_source_path=source_path,
                            current_source_doc=source_doc,
                            error_type="fragment_target",
                            detail=f"Points to auxiliary fragment '{resolved_target.name}' instead of article body.",
                            suggested_source_path=f"../sources/{suggested_file.relative_to(self.sources_dir)}" if suggested_file else None,
                            suggested_doc_id=parent_dir.name,
                            confidence=0.95,
                        )
                    )
                    continue

                # Case 3: Coordinate Clash with Master No. Filter
                if (
                    self.registry.matches_coordinates(resolved_target.name, "MB", wiki_vol, wiki_issue)
                    or self.registry.matches_coordinates(resolved_target.name, "SB", wiki_vol, wiki_issue)
                ):
                    continue

                src_info = self.sources_index.get(resolved_target.stem, {})
                src_vol = str(src_info.get("volume") or "")
                src_page = str(src_info.get("start_page") or "")

                vol_mismatch = bool(src_vol and wiki_vol and src_vol != wiki_vol)
                s_page_int = _safe_int(src_page)
                page_mismatch = False
                if s_page_int is not None and w_page_int is not None:
                    if s_page_int != 1 or w_page_int == 1:
                        page_mismatch = abs(s_page_int - w_page_int) > 3

                if vol_mismatch or page_mismatch:
                    cand, conf = self._resolve_candidate(
                        title, wiki_vol, wiki_issue, expected_master, author_variants, w_page_int, exclude_stem=resolved_target.stem
                    )
                    mismatches.append(
                        SourceMismatchReport(
                            wiki_slug=slug,
                            current_source_path=source_path,
                            current_source_doc=source_doc,
                            error_type="coordinate_mismatch",
                            detail=f"Coordinate clash: Wiki=(Vol {wiki_vol}, p.{wiki_start_page}) vs Source=(Vol {src_vol}, p.{src_page})",
                            suggested_source_path=f"../sources/{cand['rel_path']}" if cand else None,
                            suggested_doc_id=cand["path"].stem if cand else None,
                            confidence=conf,
                        )
                    )

            except Exception:
                continue

        return mismatches

    def run_health_audit(self) -> GraphHealthReport:
        # Reuses audit_source_paths() directly
        return GraphHealthReport(
            total_entities=len(self.wiki_dir.glob("*.md")),
            broken_link_count=0,
            broken_links=[],
            potential_split_authors=[],
            source_mismatches=self.audit_source_paths(),
        )