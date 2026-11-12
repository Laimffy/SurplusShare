"""
routes/public.py — Public-Facing Website Blueprint for SurplusShare

Accessible without authentication. Provides project transparency,
available food catalog (read-only), confirmed/prospective Philippine partners,
sustainability metrics, news articles, FAQs, and a contact inquiry form.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database.db import get_db
from services.audit_service import log_audit

public = Blueprint('public', __name__)


def get_public_impact_metrics():
    """Retrieve verified, real-world impact statistics directly from the database."""
    db = get_db()
    
    # Total food rescued (sum of allocated quantities)
    res_alloc = db.execute(
        "SELECT COALESCE(SUM(allocated_quantity), 0) AS total_kg FROM allocations WHERE status != 'cancelled'"
    ).fetchone()
    total_rescued = float(res_alloc['total_kg']) if res_alloc else 0.0

    # Total successful donations (listings with allocations or rescued)
    res_listings = db.execute(
        "SELECT COUNT(*) AS c FROM food_listings WHERE allocated_quantity > 0 OR status = 'fully_allocated'"
    ).fetchone()
    total_donations = int(res_listings['c']) if res_listings else 0

    # Number of active verified partners
    res_partners = db.execute(
        "SELECT COUNT(*) AS c FROM partners WHERE status = 'confirmed'"
    ).fetchone()
    active_partners = int(res_partners['c']) if res_partners else 0

    # Number of recipient organizations served
    res_recipients = db.execute(
        "SELECT COUNT(DISTINCT organization_name) AS c FROM recipient_requests WHERE fulfilled_quantity > 0 OR status = 'fulfilled'"
    ).fetchone()
    recipients_served = int(res_recipients['c']) if res_recipients else 0

    # Completed volunteer pickup distributions
    res_completed = db.execute(
        "SELECT COUNT(*) AS c FROM pickup_stops WHERE status = 'completed'"
    ).fetchone()
    completed_distributions = int(res_completed['c']) if res_completed else 0

    # Total available food listings right now
    res_avail = db.execute(
        "SELECT COUNT(*) AS c FROM food_listings WHERE status = 'available' AND expiry_at > datetime('now')"
    ).fetchone()
    available_listings_count = int(res_avail['c']) if res_avail else 0

    return {
        'total_rescued_kg': round(total_rescued, 1),
        'total_donations': total_donations,
        'active_partners': active_partners,
        'recipients_served': recipients_served,
        'completed_distributions': completed_distributions,
        'available_listings_count': available_listings_count,
    }


# ── 1. Home ───────────────────────────────────────────────────────────────
@public.route('/')
def home():
    """Render the public landing page with impact metrics, how it works, and available food."""
    db = get_db()
    metrics = get_public_impact_metrics()

    # Get top 3 freshest available listings for public teaser
    recent_available = db.execute(
        """SELECT listing_id, food_name, category, quantity, unit,
                  pickup_location, expiry_at, storage_requirements, food_condition
           FROM food_listings
           WHERE status = 'available' AND expiry_at > datetime('now')
           ORDER BY expiry_at ASC LIMIT 3"""
    ).fetchall()

    # Get confirmed partners preview
    confirmed_partners = db.execute(
        "SELECT name, category, location, description, website_url FROM partners WHERE status = 'confirmed' ORDER BY id ASC LIMIT 4"
    ).fetchall()

    # Get latest 3 news announcements
    latest_news = db.execute(
        "SELECT title, slug, category, excerpt, published_at FROM news_articles WHERE is_published = 1 ORDER BY published_at DESC LIMIT 3"
    ).fetchall()

    return render_template(
        'public/home.html',
        metrics=metrics,
        recent_available=[dict(r) for r in recent_available],
        confirmed_partners=[dict(p) for p in confirmed_partners],
        latest_news=[dict(n) for n in latest_news],
    )


# ── 2. About Us ───────────────────────────────────────────────────────────
@public.route('/about')
def about():
    """Render project background, mission, vision, and team information."""
    metrics = get_public_impact_metrics()
    return render_template('public/about.html', metrics=metrics)


# ── 3. How It Works ───────────────────────────────────────────────────────
@public.route('/how-it-works')
def how_it_works():
    """Render the 5-step redistribution workflow and DSA algorithm explanation."""
    return render_template('public/how_it_works.html')


# ── 4. Our Philippine Partners ────────────────────────────────────────────
@public.route('/partners')
def partners():
    """Render verified confirmed partners and clearly separated prospective outreach partners."""
    db = get_db()
    category_filter = request.args.get('category', '').strip()

    query_confirmed = "SELECT * FROM partners WHERE status = 'confirmed'"
    query_prospective = "SELECT * FROM partners WHERE status = 'prospective'"
    params_c = []
    params_p = []

    if category_filter:
        query_confirmed += " AND category = ?"
        params_c.append(category_filter)
        query_prospective += " AND category = ?"
        params_p.append(category_filter)

    query_confirmed += " ORDER BY name ASC"
    query_prospective += " ORDER BY name ASC"

    confirmed = [dict(r) for r in db.execute(query_confirmed, params_c).fetchall()]
    prospective = [dict(r) for r in db.execute(query_prospective, params_p).fetchall()]

    all_categories = [
        'Bakery', 'Supermarket & Grocery', 'Catering',
        'Restaurant', 'Fast-Food', 'Local Food Establishment', 'NGO / Community'
    ]

    return render_template(
        'public/partners.html',
        confirmed_partners=confirmed,
        prospective_partners=prospective,
        categories=all_categories,
        selected_category=category_filter,
    )


# ── 5. Available Food Catalog (Public Read-Only) ──────────────────────────
@public.route('/available-food')
def available_food():
    """Public, READ-ONLY catalog of currently available surplus donations.
    
    Security: Strictly sanitized; private donor phone numbers, email addresses,
    recipient details, and internal database keys are not exposed.
    """
    db = get_db()
    search_query = request.args.get('q', '').strip()
    category_filter = request.args.get('category', '').strip()
    location_filter = request.args.get('location', '').strip()

    query = """
        SELECT listing_id, food_name, category, quantity, unit,
               pickup_location, expiry_at, storage_requirements,
               food_condition, posted_at
        FROM food_listings
        WHERE status = 'available' AND expiry_at > datetime('now')
    """
    params = []

    if search_query:
        query += " AND food_name LIKE ?"
        params.append(f"%{search_query}%")

    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)

    if location_filter:
        query += " AND pickup_location LIKE ?"
        params.append(f"%{location_filter}%")

    query += " ORDER BY expiry_at ASC"

    rows = db.execute(query, params).fetchall()
    listings = [dict(r) for r in rows]

    categories = ['Bakery', 'Vegetables', 'Fruits', 'Prepared Meals', 'Dairy', 'Dry Goods', 'Other']
    locations = ['Quezon City', 'Makati', 'Manila', 'Pasig', 'Mandaluyong']

    return render_template(
        'public/available_food.html',
        listings=listings,
        search_query=search_query,
        category_filter=category_filter,
        location_filter=location_filter,
        categories=categories,
        locations=locations,
        total_count=len(listings),
    )


# ── 6. News and Announcements ─────────────────────────────────────────────
@public.route('/news')
def news():
    """Render published news articles, community announcements, and stories."""
    db = get_db()
    category_filter = request.args.get('category', '').strip()

    query = "SELECT * FROM news_articles WHERE is_published = 1"
    params = []

    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)

    query += " ORDER BY published_at DESC"

    rows = db.execute(query, params).fetchall()
    articles = [dict(r) for r in rows]

    categories = ['Activity', 'Announcement', 'Awareness', 'Story', 'Update']

    return render_template(
        'public/news.html',
        articles=articles,
        categories=categories,
        selected_category=category_filter,
    )


@public.route('/news/<slug>')
def news_detail(slug):
    """Render a single published news article."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM news_articles WHERE slug = ? AND is_published = 1",
        (slug,),
    ).fetchone()

    if not row:
        flash('The requested article was not found or has been unpublished.', 'error')
        return redirect(url_for('public.news'))

    article = dict(row)
    # Get recent related articles
    related = db.execute(
        "SELECT title, slug, category, published_at FROM news_articles WHERE is_published = 1 AND slug != ? ORDER BY published_at DESC LIMIT 3",
        (slug,),
    ).fetchall()

    return render_template(
        'public/news_detail.html',
        article=article,
        related=[dict(r) for r in related],
    )


# ── 7. Sustainability & Community Impact ──────────────────────────────────
@public.route('/impact')
@public.route('/sustainability')
def sustainability():
    """Render UN SDG 2 & SDG 12 alignment with verified database impact metrics."""
    metrics = get_public_impact_metrics()
    
    # Calculate environmental co-benefits (approx. 2.5 kg CO2e saved per kg food waste diverted)
    co2_saved_kg = round(metrics['total_rescued_kg'] * 2.5, 1)
    meals_provided = int(metrics['total_rescued_kg'] * 2.5) # approx 400g per meal equivalent

    return render_template(
        'public/sustainability.html',
        metrics=metrics,
        co2_saved_kg=co2_saved_kg,
        meals_provided=meals_provided,
    )


# ── 8. Frequently Asked Questions (FAQs) ──────────────────────────────────
@public.route('/faqs')
def faqs():
    """Render categorized FAQs."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM faqs WHERE is_published = 1 ORDER BY category ASC, order_index ASC"
    ).fetchall()

    faq_list = [dict(r) for r in rows]
    # Group by category
    categorized_faqs = {}
    for item in faq_list:
        cat = item['category']
        if cat not in categorized_faqs:
            categorized_faqs[cat] = []
        categorized_faqs[cat].append(item)

    return render_template('public/faqs.html', categorized_faqs=categorized_faqs)


# ── 9. Contact Us ─────────────────────────────────────────────────────────
@public.route('/contact', methods=['GET', 'POST'])
def contact():
    """Render contact details and handle public contact inquiry submissions."""
    if request.method == 'GET':
        return render_template('public/contact.html')

    # Handle POST inquiry
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    subject = request.form.get('subject', '').strip()
    message = request.form.get('message', '').strip()
    organization = request.form.get('organization', '').strip()

    if not name or not email or not subject or not message:
        flash('Please fill in all required fields (Name, Email, Subject, Message).', 'error')
        return render_template('public/contact.html', form_data=request.form)

    db = get_db()
    db.execute(
        """INSERT INTO contact_inquiries (name, email, subject, message, organization, status)
           VALUES (?, ?, ?, ?, ?, 'new')""",
        (name, email, subject, message, organization),
    )
    db.commit()

    log_audit('SUBMIT_CONTACT_INQUIRY', 'contact_inquiries', None, f"Inquiry from {name} ({email}): {subject}")

    flash('Thank you for reaching out! Your inquiry has been received and our team will respond shortly.', 'success')
    return redirect(url_for('public.contact'))
