import json
import sqlite3
from pathlib import Path

DDL_SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    category TEXT NOT NULL,
    primary_slug TEXT NOT NULL,
    source_origin TEXT,
    tier TEXT DEFAULT 'C',
    mention_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS entity_aliases (
    alias TEXT,
    entity_id TEXT REFERENCES entities(entity_id) ON DELETE CASCADE,
    PRIMARY KEY (alias, entity_id)
);

CREATE TABLE IF NOT EXISTS occurrences (
    occurrence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT REFERENCES entities(entity_id) ON DELETE CASCADE,
    doc_id TEXT NOT NULL,
    page_num INTEGER NOT NULL,
    context_paragraph TEXT NOT NULL
);

-- NEW: Relational Tuplets (Layer 2 Knowledge Graph)
CREATE TABLE IF NOT EXISTS entity_tuplets (
    tuplet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id TEXT NOT NULL REFERENCES entities(entity_id) ON DELETE CASCADE,
    predicate TEXT NOT NULL,
    object_id TEXT REFERENCES entities(entity_id) ON DELETE CASCADE,
    raw_object_text TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    page_num INTEGER,
    evidence_text TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_occ_entity ON occurrences(entity_id);
CREATE INDEX IF NOT EXISTS idx_occ_doc_page ON occurrences(doc_id, page_num);
CREATE INDEX IF NOT EXISTS idx_tuplet_subject ON entity_tuplets(subject_id);
"""

def init_db(db_path: Path) -> sqlite3.Connection:
    # Ensure the parent directory (e.g. munshi/ledger/) exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists() and db_path.stat().st_size == 0:
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    with conn:
        conn.executescript(DDL_SCHEMA)
    return conn

def finalize_ledger_tiers(conn: sqlite3.Connection) -> None:
    """Calculates corpus frequencies and assigns synthesis tiers across entities."""
    with conn:
        conn.execute("""
            UPDATE entities 
            SET mention_count = (
                SELECT COUNT(*) 
                FROM occurrences 
                WHERE occurrences.entity_id = entities.entity_id
            )
        """)
        # Tier A: 5+ occurrences across at least 2 distinct documents
        conn.execute("""
            UPDATE entities 
            SET tier = 'A' 
            WHERE entity_id IN (
                SELECT entity_id 
                FROM occurrences 
                GROUP BY entity_id 
                HAVING COUNT(*) >= 5 AND COUNT(DISTINCT doc_id) >= 2
            )
        """)
        # Tier B: 2+ occurrences
        conn.execute("""
            UPDATE entities 
            SET tier = 'B' 
            WHERE mention_count >= 2 AND tier != 'A'
        """)

def seed_authority_index(conn: sqlite3.Connection, authority_json_path: Path) -> int:
    """Pre-seeds the SQLite ledger with ground-truth entities and aliases."""
    if not authority_json_path.exists():
        return 0

    records = json.loads(authority_json_path.read_text(encoding="utf-8"))
    count = 0

    with conn:
        for item in records:
            entity_id = item["id"]
            canonical_name = item["headword"].strip()
            category = item.get("category", "concept")
            slug = entity_id.split(":", 1)[-1]

            # 1. Insert entity
            conn.execute(
                """
                INSERT OR IGNORE INTO entities (entity_id, canonical_name, category, primary_slug, source_origin)
                VALUES (?, ?, ?, ?, 'authority_index')
                """,
                (entity_id, canonical_name, category, slug)
            )

            # 2. Insert primary canonical name as alias
            conn.execute(
                "INSERT OR IGNORE INTO entity_aliases (alias, entity_id) VALUES (?, ?)",
                (canonical_name, entity_id)
            )

            # 3. Insert all alternate aliases
            for alias in item.get("aliases", []):
                alias_clean = alias.strip()
                if alias_clean:
                    conn.execute(
                        "INSERT OR IGNORE INTO entity_aliases (alias, entity_id) VALUES (?, ?)",
                        (alias_clean, entity_id)
                    )
            count += 1

    return count