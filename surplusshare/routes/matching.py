"""
routes/matching.py — Automatic Food Matching Blueprint (SurplusShare)

Integrates:
- Merge Sort (expiry prioritization)
- FIFO Request Queue (fair distribution)
- Minimum shelf-life & category checks
- Database transactions to guarantee atomic allocations
- Protected by Role-Based Access Control (@admin_required)
"""

from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session

from database.db import get_db
from services.listing_service import get_all_listings
from services.request_service import get_all_requests
from services.allocation_service import get_all_allocations
from services.auth_service import login_required, admin_required, get_current_user, is_api_request
from services.audit_service import log_audit
from algorithms.matching_engine import MatchingEngine

matching = Blueprint('matching', __name__)

# Cache latest run result for educational review
_last_matching_run = None


@matching.route('/matching')
@admin_required
def matching_page():
    """Render the matching page showing current listings, requests, allocations,
    and results from the latest matching engine run."""
    current_user = get_current_user()
    available_listings = get_all_listings(status_filter='available')
    pending_requests = get_all_requests(status_filter='pending')
    allocations = get_all_allocations()

    return render_template(
        'matching.html',
        available_listings=available_listings,
        pending_requests=pending_requests,
        allocations=allocations,
        last_run=_last_matching_run,
        current_user=current_user,
    )


@matching.route('/matching/run', methods=['POST'])
@admin_required
def run_matching():
    """
    Execute the automated food matching engine.
    Strictly protected: only authenticated administrators can trigger system-wide reallocations.
    """
    global _last_matching_run

    db = get_db()

    # Fetch available and partially allocated listings
    raw_listings = db.execute(
        """SELECT * FROM food_listings
           WHERE status IN ('available', 'partially_allocated')
           ORDER BY expiry_at ASC"""
    ).fetchall()
    listings_data = [dict(r) for r in raw_listings]

    # Fetch pending and partially fulfilled requests
    raw_requests = db.execute(
        """SELECT * FROM recipient_requests
           WHERE status IN ('pending', 'partially_fulfilled')
           ORDER BY requested_at ASC"""
    ).fetchall()
    requests_data = [dict(r) for r in raw_requests]

    if not listings_data:
        if is_api_request():
            return jsonify({'status': 'warning', 'message': 'No available food listings found to match.', 'allocations_count': 0}), 200
        flash('No available food listings found to match.', 'warning')
        return redirect(url_for('matching.matching_page'))

    if not requests_data:
        if is_api_request():
            return jsonify({'status': 'warning', 'message': 'No pending recipient requests found to allocate.', 'allocations_count': 0}), 200
        flash('No pending recipient requests found to allocate.', 'warning')
        return redirect(url_for('matching.matching_page'))

    # Instantiate engine and run
    engine = MatchingEngine()
    result = engine.run_matching(listings_data, requests_data)
    _last_matching_run = result

    allocations = result.get('allocations', [])
    if not allocations:
        if is_api_request():
            return jsonify({'status': 'info', 'message': 'No compatible listings and requests matched shelf-life or category criteria.', 'allocations_count': 0, 'stats': result.get('stats', {})}), 200
        flash('Matching completed: No compatible listings and requests matched shelf-life or category criteria.', 'info')
        return redirect(url_for('matching.matching_page'))

    # Persist allocations atomically
    try:
        for alloc in allocations:
            listing_pk = alloc['listing_db_id']
            request_pk = alloc['request_db_id']
            alloc_qty = alloc['allocated_quantity']

            # Insert allocation record
            db.execute(
                """INSERT INTO allocations
                   (allocation_id, listing_id, request_id, allocated_quantity, allocated_at, status)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    alloc['allocation_id'],
                    listing_pk,
                    request_pk,
                    alloc_qty,
                    alloc['allocated_at'],
                    'pending',
                ),
            )

            # Update food listing
            db.execute(
                """UPDATE food_listings
                   SET allocated_quantity = allocated_quantity + ?,
                       status = CASE
                           WHEN quantity - (allocated_quantity + ?) <= 0.0001 THEN 'fully_allocated'
                           ELSE 'partially_allocated'
                       END
                   WHERE id = ?""",
                (alloc_qty, alloc_qty, listing_pk),
            )

            # Update recipient request
            db.execute(
                """UPDATE recipient_requests
                   SET fulfilled_quantity = fulfilled_quantity + ?,
                       status = CASE
                           WHEN requested_quantity - (fulfilled_quantity + ?) <= 0.0001 THEN 'fulfilled'
                           ELSE 'partially_fulfilled'
                       END
                   WHERE id = ?""",
                (alloc_qty, alloc_qty, request_pk),
            )

        db.commit()
        stats = result['stats']
        log_audit(
            'EXECUTE_MATCHING',
            'matching_engine',
            f"{len(allocations)}-allocations",
            f"Allocated {stats['total_quantity_allocated']} units in {stats['total_time_ms']} ms",
        )
        if is_api_request():
            return jsonify({
                'status': 'success',
                'message': f"Matched and created {len(allocations)} allocation(s)",
                'allocations_count': len(allocations),
                'total_rescued_units': stats['total_quantity_allocated'],
                'time_ms': stats['total_time_ms'],
                'stats': stats,
            }), 200

        flash(
            f"Successfully matched and created {len(allocations)} allocation(s) "
            f"({stats['total_quantity_allocated']} total units rescued) in "
            f"{stats['total_time_ms']} ms!",
            'success',
        )
    except Exception as e:
        db.rollback()
        if is_api_request():
            return jsonify({'status': 'error', 'message': str(e)}), 500
        flash(f"Error persisting allocations: {str(e)}", 'error')

    return redirect(url_for('matching.matching_page'))


@matching.route('/api/matching/last-run')
@login_required
def api_last_run():
    """Return latest matching run metadata and metrics as JSON."""
    if _last_matching_run is None:
        return jsonify({'status': 'none', 'message': 'No matching run recorded yet.'})
    return jsonify(_last_matching_run)
