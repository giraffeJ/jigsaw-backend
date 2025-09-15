"""
Migration helper for the `user` table.

Usage:
    1. Make a backup of your database (required):
         cp app.db app.db.bak

    2. Run the script:
         python3 scripts/migrate_user_schema.py --db sqlite:///app.db

    3. (Optional) Provide a mapping of old column names to new preference_* names
       via the --mapping parameter as a JSON string:
         --mapping '{"old_gender_col":"preference_gender", "old_region":"preference_region"}'

What the script does (safe, idempotent operations):
    - Connects to the database using SQLAlchemy.
    - Inspects the `user` table columns.
    - Adds missing columns required by the new schema:
        - profile_url (TEXT)
        - preference_gender (VARCHAR(16))
        - preference_age_min (INTEGER)
        - preference_age_max (INTEGER)
        - preference_region (VARCHAR(64))
        - preference_city (VARCHAR(64))
        - created_at / updated_at (DATETIME) — added as TEXT-compatible default columns in SQLite.
    - If you supply an old->new mapping, the script will copy data from existing old columns
      into the new columns where the new columns are NULL.
    - Prints a summary of actions taken.

Notes:
    - This script is conservative: it only adds columns and performs UPDATE copies if requested.
    - It does not drop or rename columns; review results and drop/rename manually if desired.
    - For production, run against a copy first and verify application behavior.

Author: Generated helper (manual review recommended)
"""

import argparse
import json
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError


# Column definitions to ensure exist on `user` table.
# SQLite doesn't support adding columns with constraints like NOT NULL without defaults,
# so we add nullable columns to be safe.
COLUMN_DEFINITIONS = {
    "profile_url": "TEXT",
    "preference_gender": "VARCHAR(16)",
    "preference_age_min": "INTEGER",
    "preference_age_max": "INTEGER",
    "preference_region": "VARCHAR(64)",
    "preference_city": "VARCHAR(64)",
    # created_at / updated_at as TEXT with default CURRENT_TIMESTAMP for SQLite compatibility
    "created_at": "DATETIME DEFAULT (CURRENT_TIMESTAMP)",
    "updated_at": "DATETIME DEFAULT (CURRENT_TIMESTAMP)"
}


def add_column_if_missing(engine, table_name: str, column_name: str, column_def: str):
    insp = inspect(engine)
    cols = [c["name"] for c in insp.get_columns(table_name)]
    if column_name in cols:
        print(f"  - column already exists: {column_name}")
        return False
    # ALTER TABLE ... ADD COLUMN <definition>
    sql = f'ALTER TABLE "{table_name}" ADD COLUMN {column_name} {column_def}'
    print(f"  - adding column: {column_name} {column_def}")
    with engine.connect() as conn:
        conn.execute(text(sql))
    return True


def copy_data_from_old_columns(engine, table_name: str, mapping: dict):
    """
    mapping: { old_col_name: new_col_name, ... }
    For each mapping, if old_col exists and new_col exists, run:
       UPDATE user SET new_col = old_col WHERE (new_col IS NULL OR new_col = '') AND old_col IS NOT NULL;
    """
    insp = inspect(engine)
    cols = [c["name"] for c in insp.get_columns(table_name)]
    with engine.connect() as conn:
        for old_col, new_col in mapping.items():
            if old_col not in cols:
                print(f"  - old column not found, skipping: {old_col}")
                continue
            if new_col not in cols:
                print(f"  - new column not found, skipping: {new_col}")
                continue
            # Perform the copy safely
            print(f"  - copying data: {old_col} -> {new_col}")
            update_sql = text(
                f'UPDATE "{table_name}" SET "{new_col}" = "{old_col}" WHERE ("{new_col}" IS NULL OR "{new_col}" = \'\') AND "{old_col}" IS NOT NULL'
            )
            result = conn.execute(update_sql)
            print(f"    rows affected: {result.rowcount}")


def main():
    parser = argparse.ArgumentParser(description="Migrate/augment user table schema to include preference_* fields")
    parser.add_argument("--db", required=True, help="SQLAlchemy DB URL (e.g. sqlite:///app.db)")
    parser.add_argument("--mapping", required=False, help='JSON mapping old->new column names, e.g. \'{"old_gender":"preference_gender"}\'')
    parser.add_argument("--table", default="user", help="Table name to operate on (default: user)")
    args = parser.parse_args()

    engine = create_engine(args.db)
    table = args.table

    try:
        insp = inspect(engine)
        if table not in insp.get_table_names():
            print(f"Error: table not found: {table}")
            sys.exit(2)
    except OperationalError as e:
        print("OperationalError while inspecting database:", e)
        sys.exit(2)

    print("Inspecting table columns...")
    existing_cols = [c["name"] for c in insp.get_columns(table)]
    print("Existing columns:", existing_cols)

    # Add missing columns
    added = []
    for col, definition in COLUMN_DEFINITIONS.items():
        try:
            changed = add_column_if_missing(engine, table, col, definition)
            if changed:
                added.append(col)
        except Exception as e:
            print(f"Failed to add column {col}: {e}")

    if args.mapping:
        try:
            mapping = json.loads(args.mapping)
            copy_data_from_old_columns(engine, table, mapping)
        except json.JSONDecodeError:
            print("Failed to parse --mapping JSON; skipping data copy.")

    print("\nSummary:")
    if added:
        print("  Added columns:", ", ".join(added))
    else:
        print("  No new columns added.")
    print("  Migration helper finished. Verify data and application behavior before deleting old columns.")


if __name__ == "__main__":
    main()
