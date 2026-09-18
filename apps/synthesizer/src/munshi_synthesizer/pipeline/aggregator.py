from __future__ import annotations

import concurrent.futures
import sqlite3
from pathlib import Path

from munshi_synthesizer.pipeline.rerank import PassageReranker
from munshi_synthesizer.pipeline.zvec import ZvecRetriever
from munshi_synthesizer.schema import EntityTarget, OccurrenceRecord


class LedgerAggregator:
    """Queries SQLite and zvec-grep in parallel, deduplicates, reranks, and returns curated evidence."""

    def __init__(
        self,
        db_path: Path,
        zvec_data_dir: Path | None = None,
        zvec_top_k: int = 15,
        enable_zvec: bool = True,
        rerank_model: str = "BAAI/bge-reranker-base",
        rerank_top_k: int = 25,
        rerank_min_score: float = 0.1,
    ):
        self.db_path = db_path
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

        self.enable_zvec = enable_zvec
        self.zvec = ZvecRetriever(zvec_data_dir, top_k=zvec_top_k) if zvec_data_dir else None

        # Cross-encoder reranker for filtering noise and ranking relevance
        self.reranker = PassageReranker(model_name=rerank_model)
        self.rerank_top_k = rerank_top_k
        self.rerank_min_score = rerank_min_score

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def fetch_entity(self, target_identifier: str) -> EntityTarget | None:
        """Finds an entity by exact ID, canonical name, or registered alias."""
        with self._get_connection() as conn:
            cur = conn.cursor()

            cur.execute(
                """
                SELECT entity_id, canonical_name, category, tier, mention_count,
                       COALESCE(is_curated, 0) as is_curated
                FROM entities
                WHERE entity_id = ? OR canonical_name = ? COLLATE NOCASE
                """,
                (target_identifier, target_identifier),
            )
            row = cur.fetchone()

            if not row:
                cur.execute(
                    """
                    SELECT e.entity_id, e.canonical_name, e.category, e.tier, e.mention_count,
                           COALESCE(e.is_curated, 0) as is_curated
                    FROM entity_aliases a
                    JOIN entities e ON a.entity_id = e.entity_id
                    WHERE a.alias = ? COLLATE NOCASE
                    """,
                    (target_identifier,),
                )
                row = cur.fetchone()

            if not row:
                return None

            entity_id = row["entity_id"]
            cur.execute("SELECT alias FROM entity_aliases WHERE entity_id = ?", (entity_id,))
            aliases = [r["alias"] for r in cur.fetchall()]

            return EntityTarget(
                entity_id=row["entity_id"],
                canonical_name=row["canonical_name"],
                category=row["category"],
                tier=row["tier"] or "C",
                mention_count=row["mention_count"] or 0,
                is_curated=bool(row["is_curated"]),
                aliases=aliases,
            )

    def _fetch_db_occurrences(self, entity_id: str) -> list[OccurrenceRecord]:
        """Worker function for SQLite retrieval."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT doc_id, page_num, snippet AS context_snippet
                FROM occurrences
                WHERE entity_id = ?
                ORDER BY doc_id, page_num
                """,
                (entity_id,),
            )
            return [
                OccurrenceRecord(
                    doc_id=row["doc_id"],
                    page_num=row["page_num"],
                    context_snippet=row["context_snippet"],
                    source_type="ledger",
                )
                for row in cur.fetchall()
            ]

    def _fetch_zvec_occurrences(self, entity: EntityTarget) -> list[OccurrenceRecord]:
        """Worker function for zvec-grep retrieval."""
        if not self.enable_zvec or not self.zvec:
            return []
        query_str = f"{entity.canonical_name} {' '.join(entity.aliases[:3])}".strip()
        return self.zvec.search(query_str)

    def fetch_all_occurrences_parallel(self, entity: EntityTarget) -> list[OccurrenceRecord]:
        """Executes SQLite and zvec-grep simultaneously, deduplicates, and reranks hits."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_db = executor.submit(self._fetch_db_occurrences, entity.entity_id)
            future_zvec = executor.submit(self._fetch_zvec_occurrences, entity)

            db_records = future_db.result()
            zvec_records = future_zvec.result()

        # 1. Merge and deduplicate
        combined: list[OccurrenceRecord] = list(db_records)
        existing_signatures = {
            (r.doc_id, r.context_snippet.strip().lower()[:60]) for r in db_records
        }

        for z_rec in zvec_records:
            sig = (z_rec.doc_id, z_rec.context_snippet.strip().lower()[:60])
            if sig not in existing_signatures:
                combined.append(z_rec)
                existing_signatures.add(sig)

        # 2. Rerank and filter out noise (footnotes, TOC lines, diagnostics)
        query = f"{entity.canonical_name} {' '.join(entity.aliases[:2])}".strip()
        curated_records = self.reranker.filter_and_rerank(
            query=query,
            records=combined,
            top_k=self.rerank_top_k,
            min_score=self.rerank_min_score,
        )

        # 3. Return curated records instead of the unpruned combined pool
        return curated_records

    def list_curated_or_tier_a(self) -> list[EntityTarget]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT entity_id, canonical_name, category, tier, mention_count,
                       COALESCE(is_curated, 0) as is_curated
                FROM entities
                WHERE is_curated = 1 OR tier = 'A'
                ORDER BY mention_count DESC
                """
            )
            return [
                EntityTarget(
                    entity_id=row["entity_id"],
                    canonical_name=row["canonical_name"],
                    category=row["category"],
                    tier=row["tier"] or "C",
                    mention_count=row["mention_count"] or 0,
                    is_curated=bool(row["is_curated"]),
                )
                for row in cur.fetchall()
            ]