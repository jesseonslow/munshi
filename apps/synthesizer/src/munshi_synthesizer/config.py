"""Configuration settings for munshi-synthesizer."""

from __future__ import annotations

from pathlib import Path
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Dynamically resolve workspace root:
# apps/synthesizer/src/munshi_synthesizer/config.py -> 4 levels up to munshi/
ROOT = Path(__file__).resolve().parents[4]


class SynthesizerConfig(BaseSettings):
    """Configuration settings for munshi-synthesizer."""

    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database & Index Paths
    ledger_db_path: Path = Field(
        default_factory=lambda: ROOT / "ledger/entity_ledger.db",
        validation_alias=AliasChoices("LEDGER_DB", "MUNSHI_LEDGER_DB", "LEDGER_DB_PATH"),
        description="Path to the SQLite entity occurrence ledger",
    )
    authority_index_path: Path = Field(
        default_factory=lambda: ROOT / "ledger/authority_index.json",
        validation_alias=AliasChoices("AUTHORITY_INDEX", "MUNSHI_AUTHORITY_INDEX"),
        description="Path to the parsed Index Malaysiana authority JSON",
    )
    wiki_out_dir: Path = Field(
        default_factory=lambda: ROOT / "wiki",
        validation_alias=AliasChoices("WIKI_DIR", "MUNSHI_WIKI_DIR", "WIKI_OUT_DIR"),
        description="Flat output directory for generated markdown articles",
    )

    # API & Provider Configuration
    openrouter_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "DOCPROC_OPENROUTER_API_KEY"),
        description="OpenRouter API Key",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias=AliasChoices("OPENROUTER_BASE_URL", "DOCPROC_OPENROUTER_BASE_URL"),
        description="Base URL for OpenRouter completions",
    )

    # Model Presets
    synthesis_model_id: str = Field(
        default="qwen/qwen3.8-27b",
        validation_alias=AliasChoices("SYNTHESIS_MODEL", "MUNSHI_SYNTHESIS_MODEL"),
        description="Model slug on OpenRouter for OKF narrative compilation",
    )
    synthesis_temperature: float = Field(
        default=0.2,
        description="Sampling temperature for narrative synthesis",
    )
    rerank_model: str = Field(
        default="BAAI/bge-reranker-base",
        validation_alias=AliasChoices("RERANK_MODEL", "SYNTHESIZER_RERANK_MODEL"),
        description="HuggingFace model for passage reranking",
    )

    # Vector Retrieval (zvec)
    zvec_data_dir: Path = Field(
        default_factory=lambda: ROOT / "data",
        validation_alias=AliasChoices("DATA_DIR", "MUNSHI_DATA_DIR"),
        description="Directory containing stitched markdown files and .zvec-grep index",
    )
    zvec_top_k: int = Field(
        default=10,
        description="Number of semantic vector passages to retrieve via zvec-grep in parallel",
    )
    enable_zvec: bool = Field(
        default=True,
        description="Toggle parallel zvec-grep retrieval alongside SQLite ledger",
    )
    
    @field_validator("ledger_db_path", "authority_index_path", "wiki_out_dir", "zvec_data_dir", mode="before")
    @classmethod
    def _anchor_to_root(cls, v: str | Path | None) -> Path | None:
        if v is None:
            return None
        p = Path(v)
        return p if p.is_absolute() else ROOT / p