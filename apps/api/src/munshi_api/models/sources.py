from __future__ import annotations
from pydantic import BaseModel, Field


class SourceValidationReport(BaseModel):
    wiki_slug: str
    current_source_path: str | None
    is_valid: bool
    reason: str
    proposed_source_path: str | None = None
    confidence: float = 0.0


class MatchSourcesPayload(BaseModel):
    wiki_slug: str | None = Field(None, description="Target specific stub, or null for all unmatched")
    threshold: float = Field(65.0, description="Minimum confidence score for automatic match")
    execute: bool = Field(False, description="Apply matches in-place to frontmatter")