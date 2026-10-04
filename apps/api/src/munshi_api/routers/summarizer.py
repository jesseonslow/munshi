"""FastAPI endpoint exposing publication summarization runs."""
from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from munshi_api.config import ApiConfig

router = APIRouter(prefix="/api/summarizer", tags=["Summarizer"])


class SummarizeRequest(BaseModel):
    slugs: list[str]
    force: bool = False
    model_override: str | None = None


def get_config() -> ApiConfig:
    return ApiConfig()


@router.post("/run")
def run_summarizer(payload: SummarizeRequest, config: ApiConfig = Depends(get_config)):
    # Lazy import to avoid startup circular imports or hard crashes if summarizer is missing
    try:
        from munshi_summarizer.config import SummarizerConfig
        from munshi_summarizer.summarizer import PublicationSummarizer
    except ModuleNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail=(
                "munshi_summarizer package is not installed in the API environment. "
                "Run `uv add --path ../summarizer munshi-summarizer` in apps/api."
            ),
        ) from e

    sum_config = SummarizerConfig()
    if payload.model_override:
        sum_config.summarizer_model_id = payload.model_override

    engine = PublicationSummarizer(sum_config)
    results = []

    for slug in payload.slugs:
        wiki_file = config.wiki_dir / f"{slug}.md"
        if not wiki_file.exists():
            raise HTTPException(status_code=404, detail=f"Article {slug}.md does not exist.")

        success = engine.process_wiki_article(wiki_file, force=payload.force, execute=True)
        results.append({"slug": slug, "success": success})

    return {"status": "complete", "processed": results}