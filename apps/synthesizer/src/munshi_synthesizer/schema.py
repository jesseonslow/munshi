"""Data schemas for publication sources and synthesis outputs."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PublicationSource(BaseModel):
    """Structured evidence parsed from a publication markdown file."""
    slug: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | str = "n.d."
    journal_code: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    jstor: str | None = None
    project_muse: str | None = None
    lede: str = ""
    summary: str = ""
    key_findings: list[str] = Field(default_factory=list)
    context_notes: list[str] = Field(default_factory=list)
    relevance_score: float = 0.0

    @property
    def author_display(self) -> str:
        if not self.authors:
            return "Anon"
        if len(self.authors) == 1:
            return self.authors[0]
        if len(self.authors) == 2:
            return f"{self.authors[0]} and {self.authors[1]}"
        return f"{self.authors[0]} et al."

    @property
    def citation_author(self) -> str:
        """Returns the primary surname for compact parenthetical labels."""
        if not self.authors:
            return "Anon"
        first = self.authors[0].strip()
        if "," in first:
            return first.split(",")[0].strip()
        parts = first.split()
        return parts[-1] if parts else "Anon"

    @property
    def journal_citation(self) -> str:
        vol = f" {self.volume}" if self.volume else ""
        iss = f"({self.issue})" if self.issue else ""
        pg = f": {self.pages}" if self.pages else ""
        jcode = f" *{self.journal_code}*" if self.journal_code else ""
        return f"{jcode}{vol}{iss}{pg}".strip()

    @property
    def aggregator_badge(self) -> str:
        """Generates standard HTML pill anchors for external aggregators."""
        if self.jstor:
            return (
                f'<a href="{self.jstor}" class="aggregator-link" '
                f'target="_blank" rel="noopener noreferrer">Read on JSTOR</a>'
            )
        if self.project_muse:
            return (
                f'<a href="{self.project_muse}" class="aggregator-link" '
                f'target="_blank" rel="noopener noreferrer">Read on Project MUSE</a>'
            )
        return ""