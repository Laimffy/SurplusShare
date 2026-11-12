"""Listings routes blueprint for SurplusShare."""

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify,
)

from services.listing_service import (
    get_all_listings,
    get_listing_by_id,
    create_listing,
    update_listing,
    delete_listing,
    ALLOWED_CATEGORIES,
)
from services.auth_service import (
    login_required,
    roles_required,
    get_current_user,
    can_manage_listing,
    is_api_request,
)
from services.audit_service import log_audit

listings = Blueprint('listings', __name__)


@listings.route('/listings')
@login_required
def list_listings():
    """Render listings page with optional status and category filters.

    Query params:
        status: Filter by listing status.
        category: Filter by food category.
    """
    current_user = get_current_user()
    status_filter = request.args.get('status')
    category_filter = request.args.get('category')
    
    all_listings = get_all_listings(
        status_filter=status_filter,
        category_filter=category_filter,
    )
    return render_template(
        'listings.html',
        listings=all_listings,
        status_filter=status_filter,
        category_filter=category_filter,
        categories=ALLOWED_CATEGORIES,
        current_user=current_user,
    )


@listings.route('/listings/<listing_id>')
@login_required
def listing_detail(listing_id):
    """Render detail page for a single listing."""
    listing = get_listing_by_id(listing_id)
    if listing is None:
        flash('Listing not found.', 'error')
        return redirect(url_for('listings.list_listings'))
    
    current_user = get_current_user()
    user_can_edit = can_manage_listing(listing, current_user)
    
    from services.allocation_service import get_allocations_for_listing
    allocations = get_allocations_for_listing(listing['id'])
    return render_template(
        'listing_detail.html',
        listing=listing,
        allocations=allocations,
        user_can_edit=user_can_edit,
    )


@listings.route('/listings/new')
@roles_required('donor', 'admin')
def new_listing():
    """Render the listing creation form."""
    current_user = get_current_user()
    default_donor = current_user.get('organization') or current_user.get('display_name')
    return render_template(
        'listing_form.html',
        listing={'donor_name': default_donor},
        categories=ALLOWED_CATEGORIES,
    )


@listings.route('/listings', methods=['POST'])
@roles_required('donor', 'admin')
def create_listing_route():
    """Handle listing creation form submission."""
    current_user = get_current_user()
    donor_name = request.form.get('donor_name', '').strip()
    if current_user['role'] == 'donor' and not donor_name:
        donor_name = current_user.get('organization') or current_user.get('display_name')

    data = {
        'food_name': request.form.get('food_name', ''),
        'category': request.form.get('category', ''),
        'quantity': request.form.get('quantity', ''),
        'unit': request.form.get('unit', ''),
        'donor_name': donor_name,
        'donor_id': current_user['id'] if current_user['role'] == 'donor' else None,
        'expiry_at': request.form.get('expiry_at', ''),
        'pickup_location': request.form.get('pickup_location', ''),
        'storage_requirements': request.form.get('storage_requirements', ''),
        'food_condition': request.form.get('food_condition', 'Good'),
    }

    try:
        created = create_listing(data)
        log_audit(
            'CREATE_LISTING',
            'food_listings',
            created['listing_id'],
            f"Created listing '{created['food_name']}' ({created['quantity']} {created['unit']})",
        )
        flash(f"Listing '{created['listing_id']}' created successfully.", 'success')
        return redirect(url_for('listings.list_listings'))
    except ValueError as e:
        flash(str(e), 'error')
        return render_template(
            'listing_form.html',
            listing=data,
            categories=ALLOWED_CATEGORIES,
        ), 400


@listings.route('/listings/<listing_id>/edit')
@roles_required('donor', 'admin')
def edit_listing(listing_id):
    """Render the listing edit form with pre-populated data."""
    listing = get_listing_by_id(listing_id)
    if listing is None:
        flash('Listing not found.', 'error')
        return redirect(url_for('listings.list_listings'))

    current_user = get_current_user()
    if not can_manage_listing(listing, current_user):
        if is_api_request():
            return jsonify({'error': 'Forbidden', 'message': 'You do not own this listing.'}), 403
        return render_template('errors/403.html', user_role=current_user['role'], required_roles=['Owner or Admin']), 403

    return render_template(
        'listing_form.html',
        listing=listing,
        categories=ALLOWED_CATEGORIES,
    )


@listings.route('/listings/<listing_id>/edit', methods=['POST'])
@roles_required('donor', 'admin')
def update_listing_route(listing_id):
    """Handle listing edit form submission."""
    listing = get_listing_by_id(listing_id)
    if listing is None:
        flash('Listing not found.', 'error')
        return redirect(url_for('listings.list_listings'))

    current_user = get_current_user()
    if not can_manage_listing(listing, current_user):
        if is_api_request():
            return jsonify({'error': 'Forbidden', 'message': 'You do not own this listing.'}), 403
        return render_template('errors/403.html', user_role=current_user['role'], required_roles=['Owner or Admin']), 403

    data = {
        'food_name': request.form.get('food_name', ''),
        'category': request.form.get('category', ''),
        'quantity': request.form.get('quantity', ''),
        'unit': request.form.get('unit', ''),
        'donor_name': request.form.get('donor_name', listing['donor_name']),
        'expiry_at': request.form.get('expiry_at', ''),
        'pickup_location': request.form.get('pickup_location', ''),
        'storage_requirements': request.form.get('storage_requirements', ''),
        'food_condition': request.form.get('food_condition', 'Good'),
    }

    try:
        updated = update_listing(listing_id, data)
        log_audit(
            'UPDATE_LISTING',
            'food_listings',
            listing_id,
            f"Updated listing '{listing_id}'",
        )
        flash(f"Listing '{listing_id}' updated successfully.", 'success')
        return redirect(url_for('listings.listing_detail', listing_id=listing_id))
    except ValueError as e:
        flash(str(e), 'error')
        data['listing_id'] = listing_id
        return render_template(
            'listing_form.html',
            listing=data,
            categories=ALLOWED_CATEGORIES,
        ), 400


@listings.route('/listings/<listing_id>/delete', methods=['POST'])
@roles_required('donor', 'admin')
def delete_listing_route(listing_id):
    """Handle listing deletion with tenant ownership check."""
    listing = get_listing_by_id(listing_id)
    if listing is None:
        flash(f"Listing '{listing_id}' not found.", 'error')
        return redirect(url_for('listings.list_listings'))

    current_user = get_current_user()
    if not can_manage_listing(listing, current_user):
        if is_api_request():
            return jsonify({'error': 'Forbidden', 'message': 'You do not own this listing.'}), 403
        return render_template('errors/403.html', user_role=current_user['role'], required_roles=['Owner or Admin']), 403

    if delete_listing(listing_id):
        log_audit('DELETE_LISTING', 'food_listings', listing_id, f"Deleted listing '{listing_id}'")
        flash(f"Listing '{listing_id}' deleted successfully.", 'success')
    else:
        flash(f"Listing '{listing_id}' not found.", 'error')
    return redirect(url_for('listings.list_listings'))


@listings.route('/listings/<listing_id>/handover', methods=['POST'])
@roles_required('donor', 'admin')
def confirm_handover(listing_id):
    """Donor confirms food handover to logistics or recipient."""
    listing = get_listing_by_id(listing_id)
    if not listing:
        flash(f"Listing '{listing_id}' not found.", 'error')
        return redirect(url_for('listings.list_listings'))

    current_user = get_current_user()
    if not can_manage_listing(listing, current_user):
        if is_api_request():
            return jsonify({'error': 'Forbidden', 'message': 'You do not own this listing.'}), 403
        return render_template('errors/403.html', user_role=current_user['role'], required_roles=['Owner or Admin']), 403

    from database.db import get_db
    db = get_db()
    # Mark associated pickup stops as completed
    db.execute(
        """UPDATE pickup_stops SET status = 'completed'
           WHERE listing_id = ? AND status IN ('pending', 'in_progress')""",
        (listing['id'],),
    )
    # Mark associated allocations as picked_up
    db.execute(
        """UPDATE allocations SET status = 'picked_up'
           WHERE listing_id = ? AND status = 'pending'""",
        (listing['id'],),
    )
    db.commit()

    log_audit('CONFIRM_HANDOVER', 'food_listings', listing_id, f"Donor confirmed handover for '{listing_id}'")
    flash(f"Food handover confirmed for '{listing['food_name']}'. Handed over to volunteer driver.", 'success')
    return redirect(url_for('listings.listing_detail', listing_id=listing_id))


@listings.route('/api/listings')
@login_required
def api_listings():
    """JSON API endpoint returning listings."""
    status_filter = request.args.get('status')
    category_filter = request.args.get('category')
    all_listings = get_all_listings(
        status_filter=status_filter,
        category_filter=category_filter,
    )
    return jsonify(all_listings)
