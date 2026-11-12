"""
routes/admin.py — Comprehensive Administrative Management Blueprint for SurplusShare

Strictly protected by @admin_required. Provides modules for:
- Dashboard Analytics
- User Management
- Donation Management
- Recipient Request Management
- Food Matching Engine
- Pickup Scheduling (Doubly Linked List)
- Partner Management
- News & Content Management
- FAQ Management
- Website Inquiries Management
- Reports & Benchmarks
- Security Audit Logs
"""

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database.db import get_db
from services.auth_service import admin_required, get_current_user
from services.audit_service import log_audit, get_audit_logs, get_audit_log_stats

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ── 1. Admin Dashboard Analytics ──────────────────────────────────────────
@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Administrative analytics and operations summary."""
    db = get_db()
    current_user = get_current_user()

    total_users = db.execute("SELECT COUNT(*) AS c FROM users").fetchone()['c']
    total_listings = db.execute("SELECT COUNT(*) AS c FROM food_listings").fetchone()['c']
    total_requests = db.execute("SELECT COUNT(*) AS c FROM recipient_requests").fetchone()['c']
    total_allocations = db.execute("SELECT COUNT(*) AS c FROM allocations").fetchone()['c']
    total_partners = db.execute("SELECT COUNT(*) AS c FROM partners").fetchone()['c']
    new_inquiries = db.execute("SELECT COUNT(*) AS c FROM contact_inquiries WHERE status = 'new'").fetchone()['c']

    # Rescued kg
    res_alloc = db.execute("SELECT COALESCE(SUM(allocated_quantity), 0) AS total_kg FROM allocations WHERE status != 'cancelled'").fetchone()
    total_rescued_kg = float(res_alloc['total_kg']) if res_alloc else 0.0

    # Urgent expiries (< 6h)
    expiring_soon = db.execute(
        """SELECT listing_id, food_name, donor_name, quantity, unit, expiry_at
           FROM food_listings
           WHERE status = 'available' AND expiry_at > datetime('now')
           ORDER BY expiry_at ASC LIMIT 5"""
    ).fetchall()

    # Recent Audit Events
    audit_stats = get_audit_log_stats()

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_listings=total_listings,
        total_requests=total_requests,
        total_allocations=total_allocations,
        total_partners=total_partners,
        new_inquiries=new_inquiries,
        total_rescued_kg=round(total_rescued_kg, 1),
        expiring_soon=[dict(r) for r in expiring_soon],
        recent_audits=audit_stats['recent_events'],
        top_actions=audit_stats['top_actions'],
    )


# ── 2. User Management ────────────────────────────────────────────────────
@admin_bp.route('/users')
@admin_required
def users():
    """List all registered system users with role filters."""
    db = get_db()
    role_filter = request.args.get('role', '').strip()

    query = "SELECT id, username, display_name, role, organization, email, created_at FROM users WHERE 1=1"
    params = []
    if role_filter:
        query += " AND role = ?"
        params.append(role_filter)
    query += " ORDER BY id DESC"

    all_users = [dict(r) for r in db.execute(query, params).fetchall()]
    return render_template('admin/users.html', users=all_users, role_filter=role_filter)


@admin_bp.route('/users/new', methods=['POST'])
@admin_required
def create_user():
    """Create a new user with an assigned role."""
    from werkzeug.security import generate_password_hash
    username = request.form.get('username', '').strip()
    display_name = request.form.get('display_name', '').strip()
    email = request.form.get('email', '').strip()
    role = request.form.get('role', 'donor').strip().lower()
    organization = request.form.get('organization', '').strip()
    password = request.form.get('password', 'password123').strip()

    if not username or not display_name or not email:
        flash('Username, Display Name, and Email are required.', 'error')
        return redirect(url_for('admin.users'))

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email)).fetchone()
    if existing:
        flash('A user with that username or email already exists.', 'error')
        return redirect(url_for('admin.users'))

    pwd_hash = generate_password_hash(password)
    db.execute(
        """INSERT INTO users (username, display_name, role, organization, email, password_hash)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (username, display_name, role, organization or display_name, email, pwd_hash),
    )
    db.commit()

    log_audit('CREATE_USER', 'users', username, f"Created {role} user '{username}' ({display_name})")
    flash(f"User '{username}' created successfully.", 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/update-role', methods=['POST'])
@admin_required
def update_user_role(user_id):
    """Change a user's role (admin, donor, recipient, volunteer)."""
    new_role = request.form.get('role', '').strip().lower()
    if new_role not in ('admin', 'donor', 'recipient', 'volunteer'):
        flash('Invalid role specified.', 'error')
        return redirect(url_for('admin.users'))

    db = get_db()
    db.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    db.commit()

    log_audit('UPDATE_USER_ROLE', 'users', str(user_id), f"Changed role to '{new_role}'")
    flash(f"User role updated to '{new_role}'.", 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user account."""
    current_user = get_current_user()
    if current_user and current_user['id'] == user_id:
        flash('You cannot delete your own active administrator account.', 'error')
        return redirect(url_for('admin.users'))

    db = get_db()
    user = db.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        uname = user['username']
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
        log_audit('DELETE_USER', 'users', str(user_id), f"Deleted user '{uname}'")
        flash(f"User '{uname}' removed.", 'success')
    return redirect(url_for('admin.users'))


# ── 3. Partner Management ─────────────────────────────────────────────────
@admin_bp.route('/partners')
@admin_required
def partners():
    """List and manage confirmed and prospective Philippine partners."""
    db = get_db()
    rows = db.execute("SELECT * FROM partners ORDER BY status ASC, name ASC").fetchall()
    all_partners = [dict(r) for r in rows]
    categories = ['Bakery', 'Supermarket & Grocery', 'Catering', 'Restaurant', 'Fast-Food', 'Local Food Establishment', 'NGO / Community']
    return render_template('admin/partners.html', partners=all_partners, categories=categories)


@admin_bp.route('/partners/new', methods=['POST'])
@admin_required
def create_partner():
    """Add a new partner profile."""
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    location = request.form.get('location', '').strip()
    description = request.form.get('description', '').strip()
    status = request.form.get('status', 'confirmed').strip().lower()
    website_url = request.form.get('website_url', '').strip()
    contact_email = request.form.get('contact_email', '').strip()
    contact_phone = request.form.get('contact_phone', '').strip()

    if not name or not category or not location or not description:
        flash('Please fill in all required partner fields.', 'error')
        return redirect(url_for('admin.partners'))

    db = get_db()
    db.execute(
        """INSERT INTO partners (name, category, location, description, status, website_url, contact_email, contact_phone)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, category, location, description, status, website_url, contact_email, contact_phone),
    )
    db.commit()

    log_audit('CREATE_PARTNER', 'partners', name, f"Created {status} partner '{name}' ({category})")
    flash(f"Partner '{name}' added successfully.", 'success')
    return redirect(url_for('admin.partners'))


@admin_bp.route('/partners/<int:partner_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_partner_status(partner_id):
    """Toggle partner status between confirmed and prospective."""
    db = get_db()
    row = db.execute("SELECT name, status FROM partners WHERE id = ?", (partner_id,)).fetchone()
    if row:
        new_status = 'prospective' if row['status'] == 'confirmed' else 'confirmed'
        db.execute("UPDATE partners SET status = ? WHERE id = ?", (new_status, partner_id))
        db.commit()
        log_audit('UPDATE_PARTNER_STATUS', 'partners', str(partner_id), f"Changed status of '{row['name']}' to '{new_status}'")
        flash(f"Partner '{row['name']}' is now {new_status}.", 'success')
    return redirect(url_for('admin.partners'))


@admin_bp.route('/partners/<int:partner_id>/delete', methods=['POST'])
@admin_required
def delete_partner(partner_id):
    """Remove a partner profile."""
    db = get_db()
    row = db.execute("SELECT name FROM partners WHERE id = ?", (partner_id,)).fetchone()
    if row:
        name = row['name']
        db.execute("DELETE FROM partners WHERE id = ?", (partner_id,))
        db.commit()
        log_audit('DELETE_PARTNER', 'partners', str(partner_id), f"Deleted partner '{name}'")
        flash(f"Partner '{name}' removed.", 'success')
    return redirect(url_for('admin.partners'))


# ── 4. News and Announcements Management ──────────────────────────────────
@admin_bp.route('/news')
@admin_required
def news():
    """List all news articles with publish/unpublish status."""
    db = get_db()
    rows = db.execute("SELECT * FROM news_articles ORDER BY created_at DESC").fetchall()
    categories = ['Activity', 'Announcement', 'Awareness', 'Story', 'Update']
    return render_template('admin/news.html', articles=[dict(r) for r in rows], categories=categories)


@admin_bp.route('/news/new', methods=['POST'])
@admin_required
def create_news():
    """Create and publish a new news article."""
    title = request.form.get('title', '').strip()
    category = request.form.get('category', 'Update').strip()
    excerpt = request.form.get('excerpt', '').strip()
    content = request.form.get('content', '').strip()
    author_name = request.form.get('author_name', 'SurplusShare Team').strip()
    is_published = 1 if request.form.get('is_published') == '1' else 0

    if not title or not content:
        flash('Article title and content are required.', 'error')
        return redirect(url_for('admin.news'))

    import re
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    if not slug:
        slug = f"article-{int(datetime.now().timestamp())}"

    db = get_db()
    # Check uniqueness
    existing = db.execute("SELECT id FROM news_articles WHERE slug = ?", (slug,)).fetchone()
    if existing:
        slug = f"{slug}-{int(datetime.now().timestamp())}"

    db.execute(
        """INSERT INTO news_articles (title, slug, category, excerpt, content, author_name, is_published, published_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (title, slug, category, excerpt, content, author_name, is_published),
    )
    db.commit()

    log_audit('CREATE_NEWS', 'news_articles', slug, f"Published article '{title}'")
    flash(f"Article '{title}' created successfully.", 'success')
    return redirect(url_for('admin.news'))


@admin_bp.route('/news/<int:article_id>/toggle-publish', methods=['POST'])
@admin_required
def toggle_publish_news(article_id):
    """Toggle an article's published state."""
    db = get_db()
    row = db.execute("SELECT title, is_published FROM news_articles WHERE id = ?", (article_id,)).fetchone()
    if row:
        new_val = 0 if row['is_published'] == 1 else 1
        db.execute("UPDATE news_articles SET is_published = ? WHERE id = ?", (new_val, article_id))
        db.commit()
        status_txt = "published" if new_val == 1 else "unpublished"
        log_audit('TOGGLE_NEWS_PUBLISH', 'news_articles', str(article_id), f"Marked '{row['title']}' as {status_txt}")
        flash(f"Article '{row['title']}' is now {status_txt}.", 'success')
    return redirect(url_for('admin.news'))


@admin_bp.route('/news/<int:article_id>/delete', methods=['POST'])
@admin_required
def delete_news(article_id):
    """Delete a news article."""
    db = get_db()
    row = db.execute("SELECT title FROM news_articles WHERE id = ?", (article_id,)).fetchone()
    if row:
        title = row['title']
        db.execute("DELETE FROM news_articles WHERE id = ?", (article_id,))
        db.commit()
        log_audit('DELETE_NEWS', 'news_articles', str(article_id), f"Deleted article '{title}'")
        flash(f"Article '{title}' deleted.", 'success')
    return redirect(url_for('admin.news'))


# ── 5. FAQ Management ─────────────────────────────────────────────────────
@admin_bp.route('/faqs')
@admin_required
def faqs():
    """List and manage FAQs."""
    db = get_db()
    rows = db.execute("SELECT * FROM faqs ORDER BY category ASC, order_index ASC").fetchall()
    categories = ['Donating Food', 'Receiving Food', 'Matching & Algorithms', 'Volunteering & Pickups', 'Partnerships', 'General']
    return render_template('admin/faqs.html', faqs=[dict(r) for r in rows], categories=categories)


@admin_bp.route('/faqs/new', methods=['POST'])
@admin_required
def create_faq():
    """Add a new FAQ question and answer."""
    question = request.form.get('question', '').strip()
    answer = request.form.get('answer', '').strip()
    category = request.form.get('category', 'General').strip()
    order_index = int(request.form.get('order_index', '0') or '0')

    if not question or not answer:
        flash('Question and Answer are required.', 'error')
        return redirect(url_for('admin.faqs'))

    db = get_db()
    db.execute(
        """INSERT INTO faqs (question, answer, category, order_index, is_published)
           VALUES (?, ?, ?, ?, 1)""",
        (question, answer, category, order_index),
    )
    db.commit()

    log_audit('CREATE_FAQ', 'faqs', None, f"Added FAQ: '{question[:50]}...'")
    flash('New FAQ added.', 'success')
    return redirect(url_for('admin.faqs'))


@admin_bp.route('/faqs/<int:faq_id>/delete', methods=['POST'])
@admin_required
def delete_faq(faq_id):
    """Delete an FAQ."""
    db = get_db()
    db.execute("DELETE FROM faqs WHERE id = ?", (faq_id,))
    db.commit()
    log_audit('DELETE_FAQ', 'faqs', str(faq_id), f"Deleted FAQ ID {faq_id}")
    flash('FAQ removed.', 'success')
    return redirect(url_for('admin.faqs'))


# ── 6. Contact Inquiries Management ───────────────────────────────────────
@admin_bp.route('/inquiries')
@admin_required
def inquiries():
    """View messages submitted via public Contact Us form."""
    db = get_db()
    rows = db.execute("SELECT * FROM contact_inquiries ORDER BY created_at DESC").fetchall()
    return render_template('admin/inquiries.html', inquiries=[dict(r) for r in rows])


@admin_bp.route('/inquiries/<int:inquiry_id>/status', methods=['POST'])
@admin_required
def update_inquiry_status(inquiry_id):
    """Update status of a contact message (read, responded, archived)."""
    status = request.form.get('status', 'read').strip().lower()
    db = get_db()
    db.execute("UPDATE contact_inquiries SET status = ? WHERE id = ?", (status, inquiry_id))
    db.commit()
    flash(f"Inquiry marked as '{status}'.", 'success')
    return redirect(url_for('admin.inquiries'))


# ── 7. Security Audit Logs ────────────────────────────────────────────────
@admin_bp.route('/audit-logs')
@admin_required
def audit_logs():
    """View full security audit logs with filtering and search."""
    action_filter = request.args.get('action', '').strip()
    role_filter = request.args.get('role', '').strip()
    search_term = request.args.get('q', '').strip()

    logs = get_audit_logs(
        limit=150,
        action_filter=action_filter or None,
        role_filter=role_filter or None,
        search_term=search_term or None,
    )
    stats = get_audit_log_stats()

    return render_template(
        'admin/audit_logs.html',
        logs=logs,
        stats=stats,
        action_filter=action_filter,
        role_filter=role_filter,
        search_term=search_term,
    )
