"""Configuration settings for munshi-synthesizer."""
from __future__ import annotations

from pathlib import Path
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Dynamically resolve workspace root: apps/synthesizer/src/munshi_synthesizer/config.py -> 4 levels up
ROOT = Path(__file__).resolve().parents[4]


class SynthesizerConfig(BaseSettings):
    """Configuration settings for munshi-synthesizer."""

    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    wiki_dir: Path = Field(
        default_factory=lambda: ROOT / "wiki",
        validation_alias=AliasChoices("WIKI_DIR", "MUNSHI_WIKI_DIR"),
        description="Path to the wiki directory containing publication stubs and topic pages",
    )
    rerank_model_dir: Path = Field(
        default_factory=lambda: ROOT / "models/bge-reranker-base-onnx",
        validation_alias=AliasChoices("RERANK_MODEL_DIR", "MUNSHI_RERANK_MODEL_DIR"),
        description="Path to local ONNX model and tokenizer directory",
    )
    openrouter_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "DOCPROC_OPENROUTER_API_KEY"),
        description="OpenRouter API Key",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias=AliasChoices("OPENROUTER_BASE_URL", "DOCPROC_OPENROUTER_BASE_URL"),
        description="Base URL for OpenRouter API requests",
    )
    synthesis_model_id: str = Field(
        default="google/gemini-2.5-pro",
        validation_alias=AliasChoices("SYNTHESIS_MODEL", "MUNSHI_SYNTHESIS_MODEL"),
        description="LLM endpoint used for historiographical literature review generation",
    )
    synthesis_temperature: float = Field(
        default=0.25,
        description="Sampling temperature for synthesis",
    )
    rerank_top_k: int = Field(
        default=5,
        description="Threshold of sources above which reranking and stratification trigger",
    )

    @field_validator("wiki_dir", "rerank_model_dir", mode="before")
    @classmethod
    def _anchor_to_root(cls, v: str | Path | None) -> Path | None:
        if v is None:
            return None
        p = Path(v)
        return p if p.is_absolute() else ROOT / p