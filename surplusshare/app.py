"""Flask application factory for SurplusShare."""

from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, current_app

from config import Config
from database.db import init_app as init_db_app
from database.seed import seed_db_command


def create_app(test_config=None):
    """Create and configure the Flask application.

    Args:
        test_config: Optional dictionary of config overrides for testing.

    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__, instance_relative_config=False)

    # Load configuration
    if test_config is None:
        app.config.from_object(Config)
    else:
        app.config.update(test_config)
        if 'SECRET_KEY' not in test_config:
            app.config['SECRET_KEY'] = Config.SECRET_KEY

    # Initialize database
    init_db_app(app)
    app.cli.add_command(seed_db_command)

    # Register blueprints
    from routes.public import public
    from routes.auth import auth
    from routes.admin import admin_bp
    from routes.main import main
    from routes.listings import listings
    from routes.requests import requests_bp
    from routes.matching import matching
    from routes.schedule import schedule
    from routes.search import search
    from routes.monitoring import monitoring
    from routes.reports import reports
    from routes.benchmark import benchmark
    from routes.settings import settings

    app.register_blueprint(public)      # Public website (Home, About, Partners, Available Food, etc.)
    app.register_blueprint(auth)        # Web & API Authentication
    app.register_blueprint(admin_bp)    # Administrative Management Modules
    app.register_blueprint(main)        # Authenticated Dashboard
    app.register_blueprint(listings)    # Food Donation Management
    app.register_blueprint(requests_bp) # Recipient Requests
    app.register_blueprint(matching)    # Automated Matching Engine
    app.register_blueprint(schedule)    # Pickup Routing & Doubly Linked List
    app.register_blueprint(search)      # Search & Sort Benchmark
    app.register_blueprint(monitoring)  # Real-Time Expiry Monitoring
    app.register_blueprint(reports)     # Sustainability Analytics & CSV Export
    app.register_blueprint(benchmark)   # Empirical Algorithm Benchmark Lab
    app.register_blueprint(settings)    # System Configuration

    # HTTP Error Handlers
    @app.errorhandler(401)
    def unauthorized_error(e):
        from services.auth_service import is_api_request
        if is_api_request():
            return jsonify({
                'status': 'error',
                'error': 'Unauthorized',
                'message': 'Authentication required. Please log in or provide a valid Bearer token.',
                'code': 401,
            }), 401
        return render_template('errors/401.html'), 401

    @app.errorhandler(403)
    def forbidden_error(e):
        from services.auth_service import is_api_request
        if is_api_request():
            return jsonify({
                'status': 'error',
                'error': 'Forbidden',
                'message': 'You do not have permission to access this resource.',
                'code': 403,
            }), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(e):
        from services.auth_service import is_api_request
        if is_api_request():
            return jsonify({
                'status': 'error',
                'error': 'Not Found',
                'message': 'The requested resource was not found.',
                'code': 404,
            }), 404
        return render_template('errors/404.html'), 404

    # Template context processors
    @app.context_processor
    def inject_globals():
        """Inject global variables into all templates."""
        from services.auth_service import get_current_user, generate_csrf_token

        categories = [
            'Bakery', 'Vegetables', 'Fruits', 'Prepared Meals',
            'Dairy', 'Dry Goods', 'Other'
        ]

        user = get_current_user()
        if user:
            current_user = dict(user)
            current_user['is_authenticated'] = True
        else:
            current_user = {
                'id': None,
                'username': 'guest',
                'display_name': 'Guest Visitor',
                'role': 'public',
                'organization': None,
                'email': None,
                'is_authenticated': False,
                'is_demo_user': False,
            }

        return {
            'current_year': datetime.now().year,
            'app_name': 'SurplusShare',
            'categories': categories,
            'current_user': current_user,
            'csrf_token': generate_csrf_token,
            'demo_role_switching_enabled': app.config.get('DEMO_ROLE_SWITCHING_ENABLED', True),
        }

    # Custom Jinja2 filters
    @app.template_filter('format_datetime')
    def format_datetime_filter(value, fmt='%b %d, %Y %I:%M %p'):
        """Format an ISO datetime string for display."""
        if not value:
            return ''
        try:
            dt = datetime.fromisoformat(value)
            return dt.strftime(fmt)
        except (TypeError, ValueError):
            return value

    @app.template_filter('time_ago')
    def time_ago_filter(value):
        """Convert an ISO datetime string to a human-readable relative time."""
        if not value:
            return ''
        try:
            dt = datetime.fromisoformat(value)
            now = datetime.now()
            diff = now - dt

            if diff.total_seconds() < 0:
                # Future date
                diff = dt - now
                if diff.days > 0:
                    return f"in {diff.days} day{'s' if diff.days != 1 else ''}"
                hours = int(diff.total_seconds() // 3600)
                if hours > 0:
                    return f"in {hours} hour{'s' if hours != 1 else ''}"
                minutes = int(diff.total_seconds() // 60)
                if minutes > 0:
                    return f"in {minutes} minute{'s' if minutes != 1 else ''}"
                return "just now"

            if diff.days > 0:
                return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
            hours = int(diff.total_seconds() // 3600)
            if hours > 0:
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            minutes = int(diff.total_seconds() // 60)
            if minutes > 0:
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            return "just now"
        except (TypeError, ValueError):
            return value

    @app.template_filter('expiry_status')
    def expiry_status_filter(value):
        """Determine the expiry status category based on config thresholds."""
        if not value:
            return 'fresh'
        try:
            dt = datetime.fromisoformat(value)
            now = datetime.now()

            if dt <= now:
                return 'expired'

            hours_remaining = (dt - now).total_seconds() / 3600
            urgent_hours = app.config.get('EXPIRY_URGENT_HOURS', 6)
            warning_hours = app.config.get('EXPIRY_WARNING_HOURS', 24)

            if hours_remaining <= urgent_hours:
                return 'urgent'
            elif hours_remaining <= warning_hours:
                return 'warning'
            else:
                return 'fresh'
        except (TypeError, ValueError):
            return 'fresh'

    # Security & anti-caching headers on HTML responses
    @app.after_request
    def set_security_and_cache_headers(response):
        """Prevent browser navigation from restoring access to protected pages after logout."""
        if response.content_type and 'text/html' in response.content_type:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response

    return app


# Allow running with `python app.py`
if __name__ == '__main__':
    application = create_app()
    application.run(debug=True, port=5000)
