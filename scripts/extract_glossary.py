#!/usr/bin/env python3
"""
ChemLink glossary-only extractor.

Pulls glossary terms from the ChemLink source database and loads them into
staging.chemlink_glossary in the analytics warehouse. Intended for cases where
we only need glossary updates without re-running the full extract job.
"""

import sys
import time
from pathlib import Path
from datetime import datetime
import traceback

sys.path.insert(0, str(Path(__file__).parent.parent))

from db_config import (  # noqa: E402
    get_chemlink_source_connection,
    get_analytics_db_connection
)


def log(message, level="INFO"):
    """Emit a timestamped log entry."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    icons = {"INFO": "📝", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
    icon = icons.get(level, "📝")
    print(f"[{timestamp}] {icon} {message}")
    sys.stdout.flush()


def fetch_glossary_records(source_conn):
    """Fetch glossary data from ChemLink."""
    query = """
        SELECT
            id,
            term,
            meaning,
            category,
            description,
            created_at,
            updated_at
        FROM glossary
        ORDER BY id
    """
    with source_conn.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
    return rows, columns


def load_glossary(analytics_conn, columns, rows):
    """Replace staging.chemlink_glossary with provided rows."""
    if not rows:
        log("No glossary data returned; aborting load.", "WARNING")
        return 0

    start = time.time()
    placeholders = ",".join(["%s"] * len(columns))
    insert_sql = f"""
        INSERT INTO staging.chemlink_glossary ({",".join(columns)})
        VALUES ({placeholders})
    """

    try:
        with analytics_conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE staging.chemlink_glossary CASCADE")
        analytics_conn.commit()
        log("Truncated staging.chemlink_glossary", "SUCCESS")
    except Exception as exc:
        analytics_conn.rollback()
        raise RuntimeError(f"Failed to truncate glossary staging table: {exc}") from exc

    inserted = 0
    batch_size = 500
    try:
        with analytics_conn.cursor() as cursor:
            for idx in range(0, len(rows), batch_size):
                batch = rows[idx : idx + batch_size]
                cursor.executemany(insert_sql, batch)
                analytics_conn.commit()
                inserted += len(batch)
                progress = (inserted / len(rows)) * 100
                log(f"Loaded {inserted:,}/{len(rows):,} rows ({progress:.1f}%)", "INFO")
    except Exception as exc:
        analytics_conn.rollback()
        raise RuntimeError(f"Failed loading glossary rows: {exc}") from exc

    duration = time.time() - start
    log(f"✅ Glossary load complete: {inserted:,} rows in {duration:.2f}s", "SUCCESS")
    return inserted


def main():
    log("=" * 70, "INFO")
    log("CHEMLINK GLOSSARY EXTRACT", "INFO")
    log("=" * 70, "INFO")

    log("Connecting to databases...", "INFO")
    try:
        source_conn = get_chemlink_source_connection()
        analytics_conn = get_analytics_db_connection()
        log("Connections established", "SUCCESS")
    except Exception as exc:
        log(f"❌ Failed to connect to databases: {exc}", "ERROR")
        return 1

    try:
        rows, columns = fetch_glossary_records(source_conn)
        log(f"Fetched {len(rows):,} glossary rows", "INFO")
        load_glossary(analytics_conn, columns, rows)
        log("Glossary extract completed successfully", "SUCCESS")
        return 0
    except Exception as exc:
        log(f"❌ Glossary extract failed: {exc}", "ERROR")
        log(traceback.format_exc(), "ERROR")
        return 1
    finally:
        try:
            source_conn.close()
        except Exception:
            pass
        try:
            analytics_conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
