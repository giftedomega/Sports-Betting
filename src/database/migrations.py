"""Database migration utility for adding new columns to existing tables."""

import sqlite3
from pathlib import Path
from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# New columns to add to existing tables (table, column, type, default)
MIGRATIONS = [
    # Team advanced stats
    ("teams", "team_xg", "REAL", None),
    ("teams", "team_xga", "REAL", None),
    ("teams", "xg_difference", "REAL", None),
    ("teams", "shots", "INTEGER", 0),
    ("teams", "shots_on_target", "INTEGER", 0),
    ("teams", "possession", "REAL", None),
    ("teams", "clean_sheets", "INTEGER", 0),
    ("teams", "avg_rating", "REAL", None),
    # Player xG and form
    ("players", "xg", "REAL", None),
    ("players", "xa", "REAL", None),
    ("players", "npxg", "REAL", None),
    ("players", "shots", "INTEGER", 0),
    ("players", "shots_on_target", "INTEGER", 0),
    ("players", "xg_per90", "REAL", None),
    ("players", "current_form_rating", "REAL", None),
    # Fixture weather, referee, sofascore_id
    ("fixtures", "temperature", "REAL", None),
    ("fixtures", "precipitation_prob", "REAL", None),
    ("fixtures", "wind_speed", "REAL", None),
    ("fixtures", "referee", "TEXT", None),
    ("fixtures", "sofascore_id", "INTEGER", None),
]


def run_migrations(db_path: str = None):
    """Run all pending migrations."""
    if db_path is None:
        config = get_config()
        db_path = config.database.path

    path = Path(db_path)
    if not path.exists():
        logger.info("Database does not exist yet, skipping migrations")
        return

    conn = sqlite3.connect(str(path))
    cursor = conn.cursor()
    applied = 0

    for table, column, col_type, default in MIGRATIONS:
        try:
            # Check if column already exists
            cursor.execute(f"PRAGMA table_info({table})")
            existing_columns = [row[1] for row in cursor.fetchall()]

            if column not in existing_columns:
                default_clause = f" DEFAULT {default}" if default is not None else ""
                sql = f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}"
                cursor.execute(sql)
                applied += 1
                logger.info(f"Migration: Added {table}.{column} ({col_type})")
        except Exception as e:
            logger.warning(f"Migration failed for {table}.{column}: {e}")

    conn.commit()
    conn.close()

    if applied > 0:
        logger.info(f"Applied {applied} database migrations")
    else:
        logger.debug("No pending migrations")
