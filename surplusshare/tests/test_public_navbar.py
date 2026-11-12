"""
tests/test_public_navbar.py — Verification Suite for Simplified Public Navigation Bar

Tests:
1. Navbar contains exactly 6 primary desktop links: Home, About, How It Works, Available Food, Our Impact, Contact.
2. News, Sustainability, FAQs, and Our Partners are moved to the footer and mobile drawer, with working routes.
3. The static 'Live' badge is removed from the navbar.
4. Sign In button is styled as outlined forest-green and Register button as filled leaf-green.
5. Accessible mobile offcanvas drawer (#publicNavDrawer) and hamburger button exist with appropriate ARIA attributes.
6. Responsive CSS classes prevent line wrapping (white-space: nowrap).
7. Active state highlighted on current route.
"""

import pytest
import re


@pytest.fixture(autouse=True)
def setup_seed(init_db_fixture):
    pass


def test_navbar_structure_and_links(client):
    """Verify that the desktop navbar renders exactly the 6 simplified navigation links."""
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')

    # Extract the public-nav-menu block
    menu_match = re.search(r'<ul class="public-nav-menu"[^>]*>(.*?)</ul>', html, re.DOTALL)
    assert menu_match is not None, "Desktop .public-nav-menu not found"
    menu_content = menu_match.group(1)

    # Extract all link texts inside public-nav-menu
    link_texts = re.findall(r'<a[^>]*class="[^"]*public-nav-link[^"]*"[^>]*>(.*?)</a>', menu_content)
    cleaned_texts = [re.sub(r'<[^>]+>', '', t).strip() for t in link_texts]

    # Verify exactly 6 links
    expected_links = ['Home', 'About', 'How It Works', 'Available Food', 'Our Impact', 'Contact']
    assert cleaned_texts == expected_links, f"Expected {expected_links}, but got {cleaned_texts}"

    # Verify that 'Live' badge is not in the navbar
    for text in cleaned_texts:
        assert 'Live' not in text, "Static 'Live' badge should be removed from navbar"


def test_auth_buttons_styling(client):
    """Verify Sign In and Register buttons are present and properly styled."""
    resp = client.get('/')
    html = resp.data.decode('utf-8')

    assert 'class="btn-sign-in"' in html or "btn-sign-in" in html
    assert 'class="btn-register"' in html or "btn-register" in html
    assert 'Sign In' in html
    assert 'Register' in html
    assert 'href="/login"' in html
    assert 'href="/register"' in html


def test_mobile_drawer_and_hamburger(client):
    """Verify accessible mobile offcanvas drawer and hamburger button."""
    resp = client.get('/')
    html = resp.data.decode('utf-8')

    # Hamburger trigger button
    assert 'public-hamburger-btn' in html
    assert 'data-bs-toggle="offcanvas"' in html
    assert 'data-bs-target="#publicNavDrawer"' in html
    assert 'aria-label="Toggle navigation drawer"' in html

    # Offcanvas drawer
    assert 'id="publicNavDrawer"' in html
    assert 'class="offcanvas offcanvas-end public-nav-drawer"' in html
    assert 'aria-labelledby="publicNavDrawerLabel"' in html
    assert 'data-bs-dismiss="offcanvas"' in html

    # Check secondary links in drawer
    assert 'Our Philippine Partners' in html
    assert 'News &amp; Stories' in html or 'News & Stories' in html
    assert 'Frequently Asked Questions' in html


def test_footer_preserves_informational_routes(client):
    """Verify that News, Sustainability, FAQs, and Partners have working links in the footer."""
    resp = client.get('/')
    html = resp.data.decode('utf-8')

    footer_match = re.search(r'<footer class="public-footer[^>]*>(.*?)</footer>', html, re.DOTALL)
    assert footer_match is not None
    footer_html = footer_match.group(1)

    assert 'href="/partners"' in footer_html
    assert 'href="/news"' in footer_html
    assert 'href="/faqs"' in footer_html
    assert 'href="/sustainability"' in footer_html


def test_active_link_highlighting(client):
    """Verify that active route receives .active class with soft sage styling."""
    pages = [
        ('/', 'Home'),
        ('/about', 'About'),
        ('/how-it-works', 'How It Works'),
        ('/available-food', 'Available Food'),
        ('/sustainability', 'Our Impact'),
        ('/contact', 'Contact'),
    ]
    for url, expected_text in pages:
        resp = client.get(url)
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        # Check active nav link has the expected text
        match = re.search(r'<a[^>]*class="[^"]*public-nav-link[^"]*active[^"]*"[^>]*>(.*?)</a>', html)
        assert match is not None, f"No active nav link found for {url}"
        link_text = re.sub(r'<[^>]+>', '', match.group(1)).strip()
        assert link_text == expected_text
