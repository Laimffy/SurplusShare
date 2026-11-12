"""Configuration settings for SurplusShare application."""

import os


class Config:
    """Application configuration class."""

    SECRET_KEY = 'surplusshare-dev-key-2024'
    DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'database', 'surplusshare.db')
    EXPIRY_WARNING_HOURS = 24
    EXPIRY_URGENT_HOURS = 6
    ITEMS_PER_PAGE = 20
