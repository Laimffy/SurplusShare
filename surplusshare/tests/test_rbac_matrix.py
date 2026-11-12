"""
tests/test_rbac_matrix.py — Comprehensive Role-Based Access Control (RBAC) Test Matrix

Verifies least privilege enforcement across all four roles:
1. Admin (Full system control, algorithms, benchmarks, matching, reports, user admin)
2. Donor (Scoped dashboard, own listing CRUD, handover, isolated from matching/benchmarks/requests)
3. Recipient (Scoped dashboard, own request CRUD, confirm receipt, isolated from listings/matching/benchmarks)
4. Volunteer (Scoped dashboard, assigned routes DLL navigation, stop status updates, isolated from admin/other routes)
5. Demo Role Switching (Safe seeded switching, disabled in production)
6. CSRF utilities and 403 Access Denied presentation
"""

import pytest
from datetime import datetime, timedelta
from database.db import get_db
from services.auth_service import generate_csrf_token, validate_csrf_token


@pytest.fixture(autouse=True)
def setup_seed(init_db_fixture):
    """Ensure database is initialized and seeded for every test."""
    pass


def login_as(client, username, password='password123'):
    """Helper to establish an authenticated session via login."""
    return client.post('/login', data={'identifier': username, 'password': password}, follow_redirects=True)


# ═════════════════════════════════════════════════════════════════════════════
# 1. ADMIN RBAC MATRIX TESTS
# ═════════════════════════════════════════════════════════════════════════════

def test_admin_full_system_access(client):
    """Verify Admin has access to all administrative modules, algorithms, and reports."""
    login_as(client, 'admin_user')

    admin_endpoints = [
        '/dashboard',
        '/admin/dashboard',
        '/admin/users',
        '/admin/partners',
        '/admin/news',
        '/admin/faqs',
        '/admin/inquiries',
        '/admin/audit-logs',
        '/benchmark',
        '/matching',
        '/reports',
        '/reports/export/csv',
        '/settings',
        '/listings',
        '/requests',
        '/schedule',
    ]
    for url in admin_endpoints:
        resp = client.get(url)
        assert resp.status_code == 200, f"Admin expected 200 on {url}, got {resp.status_code}"


def test_admin_can_run_benchmark_and_matching(client):
    """Verify Admin can trigger algorithm benchmarks and matching engine."""
    login_as(client, 'admin_user')

    # Run Benchmark API
    resp_bench = client.post('/api/benchmark/run', json={'dataset_size': 500, 'query_count': 50, 'trials': 2})
    assert resp_bench.status_code == 200
    data = resp_bench.get_json()
    assert data['status'] == 'success'
    assert 'merge_sort' in data
    assert 'linear_search' in data
    assert 'binary_search' in data

    # Run Matching Engine
    resp_match = client.post('/matching/run', headers={'Accept': 'application/json'})
    assert resp_match.status_code == 200
    m_data = resp_match.get_json()
    assert m_data['status'] == 'success'


def test_admin_can_manage_schedule_stops(client, app):
    """Verify Admin can add and remove stops on any pickup schedule."""
    login_as(client, 'admin_user')

    # Add stop
    stop_payload = {
        'donor_name': 'Sunrise Bakery',
        'pickup_location': '78 Maginhawa St, QC',
        'scheduled_time': '14:00',
        'stop_order': '4',
        'notes': 'Admin added stop test',
    }
    resp_add = client.post('/schedule/PS-001/stops', data=stop_payload, follow_redirects=True)
    assert resp_add.status_code == 200

    # Verify stop was added
    with app.app_context():
        db = get_db()
        added_stop = db.execute("SELECT * FROM pickup_stops WHERE notes = 'Admin added stop test'").fetchone()
        assert added_stop is not None
        stop_id = added_stop['stop_id']

    # Remove stop
    resp_rem = client.post('/schedule/stops/' + stop_id + '/remove', data={'schedule_id': 'PS-001'}, follow_redirects=True)
    assert resp_rem.status_code == 200

    with app.app_context():
        db = get_db()
        check = db.execute("SELECT * FROM pickup_stops WHERE stop_id = ?", (stop_id,)).fetchone()
        assert check is None


# ═════════════════════════════════════════════════════════════════════════════
# 2. DONOR RBAC MATRIX TESTS
# ═════════════════════════════════════════════════════════════════════════════

def test_donor_scoped_dashboard(client):
    """Verify Donor dashboard shows donor-scoped metrics and action CTAs."""
    login_as(client, 'sunrise_bakery')
    resp = client.get('/dashboard')
    assert resp.status_code == 200
    assert b"Donor Portal" in resp.data or b"Donor Dashboard" in resp.data or b"Post Food Surplus" in resp.data


def test_donor_listing_crud_and_isolation(client, app):
    """Verify Donor can manage own listings but is strictly blocked from modifying others."""
    login_as(client, 'sunrise_bakery')

    # 1. Create listing
    new_data = {
        'food_name': 'Artisan Sourdough Loaves',
        'category': 'Bakery',
        'quantity': '20',
        'unit': 'pieces',
        'expiry_at': (datetime.now() + timedelta(days=2)).isoformat(),
        'pickup_location': '78 Maginhawa St',
        'food_condition': 'Good',
    }
    resp_create = client.post('/listings', data=new_data, follow_redirects=True)
    assert resp_create.status_code == 200
    assert b"Artisan Sourdough Loaves" in resp_create.data

    with app.app_context():
        db = get_db()
        created = db.execute("SELECT listing_id FROM food_listings WHERE food_name = 'Artisan Sourdough Loaves'").fetchone()
        assert created is not None
        own_id = created['listing_id']

    # 2. Edit own listing -> 200 / 302
    resp_edit_get = client.get(f'/listings/{own_id}/edit')
    assert resp_edit_get.status_code == 200

    resp_edit_post = client.post(f'/listings/{own_id}/edit', data={
        'food_name': 'Artisan Sourdough Loaves (Updated)',
        'category': 'Bakery',
        'quantity': '25',
        'unit': 'pieces',
        'expiry_at': (datetime.now() + timedelta(days=2)).isoformat(),
        'pickup_location': '78 Maginhawa St',
        'food_condition': 'Good',
    }, follow_redirects=True)
    assert resp_edit_post.status_code == 200

    # 3. Attempt to edit another donor's listing (FL-003 belongs to Green Basket) -> 403 Forbidden
    resp_other_edit = client.get('/listings/FL-003/edit')
    assert resp_other_edit.status_code == 403

    resp_other_post = client.post('/listings/FL-003/edit', data={'food_name': 'Tampered Veggies'})
    assert resp_other_post.status_code == 403

    # 4. Attempt to delete another donor's listing -> 403 Forbidden
    resp_other_del = client.post('/listings/FL-003/delete')
    assert resp_other_del.status_code == 403

    # 5. Delete own listing -> 302 / success
    resp_own_del = client.post(f'/listings/{own_id}/delete', follow_redirects=True)
    assert resp_own_del.status_code == 200


def test_donor_handover_confirmation(client, app):
    """Verify Donor can confirm food handover for their own listing but not others."""
    # Seed an allocation on Sunrise Bakery's listing FL-001
    with app.app_context():
        db = get_db()
        fl = db.execute("SELECT id FROM food_listings WHERE listing_id = 'FL-001'").fetchone()
        fl_id = fl['id']
        db.execute("UPDATE food_listings SET allocated_quantity = 10 WHERE id = ?", (fl_id,))
        db.execute("""INSERT OR REPLACE INTO allocations (allocation_id, listing_id, request_id, allocated_quantity, allocated_at, status)
                      VALUES ('AL-TEST-001', ?, 1, 10, datetime('now'), 'pending')""", (fl_id,))
        db.commit()

    login_as(client, 'sunrise_bakery')

    # Confirm handover on own listing FL-001 -> success
    resp = client.post('/listings/FL-001/handover', follow_redirects=True)
    assert resp.status_code == 200
    assert b"Food handover confirmed" in resp.data

    with app.app_context():
        db = get_db()
        alloc = db.execute("SELECT status FROM allocations WHERE allocation_id = 'AL-TEST-001'").fetchone()
        assert alloc['status'] == 'picked_up'

    # Attempt handover on Green Basket's listing FL-003 -> 403 Forbidden
    resp_forbidden = client.post('/listings/FL-003/handover')
    assert resp_forbidden.status_code == 403


def test_donor_restricted_from_privileged_features(client):
    """Verify Donor is blocked from recipient requests, matching, benchmarking, reports, and admin."""
    login_as(client, 'sunrise_bakery')

    restricted_endpoints = [
        ('/requests/new', 'GET', 403),
        ('/requests', 'POST', 403),
        ('/matching', 'GET', 403),
        ('/matching/run', 'POST', 403),
        ('/benchmark', 'GET', 403),
        ('/api/benchmark/run', 'POST', 403),
        ('/reports', 'GET', 403),
        ('/reports/export/csv', 'GET', 403),
        ('/admin/dashboard', 'GET', 403),
        ('/admin/users', 'GET', 403),
        ('/schedule/PS-001/stops', 'POST', 403),
    ]

    for url, method, expected_code in restricted_endpoints:
        if method == 'GET':
            resp = client.get(url)
        else:
            resp = client.post(url, headers={'Accept': 'application/json'} if 'api' in url or 'matching/run' in url else {})
        assert resp.status_code == expected_code, f"Donor on {method} {url} expected {expected_code}, got {resp.status_code}"


# ═════════════════════════════════════════════════════════════════════════════
# 3. RECIPIENT RBAC MATRIX TESTS
# ═════════════════════════════════════════════════════════════════════════════

def test_recipient_scoped_dashboard(client):
    """Verify Recipient dashboard shows recipient-scoped metrics and action CTAs."""
    login_as(client, 'community_pantry_a')
    resp = client.get('/dashboard')
    assert resp.status_code == 200
    assert b"Recipient Portal" in resp.data or b"Recipient Dashboard" in resp.data or b"Request Food" in resp.data


def test_recipient_request_crud_and_isolation(client, app):
    """Verify Recipient can create/cancel own requests but cannot cancel another recipient's request."""
    login_as(client, 'community_pantry_a')

    # 1. Create request
    req_data = {
        'organization_name': 'Community Pantry A',
        'food_category': 'Vegetables',
        'requested_quantity': '30',
        'quantity_unit': 'kg',
        'min_shelf_life_hours': '12',
    }
    resp_create = client.post('/requests', data=req_data, follow_redirects=True)
    assert resp_create.status_code == 200
    assert b"added to FIFO queue successfully" in resp_create.data

    with app.app_context():
        db = get_db()
        created = db.execute("SELECT request_id FROM recipient_requests WHERE organization_name = 'Community Pantry A' ORDER BY id DESC LIMIT 1").fetchone()
        assert created is not None
        own_req_id = created['request_id']

    # 2. Cancel own request -> success
    resp_cancel = client.post(f'/requests/{own_req_id}/cancel', follow_redirects=True)
    assert resp_cancel.status_code == 200
    assert b"cancelled successfully" in resp_cancel.data

    # 3. Attempt to cancel Hope Feeding Program's request (RR-002) -> 403 Forbidden
    resp_other_cancel = client.post('/requests/RR-002/cancel')
    assert resp_other_cancel.status_code == 403


def test_recipient_confirm_delivery_receipt(client, app):
    """Verify Recipient can confirm delivery receipt for their own request."""
    login_as(client, 'community_pantry_a')

    # RR-009 belongs to Community Pantry A and is fulfilled
    resp = client.post('/requests/RR-009/confirm-receipt', follow_redirects=True)
    assert resp.status_code == 200
    assert b"Delivery receipt confirmed" in resp.data

    # Attempt to confirm receipt for Hope Feeding Program's request (RR-002) -> 403 Forbidden
    resp_other = client.post('/requests/RR-002/confirm-receipt')
    assert resp_other.status_code == 403


def test_recipient_restricted_from_privileged_features(client):
    """Verify Recipient is blocked from posting listings, matching, benchmarks, reports, and admin."""
    login_as(client, 'community_pantry_a')

    restricted_endpoints = [
        ('/listings/new', 'GET', 403),
        ('/listings', 'POST', 403),
        ('/matching', 'GET', 403),
        ('/matching/run', 'POST', 403),
        ('/benchmark', 'GET', 403),
        ('/api/benchmark/run', 'POST', 403),
        ('/reports', 'GET', 403),
        ('/reports/export/csv', 'GET', 403),
        ('/admin/dashboard', 'GET', 403),
        ('/admin/users', 'GET', 403),
    ]

    for url, method, expected_code in restricted_endpoints:
        if method == 'GET':
            resp = client.get(url)
        else:
            resp = client.post(url, headers={'Accept': 'application/json'} if 'api' in url or 'matching/run' in url else {})
        assert resp.status_code == expected_code, f"Recipient on {method} {url} expected {expected_code}, got {resp.status_code}"


# ═════════════════════════════════════════════════════════════════════════════
# 4. VOLUNTEER RBAC MATRIX TESTS
# ═════════════════════════════════════════════════════════════════════════════

def test_volunteer_scoped_dashboard(client):
    """Verify Volunteer dashboard shows volunteer-scoped route info."""
    login_as(client, 'juan_volunteer')
    resp = client.get('/dashboard')
    assert resp.status_code == 200
    assert b"Volunteer Portal" in resp.data or b"Volunteer Dashboard" in resp.data or b"My Assigned Pickups" in resp.data


def test_volunteer_schedule_access_and_isolation(client, app):
    """Verify Volunteer can only view and manage assigned schedules and stops."""
    # Seed a second schedule assigned to Maria Volunteer
    with app.app_context():
        db = get_db()
        db.execute("""INSERT OR REPLACE INTO pickup_schedules (schedule_id, volunteer_name, schedule_date, status)
                      VALUES ('PS-002', 'Maria Volunteer', datetime('now', '+1 day'), 'planned')""")
        m_sched = db.execute("SELECT id FROM pickup_schedules WHERE schedule_id = 'PS-002'").fetchone()
        db.execute("""INSERT OR REPLACE INTO pickup_stops (stop_id, schedule_id, donor_name, pickup_location, scheduled_time, stop_order, status, notes)
                      VALUES ('ST-099', ?, 'Fresh Fields Market', '290 Commonwealth Ave', '15:00', 1, 'pending', 'Maria test stop')""", (m_sched['id'],))
        db.commit()

    # Log in as Juan Volunteer
    login_as(client, 'juan_volunteer')

    # 1. Juan can view own schedule PS-001
    resp_own_sched = client.get('/schedule/PS-001')
    assert resp_own_sched.status_code == 200

    # 2. Juan CANNOT view Maria's schedule PS-002 -> 403 Forbidden
    resp_other_sched = client.get('/schedule/PS-002')
    assert resp_other_sched.status_code == 403

    # 3. Juan can reorder stops on own schedule PS-001 via DLL move
    resp_move = client.post('/schedule/PS-001/stops/ST-001/move', data={'direction': 'down'}, follow_redirects=True)
    assert resp_move.status_code == 200

    # 4. Juan CANNOT reorder stops on Maria's schedule PS-002 -> 403 Forbidden
    resp_other_move = client.post('/schedule/PS-002/stops/ST-099/move', data={'direction': 'up'})
    assert resp_other_move.status_code == 403

    # 5. Juan can update stop status on own schedule to valid state ('completed')
    resp_status = client.post('/schedule/stops/ST-001/status', data={'schedule_id': 'PS-001', 'status': 'completed'}, follow_redirects=True)
    assert resp_status.status_code == 200
    assert b"status updated to" in resp_status.data

    with app.app_context():
        db = get_db()
        stop = db.execute("SELECT status FROM pickup_stops WHERE stop_id = 'ST-001'").fetchone()
        assert stop['status'] == 'completed'

    # 6. Juan CANNOT update stop status on Maria's schedule (ST-099) -> 403 Forbidden
    resp_other_status = client.post('/schedule/stops/ST-099/status', data={'schedule_id': 'PS-002', 'status': 'completed'})
    assert resp_other_status.status_code == 403


def test_volunteer_restricted_from_privileged_features(client):
    """Verify Volunteer is blocked from listings creation, requests creation, matching, benchmarks, reports, and admin."""
    login_as(client, 'juan_volunteer')

    restricted_endpoints = [
        ('/listings/new', 'GET', 403),
        ('/listings', 'POST', 403),
        ('/requests/new', 'GET', 403),
        ('/requests', 'POST', 403),
        ('/matching', 'GET', 403),
        ('/matching/run', 'POST', 403),
        ('/benchmark', 'GET', 403),
        ('/api/benchmark/run', 'POST', 403),
        ('/reports', 'GET', 403),
        ('/admin/dashboard', 'GET', 403),
        ('/admin/users', 'GET', 403),
        ('/schedule/PS-001/stops', 'POST', 403),  # Admin only add stop
        ('/schedule/stops/ST-001/remove', 'POST', 403),  # Admin only remove stop
    ]

    for url, method, expected_code in restricted_endpoints:
        if method == 'GET':
            resp = client.get(url)
        else:
            resp = client.post(url, headers={'Accept': 'application/json'} if 'api' in url or 'matching/run' in url else {})
        assert resp.status_code == expected_code, f"Volunteer on {method} {url} expected {expected_code}, got {resp.status_code}"


# ═════════════════════════════════════════════════════════════════════════════
# 5. DEMO ROLE SWITCHING SECURITY TESTS
# ═════════════════════════════════════════════════════════════════════════════

def test_demo_role_switching_success(client, app):
    """Verify demo role switching safely loads pre-seeded identities and audits events."""
    demo_targets = [
        ('admin_user', 'admin'),
        ('sunrise_bakery', 'donor'),
        ('community_pantry_a', 'recipient'),
        ('juan_volunteer', 'volunteer'),
    ]

    for target_user, expected_role in demo_targets:
        resp = client.post('/auth/demo-switch', data={'target_user': target_user}, follow_redirects=True)
        assert resp.status_code == 200
        assert f"Switched to".encode() in resp.data

        # Verify session has authentic role
        with client.session_transaction() as sess:
            assert sess['username'] == target_user
            assert sess['role'] == expected_role

    # Verify audit log captures demo switch event
    with app.app_context():
        db = get_db()
        switch_logs = db.execute("SELECT * FROM audit_logs WHERE action = 'DEMO_ROLE_SWITCH'").fetchall()
        assert len(switch_logs) >= len(demo_targets)


def test_demo_role_switching_rejects_arbitrary_or_invalid_user(client):
    """Verify demo role switching rejects non-whitelisted usernames."""
    resp = client.post('/auth/demo-switch', data={'target_user': 'malicious_hacker'}, follow_redirects=True)
    assert resp.status_code == 400


def test_demo_role_switching_disabled_in_production(app):
    """Verify demo role switcher returns 403 when DEMO_ROLE_SWITCHING_ENABLED is False."""
    app.config['DEMO_ROLE_SWITCHING_ENABLED'] = False
    client = app.test_client()

    resp = client.post('/auth/demo-switch', data={'target_user': 'admin_user'})
    assert resp.status_code == 403


# ═════════════════════════════════════════════════════════════════════════════
# 6. CSRF UTILITY AND ACCESS DENIED PAGE TESTS
# ═════════════════════════════════════════════════════════════════════════════

def test_csrf_token_generation_and_validation(app):
    """Verify session-bound CSRF token generation and validation."""
    with app.test_request_context():
        token1 = generate_csrf_token()
        assert token1 is not None
        assert len(token1) == 64  # secrets.token_hex(32) -> 64 hex characters

        # Repeated calls in same session return the same token
        token2 = generate_csrf_token()
        assert token1 == token2

        # Validate with matching token
        assert validate_csrf_token(token1) is True

        # Validate with mismatched token
        assert validate_csrf_token('invalid_token_12345') is False

        # Validate with None
        assert validate_csrf_token(None) is False


def test_access_denied_403_page_rendering(client):
    """Verify 403 Forbidden renders the custom styled error page with user context."""
    login_as(client, 'juan_volunteer')

    # Volunteer visiting admin endpoint
    resp = client.get('/admin/dashboard')
    assert resp.status_code == 403
    assert b"Access Denied" in resp.data or b"Forbidden" in resp.data
    assert b"volunteer" in resp.data.lower()


# ═════════════════════════════════════════════════════════════════════════════
# 7. UNIFIED LOGIN & ROLE-BASED REDIRECTION MATRIX TESTS
# ═════════════════════════════════════════════════════════════════════════════

def test_unified_login_role_based_redirection(client):
    """Verify single login endpoint redirects each authentic user to their specific dashboard."""
    role_dashboard_map = [
        ('admin_user', '/admin/dashboard'),
        ('sunrise_bakery', '/donor/dashboard'),
        ('community_pantry_a', '/recipient/dashboard'),
        ('juan_volunteer', '/volunteer/dashboard'),
    ]

    for username, expected_redirect in role_dashboard_map:
        # POST login without following redirect to assert exact Location header
        resp = client.post('/login', data={'identifier': username, 'password': 'password123'}, follow_redirects=False)
        assert resp.status_code == 302
        location = resp.headers.get('Location', '')
        assert (
            location == expected_redirect or
            location.endswith(expected_redirect) or
            (expected_redirect in ('/volunteer/dashboard', '/pickup/dashboard') and ('/pickup/dashboard' in location or '/volunteer/dashboard' in location))
        )

        # Follow redirect and verify HTTP 200 and role dashboard rendering
        followed = client.get(location)
        assert followed.status_code == 200


def test_public_registration_blocks_admin_role(client, app):
    """Verify public registration cannot be used to create admin accounts."""
    payload = {
        'username': 'rogue_admin',
        'display_name': 'Rogue Admin User',
        'email': 'rogue@evil.org',
        'role': 'admin',
        'password': 'password123',
        'confirm_password': 'password123',
    }
    resp = client.post('/register', data=payload)
    assert resp.status_code == 400
    assert b"Administrator accounts cannot be registered publicly" in resp.data

    with app.app_context():
        db = get_db()
        check = db.execute("SELECT id FROM users WHERE username = 'rogue_admin'").fetchone()
        assert check is None


def test_registration_allowed_roles_and_secure_hashing(client, app):
    """Verify registration creates valid accounts with hashed passwords and redirects to role dashboard."""
    new_users = [
        ('new_donor_org', 'New Bakery Donor', 'donor@bakery.ph', 'donor', '/donor/dashboard'),
        ('new_pantry_org', 'New Hope Pantry', 'pantry@hope.ph', 'recipient', '/recipient/dashboard'),
        ('new_driver_vol', 'New Volunteer Driver', 'driver@vol.ph', 'volunteer', '/volunteer/dashboard'),
    ]

    for uname, dname, email, role, expected_redirect in new_users:
        payload = {
            'username': uname,
            'display_name': dname,
            'email': email,
            'role': role,
            'password': 'securepassword123',
            'confirm_password': 'securepassword123',
        }
        resp = client.post('/register', data=payload, follow_redirects=False)
        assert resp.status_code == 302
        location = resp.headers.get('Location', '')
        assert (
            location == expected_redirect or
            location.endswith(expected_redirect) or
            (expected_redirect in ('/volunteer/dashboard', '/pickup/dashboard') and ('/pickup/dashboard' in location or '/volunteer/dashboard' in location))
        )

        # Verify password is saved as a secure hash in SQLite, not plain text
        with app.app_context():
            db = get_db()
            user_record = db.execute("SELECT * FROM users WHERE username = ?", (uname,)).fetchone()
            assert user_record is not None
            assert user_record['role'] == role
            stored_hash = user_record['password_hash']
            assert stored_hash is not None
            assert 'securepassword123' not in stored_hash
            assert stored_hash.startswith(('pbkdf2:', 'scrypt:'))


def test_dashboard_url_tampering_isolation(client):
    """Verify backend enforces role boundaries when users try to manually navigate to unauthorized dashboard URLs."""
    # 1. Unauthenticated requests to role dashboards redirect to login
    for url in ['/donor/dashboard', '/recipient/dashboard', '/volunteer/dashboard', '/admin/dashboard']:
        resp = client.get(url)
        assert resp.status_code == 302
        assert '/login' in resp.headers.get('Location', '')

    # 2. Donor attempts to access other role dashboards
    login_as(client, 'sunrise_bakery')
    assert client.get('/donor/dashboard').status_code == 200
    assert client.get('/recipient/dashboard').status_code == 403
    assert client.get('/volunteer/dashboard').status_code == 403
    assert client.get('/admin/dashboard').status_code == 403

    # 3. Recipient attempts to access other role dashboards
    login_as(client, 'community_pantry_a')
    assert client.get('/recipient/dashboard').status_code == 200
    assert client.get('/donor/dashboard').status_code == 403
    assert client.get('/volunteer/dashboard').status_code == 403
    assert client.get('/admin/dashboard').status_code == 403

    # 4. Volunteer attempts to access other role dashboards
    login_as(client, 'juan_volunteer')
    assert client.get('/volunteer/dashboard').status_code == 200
    assert client.get('/donor/dashboard').status_code == 403
    assert client.get('/recipient/dashboard').status_code == 403
    assert client.get('/admin/dashboard').status_code == 403

    # 5. Admin can access all dashboards for oversight
    login_as(client, 'admin_user')
    assert client.get('/admin/dashboard').status_code == 200
    assert client.get('/donor/dashboard').status_code == 200
    assert client.get('/recipient/dashboard').status_code == 200
    assert client.get('/volunteer/dashboard').status_code == 200

