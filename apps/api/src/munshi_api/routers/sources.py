from fastapi import APIRouter, Depends
from munshi_api.config import ApiConfig
from munshi_api.models.sources import SourceValidationReport
from munshi_api.services.source_matcher import SourceMatcherEngine

router = APIRouter(prefix="/api/sources", tags=["Source Operations"])


def get_source_engine():
    config = ApiConfig()
    return SourceMatcherEngine(config.wiki_dir, config.sources_dir)


@router.get("/validate/{slug}", response_model=SourceValidationReport)
def validate_source(slug: str, engine: SourceMatcherEngine = Depends(get_source_engine)):
    return engine.validate_publication_source(slug)