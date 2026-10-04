from __future__ import annotations

from pydantic import BaseModel, Field


class ReassignAuthorPayload(BaseModel):
    publication_slug: str = Field(..., description="Slug of the article being reassigned")
    old_author_name: str = Field(..., description="e.g. 'W. Cheah'")
    new_author_name: str = Field(..., description="e.g. 'Cheah Boon Kheng'")
    new_author_slug: str = Field(..., description="e.g. 'cheah-boon-kheng'")
    old_author_slug: str | None = Field(None, description="e.g. 'w-cheah'")


class MergeAuthorsPayload(BaseModel):
    source_author_slug: str = Field(..., description="Duplicate slug to retire")
    target_author_slug: str = Field(..., description="Canonical slug to absorb works")
    keep_as_alias: bool = Field(True, description="Add source name as alias on target")


class FixSourcePathPayload(BaseModel):
    slug: str = Field(..., description="Publication slug")
    new_path: str = Field(..., description="Relative or absolute target source path")
    new_doc_id: str | None = Field(None, description="Canonical document ID")


class MutationResult(BaseModel):
    status: str
    action: str
    modified_files: list[str]
    detail: str | None = None


class BatchReassignPayload(BaseModel):
    old_author_name: str = Field(..., description="e.g. 'H.C. Clifford'")
    new_author_name: str = Field(..., description="e.g. 'Sir Hugh Charles Clifford'")
    new_author_slug: str = Field(..., description="e.g. 'hugh-clifford'")
    old_author_slug: str | None = Field(None, description="e.g. 'hc-clifford'")