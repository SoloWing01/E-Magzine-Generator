import sqlite3
from pathlib import Path

from app.config.settings import settings


NEW_COLUMNS = {
    "relevance_score": "INTEGER DEFAULT 0",
    "northeast_score": "INTEGER DEFAULT 0",
    "security_score": "INTEGER DEFAULT 0",
    "development_score": "INTEGER DEFAULT 0",
    "society_score": "INTEGER DEFAULT 0",
    "sports_score": "INTEGER DEFAULT 0",
    "category": "VARCHAR(100)",
    "article_score": "INTEGER DEFAULT 0",
    "theme_score": "INTEGER DEFAULT 0",
    "security_relevance_score": "INTEGER DEFAULT 0",
    "freshness_score": "INTEGER DEFAULT 0",
    "source_quality_score": "INTEGER DEFAULT 0",
    "content_quality_score": "INTEGER DEFAULT 0",
    "rank": "INTEGER",
}


def migrate():
    database_url = settings.DATABASE_URL

    if not database_url.startswith("sqlite:///"):
        raise ValueError(
            "This migration script expects a SQLite database."
        )

    database_path = database_url.replace(
        "sqlite:///",
        "",
        1,
    )

    database_path = Path(database_path)

    print("=" * 70)
    print("NORTHEAST SENTINEL - SCORING DATABASE MIGRATION")
    print("=" * 70)

    print(f"\nDatabase: {database_path}")

    connection = sqlite3.connect(database_path)

    try:
        cursor = connection.cursor()

        cursor.execute("PRAGMA table_info(articles)")
        existing_columns = {
            row[1]
            for row in cursor.fetchall()
        }

        print("\nExisting columns:")
        for column in sorted(existing_columns):
            print(f"  - {column}")

        print("\nAdding scoring columns...")

        added = 0

        for column_name, column_definition in NEW_COLUMNS.items():

            if column_name in existing_columns:
                print(
                    f"  [SKIP] {column_name} already exists"
                )
                continue

            sql = (
                f"ALTER TABLE articles "
                f"ADD COLUMN {column_name} "
                f"{column_definition}"
            )

            cursor.execute(sql)

            print(
                f"  [ADD]  {column_name}"
            )

            added += 1

        connection.commit()

        print("\n" + "=" * 70)
        print("MIGRATION COMPLETE")
        print("=" * 70)

        print(f"Columns added: {added}")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    migrate()