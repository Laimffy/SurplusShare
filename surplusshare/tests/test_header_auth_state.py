"""
tests/test_header_auth_state.py — Authentication State & Dashboard Header Tests

Verifies the 10 scenarios requested for SurplusShare authentication and header consistency:
1. Guest visits public website -> Sign In is visible, profile controls hidden.
2. Donor logs in -> Sign In completely disappears; Sunrise Bakery profile and dropdown appear.
3. Recipient logs in -> Sign In disappears; Community Pantry A profile and dropdown appear.
4. Volunteer logs in -> Sign In disappears; Juan Volunteer profile and dropdown appear.
5. Admin logs in -> Admin profile and dropdown appear.
6. User logs out -> Session invalidated, profile disappears, Sign In returns.
7. Logged-out user attempts to access a protected dashboard -> Redirected to /login.
8. Demo role switching correctly displays demo indicator and cannot bypass database authentication.
9. Refreshing an authenticated dashboard consistently preserves the correct header.
10. Anti-caching security headers prevent browser back-button access after logout.
"""

import pytest
import re
from database.db import get_db


@pytest.fixture(autouse=True)
def setup_seed(init_db_fixture):
    """Ensure database is initialized and seeded for every test."""
    pass


def login_as(client, username, password='password123'):
    """Helper to log in as a specific user."""
    return client.post('/login', data={'identifier': username, 'password': password}, follow_redirects=True)


def extract_header_html(html_str):
    """Extract <header class="app-header">...</header> content for focused assertions."""
    match = re.search(r'<header class="app-header">.*?</header>', html_str, re.DOTALL)
    if match:
        return match.group(0)
    return html_str


# ── Scenario 1: Guest visits public website ─────────────────────────────────
def test_scenario_1_guest_public_website_shows_signin(client):
    """Verify unauthenticated guests see Sign In and Register, and profile dropdown is hidden."""
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.data.decode()

    # Public navbar shows Sign In and Register
    assert "Sign In" in html
    assert "Register" in html
    # Profile dropdown should not be present
    assert "headerUserDropdown" not in html
    assert "Sign Out" not in html


# ── Scenario 2: Donor logs in ───────────────────────────────────────────────
def test_scenario_2_donor_dashboard_header(client):
    """Verify Donor dashboard header displays Sunrise Bakery, role, and hides Sign In."""
    login_as(client, 'sunrise_bakery')

    for url in ['/donor/dashboard', '/dashboard']:
        resp = client.get(url)
        assert resp.status_code == 200
        html = resp.data.decode()
        header = extract_header_html(html)

        # Sign In button must be completely absent from the header
        assert "Sign In" not in header
        # Donor details must be present
        assert "Sunrise Bakery" in header
        assert "donor" in header.lower()
        # Dropdown menu must be present
        assert "headerUserDropdown" in header
        assert "Donation Dashboard" in header
        assert "Sign Out" in header


# ── Scenario 3: Recipient logs in ───────────────────────────────────────────
def test_scenario_3_recipient_dashboard_header(client):
    """Verify Recipient dashboard header displays Community Pantry A, role, and hides Sign In."""
    login_as(client, 'community_pantry_a')

    for url in ['/recipient/dashboard', '/dashboard']:
        resp = client.get(url)
        assert resp.status_code == 200
        html = resp.data.decode()
        header = extract_header_html(html)

        assert "Sign In" not in header
        assert "Community Pantry A" in header
        assert "recipient" in header.lower()
        assert "headerUserDropdown" in header
        assert "Recipient Dashboard" in header
        assert "Sign Out" in header


# ── Scenario 4: Volunteer logs in ───────────────────────────────────────────
def test_scenario_4_volunteer_dashboard_header(client):
    """Verify Volunteer dashboard header displays Juan Volunteer, role, and hides Sign In."""
    login_as(client, 'juan_volunteer')

    for url in ['/volunteer/dashboard', '/dashboard']:
        resp = client.get(url)
        assert resp.status_code == 200
        html = resp.data.decode()
        header = extract_header_html(html)

        assert "Sign In" not in header
        assert "Juan Volunteer" in header
        assert "volunteer" in header.lower()
        assert "headerUserDropdown" in header
        assert "Pickup Dashboard" in header
        assert "Sign Out" in header


# ── Scenario 5: Admin logs in ───────────────────────────────────────────────
def test_scenario_5_admin_dashboard_header(client):
    """Verify Admin dashboard header displays Admin User, role, and hides Sign In."""
    login_as(client, 'admin_user')

    for url in ['/admin/dashboard', '/dashboard']:
        resp = client.get(url)
        assert resp.status_code == 200
        html = resp.data.decode()
        header = extract_header_html(html)

        assert "Sign In" not in header
        assert "Admin User" in header
        assert "admin" in header.lower()
        assert "headerUserDropdown" in header
        assert "Admin Dashboard" in header
        assert "Sign Out" in header


# ── Scenario 6: User logs out ───────────────────────────────────────────────
def test_scenario_6_logout_invalidates_session_and_restores_signin(client):
    """Verify logging out completely clears the session and restores the guest state."""
    login_as(client, 'sunrise_bakery')

    # Confirm authenticated
    resp_dash = client.get('/dashboard')
    assert "headerUserDropdown" in extract_header_html(resp_dash.data.decode())

    # Perform logout
    resp_logout = client.get('/logout', follow_redirects=True)
    assert resp_logout.status_code == 200
    logout_html = resp_logout.data.decode()

    # Session must be empty of user credentials
    with client.session_transaction() as sess:
        assert 'user_id' not in sess
        assert 'username' not in sess

    # Flash message present
    assert "safely signed out" in logout_html

    # Visiting home page shows Sign In again
    assert "Sign In" in logout_html
    assert "headerUserDropdown" not in logout_html


# ── Scenario 7: Logged-out user protected dashboard access ──────────────────
def test_scenario_7_logged_out_user_protected_dashboard_redirects(client):
    """Verify that after logout, attempting to access protected dashboards redirects to /login."""
    login_as(client, 'sunrise_bakery')
    client.get('/logout')

    protected_urls = ['/dashboard', '/donor/dashboard', '/recipient/dashboard', '/volunteer/dashboard', '/admin/dashboard']
    for url in protected_urls:
        resp = client.get(url)
        assert resp.status_code == 302, f"Expected 302 redirect for {url}, got {resp.status_code}"
        assert '/login' in resp.headers.get('Location', '')


# ── Scenario 8: Demo mode indicator & authentication boundary ───────────────
def test_scenario_8_demo_role_switching_and_indicators(client, app):
    """Verify demo switching tags session as demo user and displays demo badge."""
    # Demo switch to donor
    resp_switch = client.post('/auth/demo-switch', data={'target_user': 'sunrise_bakery'}, follow_redirects=True)
    assert resp_switch.status_code == 200
    html = resp_switch.data.decode()
    header = extract_header_html(html)

    # Demo badge appears in header
    assert "Demo" in header
    assert "Sign In" not in header
    assert "Sunrise Bakery" in header

    # In production (disabled demo switching), switching is rejected
    app.config['DEMO_ROLE_SWITCHING_ENABLED'] = False
    client_prod = app.test_client()
    resp_prod = client_prod.post('/auth/demo-switch', data={'target_user': 'admin_user'})
    assert resp_prod.status_code == 403


# ── Scenario 9: Refreshing dashboard preserves header ───────────────────────
def test_scenario_9_refreshing_authenticated_dashboard_preserves_header(client):
    """Verify consecutive requests to dashboards maintain consistent authenticated header."""
    login_as(client, 'community_pantry_a')

    for _ in range(3):
        resp = client.get('/dashboard')
        assert resp.status_code == 200
        header = extract_header_html(resp.data.decode())
        assert "Sign In" not in header
        assert "Community Pantry A" in header
        assert "headerUserDropdown" in header


# ── Scenario 10: Anti-caching security headers ──────────────────────────────
def test_scenario_10_anti_caching_headers_prevent_back_button_restoration(client):
    """Verify HTML responses include Cache-Control headers to instruct browsers not to cache."""
    resp = client.get('/')
    assert resp.status_code == 200
    cache_control = resp.headers.get('Cache-Control', '')
    assert 'no-cache' in cache_control
    assert 'no-store' in cache_control
    assert resp.headers.get('Pragma') == 'no-cache'
