from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class BibliographicWork(BaseModel):
    """A published article, monograph, or review referenced in Index Malaysiana."""

    title: str
    author: str | None = None
    editors: str | None = None
    reviewer: str | None = None
    is_review: bool = False

    # Journal details
    journal_series: str | None = None  # "MB", "SB", "NQ", "Monograph", "Reprint"
    journal_full_name: str | None = None
    volume: int | None = None
    issue: str | None = None
    pages: str | None = None
    month: str | None = None
    year: int | None = None

    raw_citation: str = ""


class AuthorityRecord(BaseModel):
    """Canonical authority record for an entity, concept, or contributor."""

    id: str = Field(description="Namespaced identifier, e.g. 'person:tong-chee-kiong'")
    headword: str = Field(description="Canonical display name")
    category: Literal["person", "place", "concept", "event", "group", "publication"]
    is_contributor: bool = False
    aliases: list[str] = Field(default_factory=list)
    dates: str | None = None
    see: str | None = None
    see_also: list[str] = Field(default_factory=list)
    works_subject_of: list[BibliographicWork] = Field(default_factory=list)
    works_authored: list[BibliographicWork] = Field(default_factory=list)