import re
from pathlib import Path
from typing import List, Tuple

BOILERPLATE_PATTERNS = [
    r"digitized by the internet archive",
    r"gift of .*?carpentier",
    r"spottiswoode and shaw",
    r"reservation copy added",
    r"in usum academicum",
]

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text)

def clean_canonical_name(text: str) -> str:
    clean = re.sub(r"\s+", " ", text).strip(" ,.:;'\"")
    clean = re.sub(r"^(Mr\.|Sir|Captain|Major|Lord|Raja|Sultan|Dato|Datuk)\s+", "", clean, flags=re.IGNORECASE)
    return clean.strip()

def is_boilerplate(text: str) -> bool:
    if len(text.split()) < 20:  # Relaxed slightly for full paragraphs
        return True
    lower = text.lower()
    return any(re.search(pat, lower) for pat in BOILERPLATE_PATTERNS)

def extract_paragraphs_by_page(md_path: Path) -> List[Tuple[int, str]]:
    """Splits Markdown into page blocks, then into paragraphs."""
    raw_text = md_path.read_text(encoding="utf-8")
    matches = list(re.finditer(r'<span id="page-(\d+)"></span>', raw_text))

    if not matches:
        return [(1, p.strip()) for p in raw_text.split("\n\n") if not is_boilerplate(p)]

    paragraphs = []
    for i, match in enumerate(matches):
        p_num = int(match.group(1))
        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        
        page_content = raw_text[start_pos:end_pos]
        for p in page_content.split("\n\n"):
            clean_p = p.strip()
            if clean_p and not is_boilerplate(clean_p):
                paragraphs.append((p_num, clean_p))

    return paragraphs