"""Main routes blueprint for SurplusShare role-based dashboards."""

from flask import Blueprint, redirect, url_for, render_template
from services.listing_service import (
    get_dashboard_stats,
    get_all_listings,
    get_expiring_listings,
    get_expired_listings,
)
from services.auth_service import login_required, roles_required, get_current_user

main = Blueprint('main', __name__)


def _build_role_dashboard(target_role=None):
    """Build and render the dashboard tailored to the requested role or current authenticated role.

    Admin: Full system dashboard, all metrics, and all pickups.
    Donor: Scoped to their surplus donations, handover pickups, and expiry alerts.
    Recipient: Scoped to their requests, received kilograms, and incoming allocations.
    Volunteer: Scoped to their assigned routes, pickup checklist, and pending stops.
    """
    from services.schedule_service import get_all_schedules
    from database.db import get_db

    current_user = get_current_user()
    db = get_db()
    stats = get_dashboard_stats()
    role = target_role or current_user.get('role', 'admin')

    user_org = (current_user.get('organization') or '').strip()
    user_disp = (current_user.get('display_name') or '').strip()
    user_id = current_user.get('id')

    if role == 'donor':
        dashboard_title = 'Donation Dashboard'
        dashboard_badge = 'Donor Portal • Donation Management'
        dashboard_hero_title = 'Donation Dashboard'
        dashboard_subtitle = 'Share More. Waste Less. Track your food surplus donations, review real-time expiry clocks, and coordinate driver handovers.'

        # Scoped metrics for Donor
        donor_listings = db.execute(
            """SELECT * FROM food_listings 
               WHERE donor_id = ? OR donor_name = ? OR donor_name = ?
               ORDER BY created_at DESC""",
            (user_id, user_org, user_disp),
        ).fetchall()
        recent_listings = [dict(r) for r in donor_listings]

        expiring_rows = db.execute(
            """SELECT * FROM food_listings 
               WHERE (donor_id = ? OR donor_name = ? OR donor_name = ?)
                 AND status = 'available' 
                 AND expiry_at BETWEEN datetime('now') AND datetime('now', '+24 hours')
               ORDER BY expiry_at ASC""",
            (user_id, user_org, user_disp),
        ).fetchall()
        expiring_listings = [dict(r) for r in expiring_rows]

        expired_rows = db.execute(
            """SELECT * FROM food_listings 
               WHERE (donor_id = ? OR donor_name = ? OR donor_name = ?)
                 AND status = 'available' AND expiry_at < datetime('now')
               ORDER BY expiry_at DESC""",
            (user_id, user_org, user_disp),
        ).fetchall()
        expired = [dict(r) for r in expired_rows]

        # Rescued/allocated from this donor
        donor_res = db.execute(
            """SELECT COALESCE(SUM(fl.allocated_quantity), 0) AS rescued_kg
               FROM food_listings fl
               WHERE (fl.donor_id = ? OR fl.donor_name = ? OR fl.donor_name = ?)""",
            (user_id, user_org, user_disp),
        ).fetchone()

        stats['available_listings'] = sum(1 for l in recent_listings if l.get('status') == 'available')
        stats['total_listings'] = len(recent_listings)
        stats['rescued_kg'] = round(float(donor_res['rescued_kg']), 1) if donor_res else 0.0
        stats['expiring_soon'] = len(expiring_listings)

        # Pickups at this donor's site
        upcoming_stops_rows = db.execute(
            """SELECT pst.*, ps.schedule_id, ps.volunteer_name, ps.schedule_date
               FROM pickup_stops pst
               JOIN pickup_schedules ps ON pst.schedule_id = ps.id
               WHERE pst.status IN ('pending', 'in_progress')
                 AND (pst.donor_name = ? OR pst.donor_name = ?)
               ORDER BY ps.schedule_date ASC, pst.scheduled_time ASC
               LIMIT 5""",
            (user_org, user_disp),
        ).fetchall()
        upcoming_pickups = [dict(r) for r in upcoming_stops_rows]
        stats['scheduled_pickups'] = len(upcoming_pickups)

    elif role == 'recipient':
        dashboard_title = 'Recipient Dashboard'
        dashboard_badge = 'Recipient Portal • Community Redistribution'
        dashboard_hero_title = 'Recipient Dashboard'
        dashboard_subtitle = 'Nourish Communities. Submit food requests to the FIFO queue, monitor algorithmic allocations, and confirm delivery receipts.'

        # Scoped metrics for Recipient
        recent_listings = get_all_listings(status_filter='available')[:6]
        expiring_listings = []
        expired = []

        my_reqs = db.execute(
            """SELECT * FROM recipient_requests
               WHERE recipient_id = ? OR organization_name = ? OR organization_name = ?
               ORDER BY requested_at DESC""",
            (user_id, user_org, user_disp),
        ).fetchall()
        req_list = [dict(r) for r in my_reqs]

        rec_res = db.execute(
            """SELECT COALESCE(SUM(fulfilled_quantity), 0) as fulfilled_kg
               FROM recipient_requests
               WHERE recipient_id = ? OR organization_name = ? OR organization_name = ?""",
            (user_id, user_org, user_disp),
        ).fetchone()

        stats['pending_requests'] = sum(1 for r in req_list if r.get('status') == 'pending')
        stats['total_requests'] = len(req_list)
        stats['rescued_kg'] = round(float(rec_res['fulfilled_kg']), 1) if rec_res else 0.0

        # Deliveries for this recipient's requests
        upcoming_stops_rows = db.execute(
            """SELECT pst.*, ps.schedule_id, ps.volunteer_name, ps.schedule_date
               FROM pickup_stops pst
               JOIN pickup_schedules ps ON pst.schedule_id = ps.id
               JOIN allocations al ON al.listing_id = pst.listing_id
               JOIN recipient_requests rr ON al.request_id = rr.id
               WHERE (rr.recipient_id = ? OR rr.organization_name = ? OR rr.organization_name = ?)
                 AND pst.status IN ('pending', 'in_progress')
               ORDER BY ps.schedule_date ASC, pst.scheduled_time ASC
               LIMIT 5""",
            (user_id, user_org, user_disp),
        ).fetchall()
        upcoming_pickups = [dict(r) for r in upcoming_stops_rows]
        stats['scheduled_pickups'] = len(upcoming_pickups)

    elif role == 'volunteer':
        dashboard_title = 'Pickup Dashboard'
        dashboard_badge = 'Volunteer Portal • Logistics & Routing'
        dashboard_hero_title = 'Pickup Dashboard'
        dashboard_subtitle = 'Coordinate Pickups. Inspect your assigned route stops, reorder waypoints via Doubly Linked List, and update delivery status.'

        # Scoped metrics for Volunteer
        recent_listings = []
        expiring_listings = []
        expired = []

        # Stops assigned specifically to this volunteer
        upcoming_stops_rows = db.execute(
            """SELECT pst.*, ps.schedule_id, ps.volunteer_name, ps.schedule_date
               FROM pickup_stops pst
               JOIN pickup_schedules ps ON pst.schedule_id = ps.id
               WHERE (LOWER(ps.volunteer_name) = LOWER(?) OR LOWER(ps.volunteer_name) = LOWER(?))
                 AND pst.status IN ('pending', 'in_progress')
               ORDER BY ps.schedule_date ASC, pst.scheduled_time ASC""",
            (user_disp, user_org or user_disp),
        ).fetchall()
        upcoming_pickups = [dict(r) for r in upcoming_stops_rows]

        completed_stops_count = db.execute(
            """SELECT COUNT(*) as c
               FROM pickup_stops pst
               JOIN pickup_schedules ps ON pst.schedule_id = ps.id
               WHERE (LOWER(ps.volunteer_name) = LOWER(?) OR LOWER(ps.volunteer_name) = LOWER(?))
                 AND pst.status = 'completed'""",
            (user_disp, user_org or user_disp),
        ).fetchone()['c']

        stats['scheduled_pickups'] = len(upcoming_pickups)
        stats['pending_stops'] = len(upcoming_pickups)
        stats['completed_stops'] = completed_stops_count

    else:
        # Full admin dashboard
        dashboard_title = 'Admin Dashboard'
        dashboard_badge = 'Admin Portal • Full System Governance'
        dashboard_hero_title = 'Administrator System Dashboard'
        dashboard_subtitle = 'Oversee all food donations, recipient requests, matching operations, algorithm benchmarks, and system configurations.'

        recent_listings = get_all_listings()[:8]
        expiring_listings = get_expiring_listings(hours=24)[:6]
        expired = get_expired_listings()

        schedules = get_all_schedules()
        active_schedules_count = sum(1 for s in schedules if s.get('status') in ('planned', 'in_progress'))
        stats['scheduled_pickups'] = active_schedules_count

        upcoming_stops_rows = db.execute(
            """SELECT pst.*, ps.schedule_id, ps.volunteer_name, ps.schedule_date
               FROM pickup_stops pst
               JOIN pickup_schedules ps ON pst.schedule_id = ps.id
               WHERE pst.status IN ('pending', 'in_progress')
               ORDER BY ps.schedule_date ASC, pst.scheduled_time ASC
               LIMIT 5"""
        ).fetchall()
        upcoming_pickups = [dict(r) for r in upcoming_stops_rows]

    # Redistribution Chart Data
    cat_rescued_rows = db.execute(
        """SELECT fl.category,
                  COALESCE(SUM(fl.quantity - fl.allocated_quantity), 0) AS available_qty,
                  COALESCE(SUM(fl.allocated_quantity), 0) AS rescued_qty
           FROM food_listings fl
           WHERE fl.status != 'cancelled'
           GROUP BY fl.category"""
    ).fetchall()
    redistribution_data = {
        'categories': [r['category'] for r in cat_rescued_rows],
        'available': [round(r['available_qty'], 1) for r in cat_rescued_rows],
        'rescued': [round(r['rescued_qty'], 1) for r in cat_rescued_rows],
    }

    return render_template(
        'dashboard.html',
        stats=stats,
        recent_listings=recent_listings,
        expiring_listings=expiring_listings,
        expired_listings=expired,
        upcoming_pickups=upcoming_pickups,
        redistribution_data=redistribution_data,
        current_user=current_user,
        dashboard_title=dashboard_title,
        dashboard_badge=dashboard_badge,
        dashboard_hero_title=dashboard_hero_title,
        dashboard_subtitle=dashboard_subtitle,
    )


@main.route('/dashboard')
@login_required
def dashboard():
    """Universal dashboard entry point that dynamically renders the user's role-appropriate dashboard."""
    return _build_role_dashboard()


@main.route('/donor/dashboard')
@roles_required('donor')
def donor_dashboard():
    """Dedicated Donation Dashboard for food donors."""
    return _build_role_dashboard(target_role='donor')


@main.route('/recipient/dashboard')
@roles_required('recipient')
def recipient_dashboard():
    """Dedicated Recipient Dashboard for pantries and shelters."""
    return _build_role_dashboard(target_role='recipient')


@main.route('/volunteer/dashboard')
@main.route('/pickup/dashboard')
@roles_required('volunteer')
def volunteer_dashboard():
    """Dedicated Pickup Dashboard for volunteer drivers."""
    return _build_role_dashboard(target_role='volunteer')
