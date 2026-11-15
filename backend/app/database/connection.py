"""SQLite connection management and database initialization.

Provides robust connection handling, foreign-key enforcement, and schema initialization.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path("data/knowledge_base.db")
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_db_path(custom_path: Optional[str] = None) -> Path:
    """Return database file Path, honoring environment variable or custom argument."""
    if custom_path:
        return Path(custom_path)
    env_path = os.getenv("KNOWLEDGE_BASE_DB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create and return a SQLite connection with foreign keys enabled and row factory configured.
    
    Creates parent directories if necessary.
    """
    path = get_db_path(db_path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(path), timeout=10.0)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize the SQLite database with the full DDL schema if tables do not exist."""
    conn = get_connection(db_path)
    try:
        if SCHEMA_PATH.exists():
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            conn.commit()
        else:
            raise FileNotFoundError(f"Schema file not found at {SCHEMA_PATH}")
    finally:
        conn.close()

