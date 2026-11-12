"""Configuration settings for SurplusShare application."""

import os


class Config:
    """Application configuration class."""

    SECRET_KEY = os.environ.get('SECRET_KEY', 'surplusshare-dev-key-2024')

    # In Vercel serverless environment, the root filesystem is read-only.
    # Writable SQLite databases must reside in /tmp.
    if os.environ.get('VERCEL'):
        DATABASE = os.environ.get('DATABASE_PATH', '/tmp/surplusshare.db')
    else:
        DATABASE = os.environ.get(
            'DATABASE_PATH',
            os.path.join(os.path.abspath(os.path.dirname(__file__)), 'database', 'surplusshare.db')
        )
    EXPIRY_WARNING_HOURS = 24
    EXPIRY_URGENT_HOURS = 6
    ITEMS_PER_PAGE = 20
