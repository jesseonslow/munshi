from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class BrokenLinkItem(BaseModel):
    target_slug: str
    referenced_in: list[str]
    hit_count: int

class SplitAuthorCluster(BaseModel):
    cluster_key: str
    slugs: list[str]

class SourceMismatchReport(BaseModel):
    wiki_slug: str
    current_source_path: str | None
    current_source_doc: str | None
    error_type: Literal[
        "missing_source_field",
        "file_not_found",
        "fragment_target",
        "coordinate_mismatch",
        "neural_mismatch",
    ]
    detail: str
    suggested_source_path: str | None = None
    suggested_doc_id: str | None = None
    confidence: float = 0.0

class GraphHealthReport(BaseModel):
    total_entities: int
    broken_link_count: int
    broken_links: list[BrokenLinkItem]
    potential_split_authors: list[SplitAuthorCluster]
    source_mismatches: list[SourceMismatchReport] = []

class JournalIssueRecord(BaseModel):
    master_no: int = Field(..., description="Sequential Master Issue Number (1-329)")
    series: str = Field(..., description="'SB' (Straits Branch) or 'MB' (Malayan/Malaysian Branch)")
    volume: str = Field(..., description="Volume number or identifier")
    issue: str = Field(..., description="Part/issue string, e.g. '1', '2', '3 & 4', or empty")
    nominal_month: str | None = None
    nominal_year: int | None = None
    notes: str | None = None