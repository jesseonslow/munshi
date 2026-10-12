"""Extracts structured publication metadata, source structures, and category heuristics from wiki files."""
from __future__ import annotations

import re
from pathlib import Path
import yaml

from munshi_synthesizer.schema import PublicationSource

PUBLICATION_TYPES = {
    "publication",
    "article",
    "monograph",
    "reprint",
    "reprint_volume",
    "journal_article",
    "note",
}


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Splits YAML frontmatter and markdown body."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except Exception:
        fm = {}
    return fm, parts[2].strip()


def join_frontmatter(fm: dict, body: str) -> str:
    """Serializes updated YAML frontmatter and recombines with body."""
    fm_yaml = yaml.dump(fm, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{fm_yaml}\n---\n\n{body.strip()}\n"


class PublicationParser:
    """Extracts metadata, summaries, key findings, and context notes from publication markdown."""

    @staticmethod
    def is_publication_file(file_path: Path) -> bool:
        """Determines if a markdown file is an authentic publication stub vs an author/concept profile."""
        if not file_path.is_file():
            return False

        try:
            head = file_path.read_text(encoding="utf-8")[:1000]
        except Exception:
            return False

        fm, _ = split_frontmatter(head)
        if not fm:
            return False

        # Reject author/person stubs
        if fm.get("is_contributor") or fm.get("type") in {"person", "author", "contributor"}:
            return False

        # Accept publication types
        doc_type = str(fm.get("type", "")).lower()
        pub_type = str(fm.get("publication_type", "")).lower()
        if doc_type in PUBLICATION_TYPES or pub_type in PUBLICATION_TYPES:
            return True

        # Fallback: Does it have journal_code or volume or pages?
        if fm.get("journal_code") or fm.get("volume") or fm.get("pages"):
            return True

        return False

    @staticmethod
    def parse(file_path: Path) -> PublicationSource | None:
        if not file_path.exists() or not file_path.is_file():
            return None

        try:
            raw_text = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        fm, body = split_frontmatter(raw_text)
        if not fm or not isinstance(fm, dict):
            return None

        # Verify this is not an author stub
        if fm.get("is_contributor") or fm.get("type") in {"person", "author", "contributor"}:
            return None

        # 1. Extract Lede Paragraph (between # Title and ## Summary / ## Context)
        lede = ""
        body_no_h1 = re.sub(r"^#\s+[^\n]+\n*", "", body, count=1).strip()
        lede_match = re.match(r"^(.*?)(?=\n##\s+|\Z)", body_no_h1, re.DOTALL)
        if lede_match:
            candidate_lede = lede_match.group(1).strip()
            if not candidate_lede.startswith("<!--"):
                lede = candidate_lede

        # 2. Extract ## Summary
        summary = ""
        summary_match = re.search(
            r"##\s+Summary\s*\n(.*?)(?=\n###|\n##|\Z)", body, re.DOTALL
        )
        if summary_match:
            summary = summary_match.group(1).strip()

        # Fallback to lede if summary header was absent
        if not summary and lede:
            summary = lede
            lede = ""

        # 3. Extract ### Key Findings
        key_findings: list[str] = []
        kf_match = re.search(
            r"###\s+Key Findings\s*\n(.*?)(?=\n###|\n##|\Z)", body, re.DOTALL
        )
        if kf_match:
            for line in kf_match.group(1).strip().splitlines():
                line = line.strip()
                if line.startswith(("-", "*")):
                    clean_finding = re.sub(r"^[-*]\s*", "", line).strip()
                    if clean_finding:
                        key_findings.append(clean_finding)

        # 4. Extract ## Context
        context_notes: list[str] = []
        ctx_match = re.search(
            r"##\s+Context\s*\n(.*?)(?=\n###|\n##|\Z)", body, re.DOTALL
        )
        if ctx_match:
            for line in ctx_match.group(1).strip().splitlines():
                line = line.strip()
                if line.startswith(("-", "*")):
                    clean_note = re.sub(r"^[-*]\s*", "", line).strip()
                    if clean_note:
                        context_notes.append(clean_note)

        raw_authors = fm.get("authors") or []
        if isinstance(raw_authors, str):
            authors = [raw_authors]
        elif isinstance(raw_authors, list):
            authors = [str(a) for a in raw_authors]
        else:
            authors = []

        return PublicationSource(
            slug=file_path.stem,
            title=str(fm.get("title", file_path.stem)).strip(),
            authors=authors,
            year=fm.get("year", "n.d."),
            journal_code=fm.get("journal_code"),
            volume=str(fm.get("volume")) if fm.get("volume") is not None else None,
            issue=str(fm.get("issue")) if fm.get("issue") is not None else None,
            pages=str(fm.get("pages")) if fm.get("pages") is not None else None,
            jstor=fm.get("jstor"),
            project_muse=fm.get("project_muse"),
            lede=lede,
            summary=summary,
            key_findings=key_findings,
            context_notes=context_notes,
        )

    @classmethod
    def load_monograph_chapters(cls, monograph_dir: Path) -> str:
        """Concatenates substantive narrative chapters from a source monograph folder."""
        chapters = []
        for f in sorted(monograph_dir.glob("*.md")):
            name = f.stem.lower()
            if any(skip in name for skip in ("index", "bibliography", "plates", "preface", "contents")):
                continue
            chapters.append(f.read_text(encoding="utf-8", errors="ignore"))
        return "\n\n".join(chapters)

    @classmethod
    def resolve_raw_source_text(cls, slug: str, wiki_dir: Path) -> str | None:
        """Attempts to find the full primary markdown text from sources/ directory."""
        sources_base = wiki_dir.parent / "sources"

        # 1. Direct file or folder matching slug
        cand_file = sources_base / f"{slug}.md"
        if cand_file.is_file():
            return cand_file.read_text(encoding="utf-8", errors="ignore")

        cand_dir = sources_base / slug
        if cand_dir.is_dir():
            return cls.load_monograph_chapters(cand_dir)

        # 2. Check publication stub frontmatter for source_doc / source_path
        wiki_file = wiki_dir / f"{slug}.md"
        if wiki_file.is_file():
            fm, _ = split_frontmatter(wiki_file.read_text(encoding="utf-8", errors="ignore"))

            # Check source_doc folder
            src_doc = fm.get("source_doc")
            if src_doc:
                doc_dir = sources_base / src_doc
                if doc_dir.is_dir():
                    return cls.load_monograph_chapters(doc_dir)
                doc_file = sources_base / f"{src_doc}.md"
                if doc_file.is_file():
                    return doc_file.read_text(encoding="utf-8", errors="ignore")

            # Check source_path
            src_path = fm.get("source_path")
            if src_path:
                target = (wiki_file.parent / src_path).resolve()
                if target.is_dir():
                    return cls.load_monograph_chapters(target)
                if target.is_file():
                    if target.name in ("frontmatter.md", "index.md") and target.parent.is_dir():
                        return cls.load_monograph_chapters(target.parent)
                    return target.read_text(encoding="utf-8", errors="ignore")

        return None

    @classmethod
    def extract_sources_structure(
        cls, topic_body: str, wiki_dir: Path
    ) -> tuple[dict[str, list[str]], bool]:
        """
        Parses ## MBRAS Sources supporting flat, nested (###), 
        and deeply partitioned (####, #####) source hierarchies.
        """
        match = re.search(r"^##\s+MBRAS Sources\s*$(.*?)(?=^##\s+|\Z)", topic_body, re.MULTILINE | re.DOTALL)
        if not match:
            return {}, False

        section_text = match.group(1).strip()
        has_subtopics = bool(re.search(r"^#{3,5}\s+", section_text, re.MULTILINE))

        subtopics: dict[str, list[str]] = {}
        current_key = "_flat"
        parent_h3 = ""

        for line in section_text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue

            # Check for H3 heading (e.g., ### Malay, ### Borneo)
            h3_match = re.match(r"^###\s+([^\n]+)", line_str)
            if h3_match:
                parent_h3 = h3_match.group(1).strip()
                current_key = parent_h3
                subtopics.setdefault(current_key, [])
                continue

            # Check for H4 / H5 heading (e.g., #### Animals under ### Malay)
            h4_match = re.match(r"^#{4,5}\s+([^\n]+)", line_str)
            if h4_match:
                sub_label = h4_match.group(1).strip()
                current_key = f"{parent_h3} — {sub_label}" if parent_h3 else sub_label
                subtopics.setdefault(current_key, [])
                continue

            # Extract markdown links to publications
            links = re.findall(r"\[.*?\]\(\.\/([^)]+)\.md\)", line_str)
            if not links:
                continue

            chosen_pub_slug = None
            for slug in links:
                target_file = wiki_dir / f"{slug}.md"
                if cls.is_publication_file(target_file):
                    chosen_pub_slug = slug
                    break

            if not chosen_pub_slug:
                for slug in reversed(links):
                    target_file = wiki_dir / f"{slug}.md"
                    if target_file.is_file():
                        chosen_pub_slug = slug
                        break

            if chosen_pub_slug:
                subtopics.setdefault(current_key, []).append(chosen_pub_slug)

        return subtopics, has_subtopics

    @staticmethod
    def resolve_entity_category(fm: dict, topic_name: str) -> str:
        """
        Determines the normalized entity category (person, place, group, event, concept)
        using frontmatter properties, category aliases, and titular heuristics.
        """
        raw_cat = str(fm.get("type") or fm.get("category") or "").strip().lower()

        EVENT_ALIASES = {
            "conflict", "war", "battle", "treaty", "incident", "expedition",
            "rebellion", "revolt", "engagement", "conference", "coronation",
            "installation", "crisis", "affair", "dispute", "campaign",
        }
        PERSON_ALIASES = {"author", "contributor", "biography", "scholar", "official", "ruler"}
        PLACE_ALIASES = {"location", "toponym", "settlement", "state", "district", "island", "river", "mountain"}
        GROUP_ALIASES = {"community", "tribe", "ethnicity", "demographic", "collective", "people"}

        category = "concept"

        if raw_cat in ("event", "person", "place", "group", "concept"):
            category = raw_cat
        elif raw_cat in EVENT_ALIASES:
            category = "event"
        elif raw_cat in PERSON_ALIASES:
            category = "person"
        elif raw_cat in PLACE_ALIASES:
            category = "place"
        elif raw_cat in GROUP_ALIASES:
            category = "group"

        # Heuristic fallbacks for untyped stubs
        if category == "concept":
            name_words = topic_name.lower().split()

            if fm.get("is_contributor") is True or fm.get("is_author") is True:
                category = "person"
            elif any(
                title_word in name_words
                for title_word in ["sultan", "raja", "tunku", "tengku", "munshi", "dato'", "sheikh", "sir", "captain"]
            ):
                category = "person"
            elif any(
                w in name_words
                for w in ["war", "wars", "treaty", "engagement", "rebellion", "conference", "expedition"]
            ):
                category = "event"
            elif any(
                w in name_words
                for w in ["island", "islands", "river", "mount", "mountain", "gunong", "caves", "hill", "strait"]
            ):
                category = "place"
            elif any(
                pattern in topic_name.lower()
                for pattern in ["chinese in ", "dutch in ", "british in ", "indians in ", "bugis in ", "tribe", "people", "community", "settlers", "dayak", "iban", "bajau", "orang "]
            ):
                category = "group"

        return category