from __future__ import annotations

from fastapi import APIRouter, Depends
from munshi_api.config import ApiConfig
from munshi_api.models.janitor import (
    FixSourcePathPayload,
    MutationResult,
    ReassignAuthorPayload,
)
from munshi_api.services.janitor_engine import JanitorEngine

router = APIRouter(prefix="/api/janitor", tags=["Janitor Operations"])


def get_janitor_engine() -> JanitorEngine:
    config = ApiConfig()
    return JanitorEngine(config.wiki_dir)


@router.post("/reassign-author", response_model=MutationResult)
def reassign_author(
    payload: ReassignAuthorPayload,
    engine: JanitorEngine = Depends(get_janitor_engine),
) -> MutationResult:
    """Atomically reattributes a publication and synchronizes author bibliographies and TOCs."""
    return engine.reassign_author(payload)


@router.post("/fix-source-path", response_model=MutationResult)
def fix_source_path(
    payload: FixSourcePathPayload,
    engine: JanitorEngine = Depends(get_janitor_engine),
):
    return engine.fix_source_path(payload.slug, payload.new_path, payload.new_doc_id)

@router.post("/batch-reassign", response_model=MutationResult)
def batch_reassign(
    payload: BatchReassignPayload,
    engine: JanitorEngine = Depends(get_janitor_engine),
):
    return engine.batch_reassign_author(payload)