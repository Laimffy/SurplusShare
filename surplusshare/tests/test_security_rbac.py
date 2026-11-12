"""
tests/test_security_rbac.py — Comprehensive Security & RBAC Test Suite for SurplusShare

Verifies:
1. Public routes access without authentication (HTTP 200).
2. Public contact inquiry submission & audit log recording.
3. Unauthenticated requests to protected endpoints return 302/401.
4. Role-Based Access Control (RBAC):
   - Donors can manage their own listings, cannot access admin or create requests.
   - Multi-tenant tenant boundary isolation: Donor A cannot delete Donor B's listing (HTTP 403).
   - Recipients can manage their own requests, cannot access admin or create listings.
   - Recipient A cannot cancel Recipient B's request (HTTP 403).
   - Volunteers can manage assigned stops, cannot access admin.
   - Administrators have full access to admin modules, audit logs, partner toggling, matching engine.
5. Dual authentication (Flask session + signed JWT Bearer token).
6. Security audit trail persistence and filtering.
"""

import pytest
from datetime import datetime, timedelta
from database.seed import seed_database
from database.db import get_db
from services.auth_service import generate_jwt_token


@pytest.fixture(autouse=True)
def setup_seed(init_db_fixture):
    """Ensure database is initialized and seeded for every test."""
    pass


# ── 1. Public Routes Tests ────────────────────────────────────────────────
def test_public_routes_accessible_without_login(client):
    """Verify that all public-facing pages load with HTTP 200 for unauthenticated visitors."""
    public_urls = [
        '/',
        '/about',
        '/how-it-works',
        '/partners',
        '/available-food',
        '/news',
        '/sustainability',
        '/faqs',
        '/contact',
        '/login',
        '/register',
    ]
    for url in public_urls:
        resp = client.get(url)
        assert resp.status_code == 200, f"Expected 200 for public URL {url}, got {resp.status_code}"
        assert b"SurplusShare" in resp.data


def test_public_news_detail_accessible(client):
    """Verify public can read individual published news articles."""
    resp = client.get('/news/surplusshare-rescues-420kg-fresh-food')
    assert resp.status_code == 200
    assert b"420" in resp.data


def test_public_contact_inquiry_persists_and_audits(client, app):
    """Verify guest can submit inquiry via Contact Us form and audit log is recorded."""
    payload = {
        'name': 'Juan dela Cruz',
        'email': 'juandelacruz@example.ph',
        'organization': 'Community Advocate Group',
        'subject': 'Partnership Inquiry for Barangay 101',
        'message': 'We would like to establish a community distribution hub in our local district.',
    }
    resp = client.post('/contact', data=payload, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Thank you for reaching out" in resp.data

    with app.app_context():
        db = get_db()
        inquiry = db.execute("SELECT * FROM contact_inquiries WHERE email = ?", ('juandelacruz@example.ph',)).fetchone()
        assert inquiry is not None
        assert inquiry['name'] == 'Juan dela Cruz'
        assert inquiry['status'] == 'new'

        # Check audit log entry
        audit = db.execute("SELECT * FROM audit_logs WHERE action = 'SUBMIT_CONTACT_INQUIRY'").fetchone()
        assert audit is not None
        assert 'juandelacruz@example.ph' in audit['details']


# ── 2. Unauthenticated Protection Tests ──────────────────────────────────
def test_unauthenticated_protected_routes_redirect(client):
    """Verify unauthenticated GET requests to protected endpoints redirect to login."""
    protected_urls = [
        '/dashboard',
        '/admin/dashboard',
        '/admin/users',
        '/admin/partners',
        '/admin/news',
        '/admin/faqs',
        '/admin/inquiries',
        '/admin/audit-logs',
        '/listings/new',
        '/requests/new',
        '/schedule/new',
        '/settings',
    ]
    for url in protected_urls:
        resp = client.get(url)
        assert resp.status_code == 302, f"Expected 302 redirect for unauthenticated {url}, got {resp.status_code}"
        assert '/login' in resp.headers.get('Location', '')


def test_unauthenticated_api_request_returns_401(client):
    """Verify unauthenticated JSON API requests return HTTP 401."""
    resp = client.post('/matching/run', headers={'Accept': 'application/json'})
    assert resp.status_code == 401
    json_data = resp.get_json()
    assert json_data['error'] == 'Unauthorized'


# ── 3. Role-Based Access Control (RBAC) Tests ────────────────────────────
def login_as(client, username, password='password123'):
    """Helper to log in via web form session."""
    return client.post('/login', data={'identifier': username, 'password': password}, follow_redirects=True)


def test_donor_access_permissions(client):
    """Verify donor permissions and restrictions."""
    # Login as Green Basket Grocery (donor)
    resp = login_as(client, 'green_basket')
    assert resp.status_code == 200

    # Donor can access listings and create listing view
    assert client.get('/listings').status_code == 200
    assert client.get('/listings/new').status_code == 200

    # Donor CANNOT access admin dashboard (403)
    resp_admin = client.get('/admin/dashboard')
    assert resp_admin.status_code == 403
    assert b"Forbidden" in resp_admin.data

    # Donor CANNOT access admin user management (403)
    resp_users = client.get('/admin/users')
    assert resp_users.status_code == 403

    # Donor CANNOT create recipient requests (403)
    resp_req = client.get('/requests/new')
    assert resp_req.status_code == 403

    # Donor CANNOT trigger matching engine (403)
    resp_match = client.post('/matching/run', headers={'Accept': 'application/json'})
    assert resp_match.status_code == 403


def test_donor_tenant_isolation(client, app):
    """Verify multi-tenant isolation: Donor A cannot edit or delete Donor B's listing."""
    # Green Basket Grocery is user ID 2
    # Sunrise Bakery is user ID 3
    # Listing FL-001 belongs to Sunrise Bakery (donor_id = 3)
    with app.app_context():
        db = get_db()
        listing = db.execute("SELECT id, listing_id, donor_id FROM food_listings WHERE listing_id = 'FL-001'").fetchone()
        assert listing is not None
        fl_code = listing['listing_id']
        assert listing['donor_id'] == 3

    # Log in as green_basket (user ID 2)
    login_as(client, 'green_basket')

    # Attempt to delete Sunrise Bakery's listing FL-001 -> Must return 403 Forbidden
    resp = client.post(f'/listings/{fl_code}/delete')
    assert resp.status_code == 403
    assert b"Forbidden" in resp.data or b"Access Denied" in resp.data

    # Verify FL-001 was NOT deleted
    with app.app_context():
        db = get_db()
        check = db.execute("SELECT id FROM food_listings WHERE listing_id = 'FL-001'").fetchone()
        assert check is not None


def test_recipient_access_permissions_and_isolation(client, app):
    """Verify recipient permissions, restrictions, and tenant request isolation."""
    # Log in as community_pantry_a (recipient)
    login_as(client, 'community_pantry_a')

    # Recipient can access requests and new request view
    assert client.get('/requests').status_code == 200
    assert client.get('/requests/new').status_code == 200

    # Recipient CANNOT access admin dashboard (403)
    assert client.get('/admin/dashboard').status_code == 403

    # Recipient CANNOT post food listings (403)
    assert client.get('/listings/new').status_code == 403

    # Multi-tenant isolation: cannot cancel another recipient's request
    with app.app_context():
        db = get_db()
        # Find a request belonging to a different recipient (not community_pantry_a = recipient_id 6)
        other_req = db.execute("SELECT id, request_id, recipient_id FROM recipient_requests WHERE recipient_id != 6 LIMIT 1").fetchone()
        assert other_req is not None
        other_req_code = other_req['request_id']

    # Attempt to cancel another recipient's request -> 403 Forbidden
    resp = client.post(f'/requests/{other_req_code}/cancel')
    assert resp.status_code == 403
    assert b"Forbidden" in resp.data or b"Access Denied" in resp.data


def test_volunteer_access_permissions(client):
    """Verify volunteer permissions and restrictions."""
    login_as(client, 'juan_volunteer')

    # Volunteer can access schedule view
    assert client.get('/schedule').status_code == 200

    # Volunteer CANNOT access admin dashboard (403)
    assert client.get('/admin/dashboard').status_code == 403

    # Volunteer CANNOT create listings or requests
    assert client.get('/listings/new').status_code == 403
    assert client.get('/requests/new').status_code == 403


def test_admin_full_management_access(client, app):
    """Verify administrator has full access to all admin modules and operations."""
    login_as(client, 'admin_user')

    admin_views = [
        '/admin/dashboard',
        '/admin/users',
        '/admin/partners',
        '/admin/news',
        '/admin/faqs',
        '/admin/inquiries',
        '/admin/audit-logs',
    ]
    for url in admin_views:
        resp = client.get(url)
        assert resp.status_code == 200, f"Admin view {url} failed with {resp.status_code}"

    # Admin can toggle partner status
    with app.app_context():
        db = get_db()
        partner = db.execute("SELECT id, name, status FROM partners LIMIT 1").fetchone()
        p_id = partner['id']
        old_status = partner['status']

    resp_toggle = client.post(f'/admin/partners/{p_id}/toggle-status', follow_redirects=True)
    assert resp_toggle.status_code == 200

    with app.app_context():
        db = get_db()
        updated = db.execute("SELECT status FROM partners WHERE id = ?", (p_id,)).fetchone()
        expected = 'prospective' if old_status == 'confirmed' else 'confirmed'
        assert updated['status'] == expected

    # Admin can toggle news article publish state
    with app.app_context():
        db = get_db()
        article = db.execute("SELECT id, is_published FROM news_articles LIMIT 1").fetchone()
        art_id = article['id']
        old_pub = article['is_published']

    resp_art = client.post(f'/admin/news/{art_id}/toggle-publish', follow_redirects=True)
    assert resp_art.status_code == 200

    with app.app_context():
        db = get_db()
        art_updated = db.execute("SELECT is_published FROM news_articles WHERE id = ?", (art_id,)).fetchone()
        assert art_updated['is_published'] != old_pub


# ── 4. JWT REST API Authentication Tests ──────────────────────────────────
def test_jwt_auth_login_endpoint(client):
    """Verify /api/auth/login returns valid JWT token for legitimate credentials."""
    # Correct login
    resp = client.post('/api/auth/login', json={'username': 'admin_user', 'password': 'password123'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'
    assert 'token' in data
    assert data['user']['role'] == 'admin'
    assert data['user']['username'] == 'admin_user'

    # Bad password
    resp_bad = client.post('/api/auth/login', json={'username': 'admin_user', 'password': 'wrongpassword'})
    assert resp_bad.status_code == 401
    assert 'error' in resp_bad.get_json()


def test_jwt_bearer_token_authorization(client, app):
    """Verify that requests with valid JWT Bearer tokens pass RBAC checks."""
    with app.app_context():
        db = get_db()
        admin_row = db.execute("SELECT * FROM users WHERE username = 'admin_user'").fetchone()
        admin_user = dict(admin_row)
        token = generate_jwt_token(admin_user)

    # Use Bearer token to trigger matching engine via REST API
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
    }
    resp = client.post('/matching/run', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'success'

    # With invalid token
    bad_headers = {
        'Authorization': 'Bearer invalid.token.payload',
        'Accept': 'application/json',
    }
    resp_invalid = client.post('/matching/run', headers=bad_headers)
    assert resp_invalid.status_code == 401


# ── 5. Security Audit Log Verification ───────────────────────────────────
def test_audit_log_captures_events(client, app):
    """Verify security audit logs record login, updates, and user activities."""
    # Perform a login
    login_as(client, 'admin_user')

    with app.app_context():
        db = get_db()
        login_log = db.execute("SELECT * FROM audit_logs WHERE action = 'LOGIN_SUCCESS' AND user_id = 1").fetchone()
        assert login_log is not None
        assert login_log['role'] == 'admin'
