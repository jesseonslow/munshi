from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


EntityCategory = Literal["person", "place", "event", "concept", "publication", "group"]
EntityTier = Literal["A", "B", "C"]


class OccurrenceRecord(BaseModel):
    """A verified mention of an entity in the primary corpus."""
    doc_id: str
    page_num: int | None = None
    context_snippet: str
    block_id: str | None = None
    source_type: Literal["ledger", "zvec_vector", "hybrid"] = "ledger"
    similarity_score: float | None = None


class EntityTarget(BaseModel):
    """An entity selected for synthesis evaluation."""
    entity_id: str
    canonical_name: str
    category: EntityCategory
    tier: EntityTier = "C"
    mention_count: int = 0
    is_curated: bool = False
    aliases: list[str] = Field(default_factory=list)


class AuthorityCitation(BaseModel):
    """Bibliographic citation extracted from Index Malaysiana."""
    author: str
    title: str
    journal_code: str
    volume: str
    raw_entry: str


class AuthorityRecord(BaseModel):
    """Authority data parsed from Index Malaysiana for an entity or concept."""
    id: str
    canonical_name: str
    category: str = "concept"
    is_collector_hub: bool = False
    aliases: list[str] = Field(default_factory=list)
    facets: list[str] = Field(default_factory=list)
    cross_references: list[str] = Field(default_factory=list)
    citations: list[AuthorityCitation] = Field(default_factory=list)


class SynthesisPayload(BaseModel):
    """Contextual bundle fed to the synthesis generator."""
    target: EntityTarget
    occurrences: list[OccurrenceRecord]
    authority: AuthorityRecord | None = None
    custom_instructions: str | None = None


class GeneratedArticle(BaseModel):
    """Output artifact produced by the synthesis pass."""
    entity_id: str
    slug: str
    markdown_content: str
    sources_referenced: list[str] = Field(default_factory=list)