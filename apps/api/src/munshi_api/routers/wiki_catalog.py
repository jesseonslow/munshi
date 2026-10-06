from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from munshi_api.config import ApiConfig

router = APIRouter(prefix="/api/wiki", tags=["Wiki Catalog"])


class WikiItemSummary(BaseModel):
    slug: str
    title: str
    type: str
    article_type: str | None = None
    authors: list[str] = []
    year: Any = None
    summarized: bool = False
    source_doc: str | None = None
    source_path: str | None = None


class WikiArticleDetail(BaseModel):
    slug: str
    frontmatter: dict[str, Any]
    body: str


class WikiListResponse(BaseModel):
    total: int
    items: list[WikiItemSummary]


def get_config() -> ApiConfig:
    return ApiConfig()


@router.get("/articles", response_model=WikiListResponse)
def list_wiki_articles(
    type: str | None = None,
    article_type: str | None = None,
    summarized: bool | None = None,
    search: str | None = None,
    config: ApiConfig = Depends(get_config),
):
    items: list[WikiItemSummary] = []
    if not config.wiki_dir.exists():
        return WikiListResponse(total=0, items=[])

    for f in config.wiki_dir.glob("*.md"):
        try:
            raw = f.read_text(encoding="utf-8")
            if not raw.startswith("---"):
                continue
            parts = raw.split("---", 2)
            fm = yaml.safe_load(parts[1]) or {}

            item_type = fm.get("type", "concept")
            if type and item_type != type:
                continue

            item_art_type = fm.get("article_type")
            if article_type and item_art_type != article_type:
                continue

            is_sum = bool(fm.get("summarized") or fm.get("summarised"))
            if summarized is not None and is_sum != summarized:
                continue

            title = fm.get("title", f.stem)
            if search and search.lower() not in title.lower() and search.lower() not in f.stem.lower():
                continue

            items.append(
                WikiItemSummary(
                    slug=f.stem,
                    title=title,
                    type=item_type,
                    article_type=item_art_type,
                    authors=fm.get("authors") or [],
                    year=fm.get("year"),
                    summarized=is_sum,
                    source_doc=fm.get("source_doc"),
                    source_path=fm.get("source_path"),
                )
            )
        except Exception:
            continue

    items.sort(key=lambda x: str(x.year or 9999))
    return WikiListResponse(total=len(items), items=items)


@router.get("/articles/{slug}", response_model=WikiArticleDetail)
def get_wiki_article_detail(slug: str, config: ApiConfig = Depends(get_config)):
    file_path = config.wiki_dir / f"{slug}.md"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Article not found")

    raw = file_path.read_text(encoding="utf-8")
    parts = raw.split("---", 2)
    fm = yaml.safe_load(parts[1]) if len(parts) >= 3 else {}
    body = parts[2] if len(parts) >= 3 else raw

    return WikiArticleDetail(slug=slug, frontmatter=fm, body=body)