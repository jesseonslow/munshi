"""Pipeline configuration via Pydantic Settings."""

from __future__ import annotations

from pathlib import Path
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Dynamically resolve workspace root:
# apps/docproc/src/munshi_docproc/config.py -> parents[4] is the monorepo root
ROOT = Path(__file__).resolve().parents[4]


class PipelineConfig(BaseSettings):
    """Configuration for the document processing pipeline."""

    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Input / Output Topology
    pdf_path: Path = Path(".")
    out_dir: Path = Field(
        default_factory=lambda: ROOT / "data",
        validation_alias=AliasChoices("DATA_DIR", "DOCPROC_OUT_DIR"),
        description="Target directory for processed JSONL and stitched Markdown",
    )
    max_pages: int | None = None
    page_range: str | None = None
    force: bool = False

    # Layout & Margin Thresholds
    boilerplate_threshold: float = Field(default=0.3)
    footnote_zone_top: float = Field(default=0.72)
    footnote_zone_bottom: float = Field(default=1.0)
    header_zone_bottom: float = Field(default=0.10)
    footer_zone_top: float = Field(default=0.80)

    # Language Detection
    min_lang_chars: int = Field(default=30)
    lang_set: list[str] = Field(default=["en", "ms", "zh", "ar"])

    # Provider & Model Settings
    llm_provider: str = Field(
        default="openrouter",
        validation_alias=AliasChoices("LLM_PROVIDER", "DOCPROC_LLM_PROVIDER"),
        description="LLM provider: openrouter, bedrock, or model_studio",
    )
    openrouter_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "DOCPROC_OPENROUTER_API_KEY"),
        description="OpenRouter API key",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias=AliasChoices("OPENROUTER_BASE_URL", "DOCPROC_OPENROUTER_BASE_URL"),
    )
    openrouter_ocr_model_id: str = Field(
        default="qwen/qwen-2.5-vl-72b-instruct",
        validation_alias=AliasChoices(
            "OCR_MODEL",
            "DOCPROC_OCR_MODEL",
            "DOCPROC_OPENROUTER_OCR_MODEL_ID",
        ),
        description="Vision model ID for OCR / page extraction",
    )
    openrouter_reasoning_model_id: str = Field(
        default="qwen/qwen-2.5-7b-instruct",
        validation_alias=AliasChoices(
            "REASONING_MODEL",
            "DOCPROC_REASONING_MODEL",
            "DOCPROC_OPENROUTER_REASONING_MODEL_ID",
        ),
        description="Text model ID for metadata extraction and classification",
    )

    @field_validator("ledger_db_path", "authority_index_path", "wiki_out_dir", "zvec_data_dir", mode="before")
    @classmethod
    def _anchor_to_root(cls, v: str | Path | None) -> Path | None:
        if v is None:
            return None
        p = Path(v)
        return p if p.is_absolute() else ROOT / p

    # Execution Parameters
    qwen3vl_dpi: int = Field(default=200)
    qwen3vl_max_tokens: int = Field(default=4096)
    qwen3vl_max_workers: int = Field(
        default=8,
        validation_alias=AliasChoices(
            "MAX_WORKERS",
            "DOCPROC_MAX_WORKERS",
            "DOCPROC_QWEN3VL_MAX_WORKERS",
        ),
        description="Max parallel API calls during vision extraction",
    )

    qwen3vl_system_prompt: str = Field(
        default="""\
You are a document OCR engine. Convert the page image to clean Markdown text.
Rules:
- Preserve the reading order exactly as it appears on the page.
- Use **bold** and *italic* for emphasis where the original uses bold/italic.
- Use # for main headings, ## for subheadings.
- Use > for block quotes.
- Separate each distinct paragraph or entry with a blank line.
- In journals or diaries, treat each date entry as the start of a new paragraph — always insert a blank line before it.
- Preserve natural paragraph breaks from the source document; do not merge adjacent paragraphs into a single block of text.
- If the page has footnotes (small text at the bottom, often after a horizontal rule), separate them with --- and format each as a numbered line: 1. footnote text
- Convert superscript footnote references in body text to ^N notation (e.g. ^1, ^23).
- For images, illustrations, maps, plates, engravings, or figures on the page, emit a single line: ![Figure](brief description). Do not describe the image in detail — just note what it depicts in a few words. If the illustration is rotated sideways, append |rotate90cw or |rotate90ccw.
- Do NOT add any commentary, explanation, or preamble. Output ONLY the Markdown text.\
"""
    )

    extraction_version: str = "0.1.0"

    def parse_page_range(self) -> list[int] | None:
        if not self.page_range:
            return None
        pages: list[int] = []
        for part in self.page_range.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                pages.extend(range(int(start) - 1, int(end)))
            else:
                pages.append(int(part) - 1)
        return sorted(set(pages))