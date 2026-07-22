#!/bin/sh
# Boot script — creates tables, migrates data from SQLite, starts gunicorn
set -e

echo "=== ADDIE App Boot ==="

# Create database tables by running a small Python script that imports the app
echo "Creating database tables..."
python -c "
from app import create_app
from extensions import db
app = create_app()
with app.app_context():
    db.create_all()
    print('Tables created successfully')
"

# Migrate data from SQLite to PostgreSQL
echo "Migrating data from SQLite to PostgreSQL..."
python migrate_to_postgres.py

# Start the application
echo "Starting gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 'app:create_app()'
