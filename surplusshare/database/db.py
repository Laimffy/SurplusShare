"""Database helper functions for SurplusShare."""

import sqlite3
import os
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
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

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
