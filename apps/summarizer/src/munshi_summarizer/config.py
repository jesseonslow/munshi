"""Configuration settings for munshi-publication-summarizer."""
from __future__ import annotations

from pathlib import Path
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve monorepo workspace root:
# apps/summarizer/src/munshi_summarizer/config.py -> 4 levels up to workspace root
ROOT = Path(__file__).resolve().parents[4]


class SummarizerConfig(BaseSettings):
    """Configuration for publication summarization loaded from root .env."""

    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Monorepo Topology
    wiki_dir: Path = Field(
        default_factory=lambda: ROOT / "wiki",
        validation_alias=AliasChoices("WIKI_DIR", "MUNSHI_WIKI_DIR"),
        description="Target directory containing wiki Markdown articles",
    )
    sources_dir: Path = Field(
        default_factory=lambda: ROOT / "sources",
        validation_alias=AliasChoices("DATA_DIR", "SOURCES_DIR", "MUNSHI_DATA_DIR"),
        description="Directory containing stitched source markdown files",
    )

    # API & Provider Settings
    openrouter_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "OPENROUTER_API_KEY",
            "DOCPROC_OPENROUTER_API_KEY",
        ),
        description="OpenRouter API Key",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias=AliasChoices(
            "OPENROUTER_BASE_URL",
            "DOCPROC_OPENROUTER_BASE_URL",
        ),
        description="Base URL for OpenRouter completions",
    )

    # Model Presets
    summarizer_model_id: str = Field(
        default="qwen/qwen3.5-flash-02-23",
        validation_alias=AliasChoices(
            "SUMMARIZER_MODEL",
            "SUMMARISER_MODEL",
            "SUMMARY_MODEL_ID",
            "MUNSHI_SUMMARIZER_MODEL",
        ),
        description="OpenRouter model slug for publication summarization",
    )
    temperature: float = Field(
        default=0.2,
        description="Sampling temperature for synthesis adherence",
    )

    @field_validator("wiki_dir", "sources_dir", mode="before")
    @classmethod
    def _anchor_to_root(cls, v: str | Path | None) -> Path | None:
        """Anchors relative paths from .env (e.g. 'wiki', 'sources') to monorepo ROOT."""
        if v is None:
            return None
        p = Path(v)
        return p if p.is_absolute() else ROOT / p


# Backward-compatible alias for British spelling in existing modules
SummariserConfig = SummarizerConfig