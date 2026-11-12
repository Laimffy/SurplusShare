"""
services/auth_service.py — Authentication & Role-Based Access Control (RBAC) Service

Features:
- Dual authentication: Flask session cookies (web UI) & JWT Bearer tokens (REST APIs)
- Decorators: @login_required, @roles_required, @admin_required
- Proper HTTP response codes: HTTP 401 (Unauthorized) & HTTP 403 (Forbidden)
- Resource ownership verification for multi-tenant data isolation:
  - Donors can only manage their own listings
  - Recipients can only manage their own requests
  - Volunteers can only manage assigned pickup schedules
  - Admins can manage the entire system
"""

import functools
from datetime import datetime, timedelta, timezone
from flask import request, session, redirect, url_for, flash, jsonify, render_template, current_app
import jwt
from database.db import get_db


JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24


def generate_jwt_token(user_id=None, username=None, role=None, display_name=None, **kwargs):
    """Generate a signed JWT token valid for 24 hours.
    
    Accepts either a user dictionary as the first positional argument,
    or explicit user_id, username, role arguments.
    """
    if isinstance(user_id, dict):
        u_dict = user_id
        user_id = u_dict.get('id') or u_dict.get('user_id')
        username = u_dict.get('username')
        role = u_dict.get('role')
        display_name = u_dict.get('display_name', username)

    secret = current_app.config.get('SECRET_KEY', 'surplusshare-dev-secret-key-2026-very-secure-32bytes')
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user_id),
        'user_id': user_id,
        'username': username,
        'role': role,
        'display_name': display_name or username,
        'iat': now,
        'exp': now + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token):
    """Decode and validate a JWT token. Returns dict or None."""
    secret = current_app.config.get('SECRET_KEY', 'surplusshare-dev-secret-key-2026')
    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
        return None


def get_current_user():
    """Retrieve the currently authenticated user from Bearer token or session.
    
    Returns:
        dict: User dictionary with 'id', 'username', 'role', 'display_name', 'organization', etc.,
              or None if unauthenticated.
    """
    # 1. Check Authorization Bearer header
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1].strip()
        payload = decode_jwt_token(token)
        if payload and 'user_id' in payload:
            db = get_db()
            row = db.execute(
                "SELECT id, username, display_name, role, organization, email FROM users WHERE id = ?",
                (payload['user_id'],),
            ).fetchone()
            if row:
                user = dict(row)
                user['auth_method'] = 'jwt'
                user['is_authenticated'] = True
                user['is_demo_user'] = False
                return user

    # 2. Check Flask session
    user_id = session.get('user_id')
    if user_id:
        db = get_db()
        row = db.execute(
            "SELECT id, username, display_name, role, organization, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row:
            user = dict(row)
            user['auth_method'] = 'session'
            user['is_authenticated'] = True
            is_demo = bool(session.get('is_demo_user', False)) and current_app.config.get('DEMO_ROLE_SWITCHING_ENABLED', True)
            user['is_demo_user'] = is_demo
            return user

    return None


def is_api_request():
    """Check if the incoming request expects a JSON API response."""
    return (
        request.path.startswith('/api/') or
        request.is_json or
        request.headers.get('Accept') == 'application/json' or
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        request.headers.get('Authorization', '').startswith('Bearer ')
    )


def login_required(view_func):
    """Decorator requiring an authenticated user.
    
    Returns HTTP 401 Unauthorized for unauthenticated requests.
    """
    @functools.wraps(view_func)
    def wrapped_view(*args, **kwargs):
        user = get_current_user()
        if user is None:
            if is_api_request():
                return jsonify({
                    'status': 'error',
                    'error': 'Unauthorized',
                    'message': 'Authentication required. Please log in or provide a valid Bearer token.',
                    'code': 401,
                }), 401
            flash('Please sign in to access this resource.', 'warning')
            return redirect(url_for('auth.login', next=request.path))
        return view_func(*args, **kwargs)
    return wrapped_view


def roles_required(*allowed_roles):
    """Decorator requiring the user to have at least one of the specified roles.
    
    Admins automatically satisfy all role checks.
    Returns HTTP 401 for unauthenticated, HTTP 403 Forbidden for unauthorized.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped_view(*args, **kwargs):
            user = get_current_user()
            if user is None:
                if is_api_request():
                    return jsonify({
                        'status': 'error',
                        'error': 'Unauthorized',
                        'message': 'Authentication required. Please log in or provide a valid Bearer token.',
                        'code': 401,
                    }), 401
                flash('Please sign in to access this resource.', 'warning')
                return redirect(url_for('auth.login', next=request.path))

            user_role = user.get('role', '')
            # Admin has superuser privileges
            if user_role != 'admin' and user_role not in allowed_roles:
                if is_api_request():
                    return jsonify({
                        'status': 'error',
                        'error': 'Forbidden',
                        'message': f'Access forbidden. Requires one of roles: {list(allowed_roles)}. Your role is "{user_role}".',
                        'code': 403,
                    }), 403
                return render_template(
                    'errors/403.html',
                    required_roles=allowed_roles,
                    user_role=user_role,
                ), 403

            return view_func(*args, **kwargs)
        return wrapped_view
    return decorator


def admin_required(view_func):
    """Decorator shorthand for restricting access strictly to administrators."""
    return roles_required('admin')(view_func)


# ── Ownership & Tenant Validation ──────────────────────────────────────────

def can_manage_listing(listing, user):
    """Check if the given user is authorized to edit or delete the food listing.
    
    Admins can manage any listing. Donors can only manage their own listings.
    """
    if not user:
        return False
    if user['role'] == 'admin':
        return True
    if user['role'] == 'donor':
        # Check by donor_id foreign key if present
        if listing.get('donor_id') and listing['donor_id'] == user['id']:
            return True
        # Check by donor_name matching user's organization or display_name
        donor_name = listing.get('donor_name', '').strip().lower()
        org_name = (user.get('organization') or '').strip().lower()
        disp_name = (user.get('display_name') or '').strip().lower()
        user_name = (user.get('username') or '').strip().lower()
        if donor_name and (donor_name == org_name or donor_name == disp_name or donor_name == user_name):
            return True
    return False


def can_manage_request(req_data, user):
    """Check if the given user is authorized to edit or cancel the recipient request.
    
    Admins can manage any request. Recipients can only manage their own requests.
    """
    if not user:
        return False
    if user['role'] == 'admin':
        return True
    if user['role'] == 'recipient':
        if req_data.get('recipient_id') and req_data['recipient_id'] == user['id']:
            return True
        org_name = req_data.get('organization_name', '').strip().lower()
        user_org = (user.get('organization') or '').strip().lower()
        disp_name = (user.get('display_name') or '').strip().lower()
        user_name = (user.get('username') or '').strip().lower()
        if org_name and (org_name == user_org or org_name == disp_name or org_name == user_name):
            return True
    return False


def can_manage_schedule(schedule_data, user):
    """Check if the given user is authorized to manage or complete pickup activities."""
    if not user:
        return False
    if user['role'] == 'admin':
        return True
    if user['role'] == 'volunteer':
        vname = (schedule_data.get('volunteer_name') or '').strip().lower()
        disp_name = (user.get('display_name') or '').strip().lower()
        user_name = (user.get('username') or '').strip().lower()
        if vname and (vname == disp_name or vname == user_name or vname in disp_name or disp_name in vname):
            return True
        if schedule_data.get('volunteer_id') and schedule_data['volunteer_id'] == user['id']:
            return True
    return False


def can_view_schedule(schedule_data, user):
    """Check if user has permission to view the pickup schedule.
    
    Admins can view any schedule.
    Volunteers can view only schedules assigned to them.
    Donors can view schedules that include pickup stops for their donations.
    Recipients can view schedules that deliver allocations fulfilling their requests.
    """
    if not user:
        return False
    if user['role'] == 'admin':
        return True
    if user['role'] == 'volunteer':
        return can_manage_schedule(schedule_data, user)
    if user['role'] == 'donor':
        donor_org = (user.get('organization') or '').strip().lower()
        donor_disp = (user.get('display_name') or '').strip().lower()
        stops = schedule_data.get('stops', [])
        for s in stops:
            s_donor = (s.get('donor_name') or '').strip().lower()
            if s_donor and (s_donor == donor_org or s_donor == donor_disp):
                return True
        return False
    if user['role'] == 'recipient':
        db = get_db()
        stops = schedule_data.get('stops', [])
        listing_ids = [s.get('listing_id') for s in stops if s.get('listing_id')]
        if not listing_ids:
            return False
        placeholders = ','.join('?' for _ in listing_ids)
        row = db.execute(
            f"""SELECT 1 FROM allocations al
                JOIN recipient_requests rr ON al.request_id = rr.id
                WHERE al.listing_id IN ({placeholders})
                  AND (rr.recipient_id = ? OR rr.organization_name = ? OR rr.organization_name = ?)
                LIMIT 1""",
            (*listing_ids, user['id'], user.get('organization') or '', user.get('display_name') or '')
        ).fetchone()
        return row is not None
    return False


# ── CSRF Protection Utility ────────────────────────────────────────────────
import secrets

def generate_csrf_token():
    """Generate or retrieve the session-bound CSRF token."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']


def validate_csrf_token(token=None):
    """Validate CSRF token against session."""
    expected = session.get('_csrf_token')
    if not expected:
        return False
    token_to_check = token or request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
    if not token_to_check:
        return False
    return secrets.compare_digest(expected, token_to_check)
