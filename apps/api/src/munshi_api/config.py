"""Configuration settings for munshi-api."""
from __future__ import annotations

from pathlib import Path
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Dynamically resolve root: apps/api/src/munshi_api/config.py -> 4 levels up to workspace root
ROOT = Path(__file__).resolve().parents[4]


class ApiConfig(BaseSettings):
    """Configuration loaded from monorepo root .env."""

    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Directories
    wiki_dir: Path = Field(
        default_factory=lambda: ROOT / "wiki",
        validation_alias=AliasChoices("WIKI_DIR", "MUNSHI_WIKI_DIR"),
    )
    sources_dir: Path = Field(
        default_factory=lambda: ROOT / "sources",
        validation_alias=AliasChoices("DATA_DIR", "SOURCES_DIR", "MUNSHI_DATA_DIR"),
    )
    db_dir: Path = Field(
        default_factory=lambda: ROOT / "db",
        validation_alias=AliasChoices("DB_DIR", "MUNSHI_DB_DIR"),
    )

    # Database Files
    ledger_db_path: Path = Field(
        default_factory=lambda: ROOT / "db/entity_ledger.db",
        validation_alias=AliasChoices("LEDGER_DB", "MUNSHI_LEDGER_DB"),
    )
    seed_db_path: Path = Field(
        default_factory=lambda: ROOT / "db/seed_dictionary.db",
        validation_alias=AliasChoices("SEED_DB", "MUNSHI_SEED_DB"),
    )

    # Service Bindings
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)

    @field_validator("wiki_dir", "sources_dir", "db_dir", "ledger_db_path", "seed_db_path", mode="before")
    @classmethod
    def _anchor_to_root(cls, v: str | Path | None) -> Path | None:
        if v is None:
            return None
        p = Path(v)
        return p if p.is_absolute() else ROOT / p