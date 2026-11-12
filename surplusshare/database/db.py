"""Database helper functions for SurplusShare."""

import sqlite3
import os
import shutil
import click
from flask import current_app, g


def get_db():
    """Get database connection, storing it in Flask's g object.

    Returns:
        sqlite3.Connection: Database connection with Row factory enabled.
    """
    if 'db' not in g:
        db_path = current_app.config['DATABASE']
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        # On Vercel serverless execution, copy pre-seeded database to /tmp if not present
        if os.environ.get('VERCEL') and not os.path.exists(db_path):
            bundled_db = os.path.join(os.path.dirname(__file__), 'surplusshare.db')
            if os.path.exists(bundled_db) and os.path.getsize(bundled_db) > 0:
                shutil.copyfile(bundled_db, db_path)
            else:
                # Fallback: create schema if bundled db is not found
                conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
                schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
                if os.path.exists(schema_path):
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        conn.executescript(f.read())
                conn.close()

        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


def close_db(e=None):
    """Close the database connection if it exists.

    Args:
        e: Optional exception (unused, required by Flask teardown signature).
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database by executing the schema SQL file."""
    db = get_db()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        db.executescript(f.read())


@click.command('init-db')
def init_db_command():
    """CLI command to clear existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


def init_app(app):
    """Register database functions with the Flask application.

    Args:
        app: The Flask application instance.
    """
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
