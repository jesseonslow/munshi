import sqlite3
from pathlib import Path
from typing import Optional
from sentence_transformers import SentenceTransformer
import zvec

class ZvecResolver:
    def __init__(self, index_path: Path, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.index_path = index_path
        self.embedder = SentenceTransformer(model_name)
        
        if self.index_path.exists():
            self.entity_vdb = zvec.open(path=str(self.index_path))
        else:
            self.entity_vdb = None

    def resolve_unmatched_entity(
        self, 
        raw_mention: str, 
        context_snippet: str, 
        category: str, 
        conn: sqlite3.Connection
    ) -> Optional[str]:
        """Semantic reconciliation check when SQL alias lookup misses[cite: 10]."""
        if not self.entity_vdb:
            return None

        query_text = f"{raw_mention}: {context_snippet}"
        query_vec = self.embedder.encode([query_text], normalize_embeddings=True)[0].tolist()

        try:
            matches = self.entity_vdb.search(
                vector_field="embedding",
                vector=query_vec,
                top_k=3,
                filter=f"category == '{category}'"
            )
        except Exception:
            return None

        if not matches:
            return None

        top_hit = matches[0]
        if getattr(top_hit, "score", 0.0) >= 0.88:
            canonical_id = top_hit.fields.get("entity_id")
            if canonical_id:
                conn.execute(
                    "INSERT OR IGNORE INTO entity_aliases (alias, entity_id) VALUES (?, ?)", 
                    (raw_mention, canonical_id)
                )
                return canonical_id

        return None