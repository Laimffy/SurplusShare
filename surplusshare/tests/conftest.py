"""Pytest fixtures for SurplusShare tests."""

import os
import tempfile
import pytest

from app import create_app
from database.db import init_db, get_db
from database.seed import seed_database


@pytest.fixture
def app():
    """Create a Flask application configured for testing.

    Uses a temporary file for the SQLite database that is cleaned up
    after the test completes.

    Yields:
        Flask: The test-configured Flask application.
    """
    db_fd, db_path = tempfile.mkstemp(suffix='.db')

    test_config = {
        'TESTING': True,
        'DATABASE': db_path,
        'SECRET_KEY': 'test-secret-key-32-bytes-minimum-length-surplusshare',
        'EXPIRY_WARNING_HOURS': 24,
        'EXPIRY_URGENT_HOURS': 6,
        'ITEMS_PER_PAGE': 20,
    }

    application = create_app(test_config=test_config)

    with application.app_context():
        init_db()

    yield application

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create a Flask test client.

    Args:
        app: The test Flask application fixture.

    Returns:
        FlaskClient: A test client for making requests.
    """
    return app.test_client()


@pytest.fixture
def init_db_fixture(app):
    """Initialize and seed the test database.

    Args:
        app: The test Flask application fixture.

    Returns:
        Flask: The application with a seeded database.
    """
    with app.app_context():
        init_db()
        seed_database()

    return app
