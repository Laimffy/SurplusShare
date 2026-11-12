"""
services/audit_service.py — Security Audit Logging Service

Records security-relevant events and administrative operations:
- User authentication events (login, logout, registration)
- Resource mutations (create, update, delete on listings, requests, schedules, partners, news, faqs)
- Algorithmic triggers (matching engine execution)
- Role and permission changes
"""

from datetime import datetime
from flask import request
from database.db import get_db
from services.auth_service import get_current_user


def log_audit(action, resource_type, resource_id=None, details=None, user=None):
    """Write an entry to the audit_logs table.
    
    Args:
        action (str): Action code (e.g. 'LOGIN', 'CREATE_LISTING', 'DELETE_LISTING', 'EXECUTE_MATCHING').
        resource_type (str): Type of resource (e.g. 'user', 'food_listings', 'recipient_requests', 'matching_engine').
        resource_id (str, optional): Target resource identifier.
        details (str, optional): Additional context or summary.
        user (dict, optional): Overriding user dict; if None, resolves current_user automatically.
    """
    if user is None:
        try:
            user = get_current_user()
        except Exception:
            user = None

    user_id = user['id'] if user else None
    username = user['username'] if user else 'anonymous'
    role = user['role'] if user else 'public'

    ip_address = '127.0.0.1'
    try:
        if request:
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1')
            if ',' in ip_address:
                ip_address = ip_address.split(',')[0].strip()
    except Exception:
        pass

    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    try:
        db = get_db()
        db.execute(
            """INSERT INTO audit_logs
               (user_id, username, role, action, resource_type, resource_id, details, ip_address, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, username, role, action, resource_type, str(resource_id) if resource_id else None, details, ip_address, timestamp),
        )
        db.commit()
    except Exception as e:
        # Don't let logging failures crash main application logic
        print(f"[AuditLog Error] Failed to write audit log: {e}")


def get_audit_logs(limit=100, offset=0, action_filter=None, role_filter=None, search_term=None):
    """Retrieve filtered audit log records for administrative review."""
    db = get_db()
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []

    if action_filter:
        query += " AND action = ?"
        params.append(action_filter)

    if role_filter:
        query += " AND role = ?"
        params.append(role_filter)

    if search_term:
        query += " AND (username LIKE ? OR resource_type LIKE ? OR resource_id LIKE ? OR details LIKE ?)"
        like_term = f"%{search_term}%"
        params.extend([like_term, like_term, like_term, like_term])

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_audit_log_stats():
    """Retrieve aggregate statistics on security audit events."""
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS c FROM audit_logs").fetchone()['c']
    recent = db.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 5").fetchall()
    action_counts = db.execute(
        "SELECT action, COUNT(*) AS count FROM audit_logs GROUP BY action ORDER BY count DESC LIMIT 6"
    ).fetchall()

    return {
        'total_events': total,
        'recent_events': [dict(r) for r in recent],
        'top_actions': [dict(r) for r in action_counts],
    }
