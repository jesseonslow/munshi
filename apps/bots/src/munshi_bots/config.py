"""Configuration settings for munshi-bots loaded from root .env."""
from __future__ import annotations

from pathlib import Path
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Dynamically resolve workspace root:
# apps/bots/src/munshi_bots/config.py -> 4 levels up to workspace root (/home/jesse/Code/munshi)
ROOT = Path(__file__).resolve().parents[4]


class BotConfig(BaseSettings):
    """Bot runner configuration and credentials."""

    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
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

    # Monorepo Topology
    wiki_dir: Path = Field(
        default_factory=lambda: ROOT / "wiki",
        validation_alias=AliasChoices("WIKI_DIR", "MUNSHI_WIKI_DIR"),
        description="Target directory containing wiki Markdown articles",
    )
    triage_dir: Path = Field(
        default_factory=lambda: ROOT / "triage",
        validation_alias=AliasChoices("TRIAGE_DIR", "MUNSHI_TRIAGE_DIR"),
        description="Directory for append-only JSONL audit logs",
    )
    policies_dir: Path = Field(
        default_factory=lambda: ROOT / "apps/bots/policies",
        validation_alias=AliasChoices("POLICIES_DIR", "MUNSHI_POLICIES_DIR"),
        description="Directory containing policy markdown files",
    )

    # Model Defaults
    default_model: str = Field(
        default="qwen/qwen3.8-flash",
        validation_alias=AliasChoices(
            "BOT_MODEL",
            "TAXONOMY_MODEL",
            "LEDGER_NER_MODEL_ID",
        ),
        description="Default model for bot reasoning passes",
    )

    @field_validator("wiki_dir", "triage_dir", "policies_dir", mode="before")
    @classmethod
    def _anchor_to_root(cls, v: str | Path | None) -> Path | None:
        """Anchors relative paths from .env to monorepo ROOT."""
        if v is None:
            return None
        p = Path(v)
        return p if p.is_absolute() else ROOT / p