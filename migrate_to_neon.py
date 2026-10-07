import os
import sqlite3

from flask import Flask
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from models import db


load_dotenv()

NEON_DATABASE_URL = os.environ.get("DATABASE_URL")

if not NEON_DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in .env")

if NEON_DATABASE_URL.startswith("postgres://"):
    NEON_DATABASE_URL = NEON_DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )

SQLITE_DB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "instance",
    "study_platform.db"
)

if not os.path.exists(SQLITE_DB):
    raise FileNotFoundError(
        f"SQLite database not found: {SQLITE_DB}"
    )


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = NEON_DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


TABLE_ORDER = [
    "users",
    "subjects",
    "study_materials",
    "doubts",
    "answers",
    "discussions",
    "comments",
    "study_groups",
    "group_members",
    "group_materials",
    "group_discussions",
    "group_discussion_comments",
    "quizzes",
    "questions",
    "quiz_attempts",
    "ratings",
    "user_progress",
    "notifications",
]


# SQLite stores booleans as 0/1.
# PostgreSQL needs real True/False values.
BOOLEAN_COLUMNS = {
    "users": {
        "is_active"
    },
    "study_materials": {
        "is_public"
    },
    "doubts": {
        "is_resolved"
    },
    "discussions": {
        "is_pinned",
        "is_locked"
    },
    "study_groups": {
        "is_private"
    },
    "quizzes": {
        "is_public",
        "shuffle_questions"
    },
    "quiz_attempts": {
    },
    "notifications": {
        "is_read"
    },
}


def get_sqlite_tables():
    connection = sqlite3.connect(SQLITE_DB)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )

        return [row["name"] for row in cursor.fetchall()]

    finally:
        connection.close()


def get_sqlite_columns(connection, table_name):
    rows = connection.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [row[1] for row in rows]


def convert_value(table_name, column_name, value):
    if column_name in BOOLEAN_COLUMNS.get(table_name, set()):
        if value is None:
            return None

        return bool(value)

    return value


def migrate_table(
    sqlite_connection,
    postgres_connection,
    table_name
):
    sqlite_columns = get_sqlite_columns(
        sqlite_connection,
        table_name
    )

    if not sqlite_columns:
        print(
            f"Skipping {table_name}: "
            "no columns found."
        )
        return

    result = sqlite_connection.execute(
        f'SELECT * FROM "{table_name}"'
    )

    rows = result.fetchall()

    if not rows:
        print(f"✓ {table_name}: empty")
        return

    postgres_columns_result = postgres_connection.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = :table_name
            """
        ),
        {
            "table_name": table_name
        }
    )

    postgres_columns = {
        row[0]
        for row in postgres_columns_result.fetchall()
    }

    columns = [
        column
        for column in sqlite_columns
        if column in postgres_columns
    ]

    if not columns:
        print(
            f"Skipping {table_name}: "
            "no matching columns."
        )
        return

    # Clear existing rows in Neon so this script
    # can safely be re-run after a failed migration.
    postgres_connection.execute(
        text(
            f'DELETE FROM "{table_name}"'
        )
    )

    column_sql = ", ".join(
        f'"{column}"'
        for column in columns
    )

    value_sql = ", ".join(
        f":{column}"
        for column in columns
    )

    insert_sql = text(
        f"""
        INSERT INTO "{table_name}"
        ({column_sql})
        VALUES ({value_sql})
        """
    )

    for row in rows:

        data = {
            column: convert_value(
                table_name,
                column,
                row[column]
            )
            for column in columns
        }

        postgres_connection.execute(
            insert_sql,
            data
        )

    print(
        f"✓ {table_name}: "
        f"{len(rows)} rows migrated"
    )


def reset_sequences(postgres_connection):

    for table_name in TABLE_ORDER:

        try:
            postgres_connection.execute(
                text(
                    f"""
                    SELECT setval(
                        pg_get_serial_sequence(
                            '"{table_name}"',
                            'id'
                        ),
                        COALESCE(
                            (
                                SELECT MAX(id)
                                FROM "{table_name}"
                            ),
                            1
                        ),
                        true
                    )
                    """
                )
            )

        except Exception:
            pass


def main():

    print("=" * 60)
    print("StudyHub SQLite → Neon Migration")
    print("=" * 60)

    print("\nChecking SQLite database...")

    sqlite_tables = get_sqlite_tables()

    print("\nTables found:")

    for table in sqlite_tables:
        print(f"  - {table}")

    print("\nConnecting to Neon...")

    postgres_engine = create_engine(
        NEON_DATABASE_URL,
        pool_pre_ping=True
    )

    sqlite_connection = sqlite3.connect(
        SQLITE_DB
    )

    sqlite_connection.row_factory = sqlite3.Row

    try:

        with app.app_context():

            print("\nCreating Neon tables...")

            db.create_all()

            print("✓ Neon tables ready")

            with postgres_engine.begin() as postgres_connection:

                print("\nMigrating data...\n")

                for table_name in TABLE_ORDER:

                    if table_name in sqlite_tables:

                        migrate_table(
                            sqlite_connection,
                            postgres_connection,
                            table_name
                        )

                print(
                    "\nUpdating PostgreSQL ID sequences..."
                )

                reset_sequences(
                    postgres_connection
                )

                print("✓ Sequences updated")

        print("\n" + "=" * 60)
        print("🎉 MIGRATION COMPLETED")
        print("=" * 60)

        print(
            "\nOriginal SQLite database is safe."
        )

        print(
            "Backup: "
            "instance/study_platform_backup.db"
        )

    except Exception as error:

        print("\n" + "=" * 60)
        print("❌ MIGRATION FAILED")
        print("=" * 60)

        print(f"\nError: {error}")

        print(
            "\nYour original SQLite database "
            "was not modified."
        )

        raise

    finally:

        sqlite_connection.close()
        postgres_engine.dispose()


if __name__ == "__main__":
    main()