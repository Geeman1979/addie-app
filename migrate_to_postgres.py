"""
Migration script: SQLite → PostgreSQL
Preserves ALL existing data from addie_v4.db
First run: migrates data from SQLite to PostgreSQL
Subsequent runs: idempotent (skips if data already exists)
"""
import os
import json
from datetime import datetime
from sqlalchemy import create_engine, MetaData, Table, select, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://addie_user:addie_pass@db:5432/addie')
SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'addie_v4.db')

if not os.path.exists(SQLITE_PATH):
    print(f"No SQLite database found at {SQLITE_PATH} — skipping migration")
    exit(0)

print(f"Found SQLite database: {SQLITE_PATH}")

sqlite_engine = create_engine(f'sqlite:///{SQLITE_PATH}')
pg_engine = create_engine(DATABASE_URL)

sqlite_meta = MetaData()
sqlite_meta.reflect(bind=sqlite_engine)

pg_meta = MetaData()
try:
    pg_meta.reflect(bind=pg_engine)
except:
    print("PostgreSQL not yet available — tables will be created by app on first run")
    exit(1)

sqlite_conn = sqlite_engine.connect()
pg_conn = pg_engine.connect()

TABLES_IN_ORDER = [
    'user', 'lna_cycle', 'department_budget',
    'request', 'phase', 'approval', 'kirkpatrick_result',
    'interview_guide', 'content_tag',
    'learning_statistic', 'learning_upload_batch',
    'cohort', 'audit_log', 'training_event',
    'resource_allocation', 'resource_forecast',
    'phase_activity'
]

total_rows = 0
for table_name in TABLES_IN_ORDER:
    if table_name not in sqlite_meta.tables:
        print(f"  Table '{table_name}' not in SQLite — skipping")
        continue
    if table_name not in pg_meta.tables:
        print(f"  Table '{table_name}' not in PostgreSQL yet — skipping")
        continue

    sqlite_table = sqlite_meta.tables[table_name]
    pg_table = pg_meta.tables[table_name]

    existing = pg_conn.execute(select(text('count(*)')).select_from(pg_table)).scalar()
    if existing and existing > 0:
        print(f"  Table '{table_name}' already has {existing} rows in PostgreSQL — skipping")
        total_rows += existing
        continue

    rows = sqlite_conn.execute(select(sqlite_table)).fetchall()
    if not rows:
        continue

    col_names = [c.name for c in sqlite_table.columns]
    inserted = 0
    for row in rows:
        row_dict = dict(zip(col_names, row))
        try:
            pg_conn.execute(pg_table.insert().values(**row_dict))
            inserted += 1
        except Exception as e:
            print(f"    Warning: Could not insert row in {table_name}: {str(e)[:80]}")

    pg_conn.commit()
    total_rows += inserted
    print(f"  Table '{table_name}': {inserted} rows migrated")

print(f"\nMigration complete! {total_rows} total rows migrated to PostgreSQL.")
sqlite_conn.close()
pg_conn.close()
