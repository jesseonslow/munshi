from pathlib import Path
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[4]


class LedgerConfig(BaseSettings):
    """Configuration for the entity & relational tuplet extraction ledger."""

    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Field(
        default_factory=lambda: ROOT / "data",
        validation_alias=AliasChoices("DATA_DIR", "MUNSHI_DATA_DIR", "LEDGER_DATA_DIR"),
    )
    ledger_db_path: Path = Field(
        default_factory=lambda: ROOT / "ledger/entity_ledger.db",
        validation_alias=AliasChoices("LEDGER_DB", "MUNSHI_LEDGER_DB", "LEDGER_DB_PATH"),
    )
    zvec_index_path: Path = Field(
        default_factory=lambda: ROOT / "ledger/entity_zvec_index",
        validation_alias=AliasChoices("ZVEC_INDEX_DIR", "MUNSHI_ZVEC_INDEX_DIR", "LEDGER_ZVEC_INDEX"),
    )
    authority_index_path: Path = Field(
        default_factory=lambda: ROOT / "db/authority_index.json",
        validation_alias=AliasChoices("AUTHORITY_INDEX", "MUNSHI_AUTHORITY_INDEX", "AUTHORITY_INDEX_PATH"),
    )

    gliner_model: str = Field(
        default="knowledgator/gliner-multitask-v1.0",
        validation_alias=AliasChoices("GLINER_MODEL", "LEDGER_GLINER_MODEL"),
    )
    confidence_threshold: float = Field(
        default=0.5,
        validation_alias=AliasChoices("CONFIDENCE_THRESHOLD", "LEDGER_THRESHOLD"),
    )

    @field_validator("data_dir", "ledger_db_path", "zvec_index_path", "authority_index_path", mode="before")
    @classmethod
    def _anchor_to_root(cls, v: str | Path | None) -> Path | None:
        if v is None:
            return None
        p = Path(v)
        return p if p.is_absolute() else ROOT / p