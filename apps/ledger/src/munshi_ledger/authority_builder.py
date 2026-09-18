from __future__ import annotations

import json
import re
from pathlib import Path
from munshi_ledger.parser import clean_canonical_name, slugify
from munshi_ledger.schema_authority import AuthorityRecord, BibliographicWork

MONTH_MAP = {
    "Ja": "January", "F": "February", "Mr": "March", "Ap": "April",
    "My": "May", "Je": "June", "Jl": "July", "Ag": "August",
    "S": "September", "O": "October", "N": "November", "D": "December",
}

# Matches citations like: "Jakeman, R.W. Pahang Kanun. MB 24(3)" or "MB 76(2): 124–126 D 2003"
CITATION_DETAILED_RE = re.compile(
    r"^(?P<text>.*?)"
    r"(?P<series>MB|SB|NQ|Monograph|Reprint)\s+"
    r"(?P<vol>\d+)"
    r"(?:\((?P<issue>[^)]+)\))?"
    r"(?::\s*(?P<pages>[\d–-]+))?"
    r"(?:\s+(?P<month>[A-Z][a-z]?))?"
    r"(?:\s+(?P<year>\d{4}))?"
    r"(?:\s*\{R\})?$"
)

REVIEWER_RE = re.compile(r"\{Reviewed\s+([^}]+)\}")
EDITOR_RE = re.compile(r"(?i)\bEd\.\s+([^{]+)")

# Headword matching: **Title**, ## Title
HEADWORD_RE = re.compile(r"^(?:##\s+)?\*\*(?P<name>[^*]+)\*\*(?:\s+(?P<trailer>.*))?$|^(?:##\s+)(?P<hname>[^*]+)$")
INLINE_SEE_RE = re.compile(r"^(?P<name>[A-Za-z0-9\s,\(\)'-]+?)\s+\*?see\*?\s+(?P<target>.+)$", re.IGNORECASE)
SEE_RE = re.compile(r"(?i)\bsee\s+([^/]+)")
SEE_ALSO_RE = re.compile(r"(?i)\band\s+see\s+([^/]+)")
DATE_EXTRACT_RE = re.compile(r"\b(r\.\s*\d{4}[–-]\d{2,4}|\d{4}[–-]\d{2,4})\b")

# Matches variable-length OCR underscores (3 or more)
REPEAT_AUTHOR_RE = re.compile(r"^[_\s–—]{3,}\s*")

KNOWN_PLACES = {
    "aceh", "achin", "malacca", "melaka", "singapore", "penang", "perak", "selangor", 
    "pahang", "kedah", "johor", "johore", "kelantan", "terengganu", "trengganu", "borneo", 
    "sarawak", "sabah", "brunei", "sumatra", "java", "celebes", "kuala lumpur", "patani", 
    "siam", "thailand", "burma", "cambodia", "indo-china", "vietnam", "ceylon", "india", 
    "bencoolen", "batavia", "djakarta", "jakarta", "manila", "philippines", "champa", "pasai"
}

IGNORE_SECTIONS = {"internal numbering scheme", "numbering", "references & footnotes"}


def resolve_journal_name(series: str, volume: int | None, year: int | None) -> str:
    if series == "SB":
        return "Journal of the Straits Branch of the Royal Asiatic Society"
    if series == "MB":
        if volume is not None:
            if volume >= 37:
                return "Journal of the Malaysian Branch of the Royal Asiatic Society"
            return "Journal of the Malayan Branch of the Royal Asiatic Society"
        if year is not None:
            if year >= 1964:
                return "Journal of the Malaysian Branch of the Royal Asiatic Society"
            return "Journal of the Malayan Branch of the Royal Asiatic Society"
        return "Journal of the Malayan/Malaysian Branch of the Royal Asiatic Society"
    if series == "NQ":
        return "Notes and Queries"
    return series


def parse_citation(line: str, fallback_author: str | None = None) -> BibliographicWork | None:
    match = CITATION_DETAILED_RE.match(line.strip())
    if not match:
        return None

    raw_body = match.group("text").strip()
    series = match.group("series")
    vol_str = match.group("vol")
    issue = match.group("issue")
    pages = match.group("pages")
    month_code = match.group("month")
    year_str = match.group("year")

    vol = int(vol_str) if vol_str else None
    year = int(year_str) if year_str else None
    month = MONTH_MAP.get(month_code, month_code)

    reviewer = None
    rev_match = REVIEWER_RE.search(raw_body)
    if rev_match:
        reviewer = rev_match.group(1).strip()
        raw_body = REVIEWER_RE.sub("", raw_body).strip()

    editors = None
    ed_match = EDITOR_RE.search(raw_body)
    if ed_match:
        editors = ed_match.group(1).strip(" .")
        raw_body = raw_body[:ed_match.start()].strip(" .")

    author = fallback_author
    title = raw_body.strip(" .")

    # If no fallback author was provided, parse author prefix from "Author Name. Title"
    if not fallback_author and "." in raw_body:
        parts = raw_body.split(".", 1)
        potential_author = parts[0].strip()
        if len(potential_author.split()) <= 4:
            author = potential_author
            title = parts[1].strip()

    return BibliographicWork(
        title=title,
        author=author,
        editors=editors,
        reviewer=reviewer,
        is_review=bool(reviewer or "{R}" in line),
        journal_series=series,
        journal_full_name=resolve_journal_name(series, vol, year),
        volume=vol,
        issue=issue,
        pages=pages,
        month=month,
        year=year,
        raw_citation=line.strip(),
    )


def parse_subject_index(index_text: str) -> dict[str, AuthorityRecord]:
    """Parses index.md into concept/place/person authority records."""
    records: dict[str, AuthorityRecord] = {}
    current_record: AuthorityRecord | None = None
    last_author: str | None = None

    for line in index_text.splitlines():
        line = line.strip()
        if not line or line.startswith("---"):
            continue

        line_clean = re.sub(r'<span[^>]*></span>\s*', '', line).strip()
        if not line_clean:
            continue

        # Skip alphabet letters (A, B, C...) and structural backmatter
        if (len(line_clean) == 1 and line_clean.isalpha()) or line_clean.lower() in IGNORE_SECTIONS:
            current_record = None
            last_author = None
            continue

        # 1. Match Headwords (## Header or **Header**)
        hw_match = HEADWORD_RE.match(line_clean)
        if hw_match:
            raw_title = (hw_match.group("name") or hw_match.group("hname") or "").strip()
            trailer = (hw_match.group("trailer") or "").strip()

            if len(raw_title) == 1 and raw_title.isalpha():
                continue
            if raw_title.lower() in IGNORE_SECTIONS:
                current_record = None
                continue

            date_m = DATE_EXTRACT_RE.search(raw_title)
            dates = date_m.group(1) if date_m else None

            canonical = DATE_EXTRACT_RE.sub("", raw_title)
            canonical = re.sub(r"\(\s*\)", "", canonical)
            canonical = clean_canonical_name(canonical.strip(" ,.:;'\""))
            if not canonical:
                continue

            raw_lower = canonical.lower()
            category = "concept"
            if raw_lower in KNOWN_PLACES or any(t in raw_lower for t in ["river", "mount", "island", "district", "caves", "hill", "peninsula", "valley", "settlement"]):
                category = "place"
            elif dates or any(t in raw_lower for t in ["sultan", "raja", "sir", "sheikh", "dr", "tun", "kapitan", "major", "colonel", "reverend"]):
                category = "person"

            rec_id = f"{category}:{slugify(canonical)}"

            see_m = SEE_RE.search(trailer)
            see_target = see_m.group(1).strip() if see_m else None

            current_record = AuthorityRecord(
                id=rec_id,
                headword=canonical,
                category=category,
                is_contributor=False,
                dates=dates,
                see=see_target,
                aliases=[raw_title] if raw_title != canonical else [],
            )
            records[rec_id] = current_record
            last_author = None
            continue

        # 2. Match Inline Redirects: "Acridiidae *see* Orthoptera"
        inline_see = INLINE_SEE_RE.match(line_clean)
        if inline_see and not CITATION_DETAILED_RE.search(line_clean):
            raw_title = inline_see.group("name").strip()
            see_target = inline_see.group("target").strip(" *.")
            canonical = clean_canonical_name(raw_title)
            if canonical and len(canonical) > 1:
                rec_id = f"concept:{slugify(canonical)}"
                records[rec_id] = AuthorityRecord(
                    id=rec_id,
                    headword=canonical,
                    category="concept",
                    is_contributor=False,
                    see=see_target,
                )
            current_record = None
            last_author = None
            continue

        if not current_record:
            continue

        # 3. Check for "and see" / "see also"
        see_also_m = SEE_ALSO_RE.search(line_clean)
        if see_also_m:
            targets = [t.strip() for t in see_also_m.group(1).split("//")]
            current_record.see_also.extend([t for t in targets if t])
            continue

        # 4. Handle repeated authors with variable-length underscores (____ to _______)
        citation_line = line_clean
        same_author = False
        if REPEAT_AUTHOR_RE.match(citation_line):
            citation_line = REPEAT_AUTHOR_RE.sub("", citation_line).strip()
            same_author = True

        work = parse_citation(citation_line, fallback_author=last_author if same_author else None)
        if work:
            if not same_author and work.author:
                last_author = work.author
            current_record.works_subject_of.append(work)

    return records


def merge_authors_md(authors_text: str, records: dict[str, AuthorityRecord]) -> None:
    """Parses authors.md and links authored publications to authority entities."""
    current_author_rec: AuthorityRecord | None = None
    last_author_name: str | None = None

    for raw_line in authors_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("---"):
            continue

        line_clean = re.sub(r'<span[^>]*></span>\s*', '', line).strip()
        if (len(line_clean) == 1 and line_clean.isalpha()) or line_clean.lower() in IGNORE_SECTIONS:
            current_author_rec = None
            continue

        # Header line: **Author Name**
        if line_clean.startswith("**") and ("**" in line_clean[2:]):
            header_content = line_clean.split("**")[1].strip()
            if len(header_content) == 1 and header_content.isalpha():
                continue

            date_m = DATE_EXTRACT_RE.search(header_content)
            dates = date_m.group(1) if date_m else None

            canonical = DATE_EXTRACT_RE.sub("", header_content)
            canonical = re.sub(r"\(\s*\)", "", canonical)
            clean_name = clean_canonical_name(canonical.strip(" ,.:;'\""))
            if not clean_name:
                continue

            rec_id = f"person:{slugify(clean_name)}"
            if rec_id in records:
                current_author_rec = records[rec_id]
                current_author_rec.is_contributor = True
                if not current_author_rec.dates and dates:
                    current_author_rec.dates = dates
            else:
                current_author_rec = AuthorityRecord(
                    id=rec_id,
                    headword=clean_name,
                    category="person",
                    is_contributor=True,
                    dates=dates,
                    aliases=[header_content] if header_content != clean_name else [],
                )
                records[rec_id] = current_author_rec

            last_author_name = current_author_rec.headword
            continue

        # Citation lines in authors.md
        if current_author_rec:
            citation_line = line_clean
            if REPEAT_AUTHOR_RE.match(citation_line):
                citation_line = REPEAT_AUTHOR_RE.sub("", citation_line).strip()

            work = parse_citation(citation_line, fallback_author=last_author_name)
            if work:
                current_author_rec.works_authored.append(work)


def build_authority_catalog(subject_md_path: Path, authors_md_path: Path | None, out_json_path: Path) -> int:
    if not subject_md_path.exists():
        raise FileNotFoundError(f"Subject index not found: {subject_md_path}")

    records = parse_subject_index(subject_md_path.read_text(encoding="utf-8"))

    if authors_md_path and authors_md_path.exists():
        merge_authors_md(authors_md_path.read_text(encoding="utf-8"), records)

    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = [rec.model_dump(exclude_none=True) for rec in records.values()]
    out_json_path.write_text(json.dumps(serialized, indent=2, ensure_ascii=False), encoding="utf-8")

    return len(serialized)