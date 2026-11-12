"""Requests routes blueprint for SurplusShare."""

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify,
)

from services.request_service import (
    get_all_requests,
    get_request_by_id,
    create_request,
    cancel_request,
    ALLOWED_CATEGORIES,
)
from services.auth_service import (
    login_required,
    roles_required,
    get_current_user,
    can_manage_request,
    is_api_request,
)
from services.audit_service import log_audit

requests_bp = Blueprint('requests_bp', __name__)


@requests_bp.route('/requests')
@login_required
def list_requests():
    """Render requests page with optional filters.

    Query params:
        status: Filter by request status.
        category: Filter by food category.
    """
    current_user = get_current_user()
    status_filter = request.args.get('status')
    category_filter = request.args.get('category')
    all_requests = get_all_requests(
        status_filter=status_filter,
        category_filter=category_filter,
    )
    return render_template(
        'requests.html',
        requests=all_requests,
        status_filter=status_filter,
        category_filter=category_filter,
        categories=ALLOWED_CATEGORIES,
        current_user=current_user,
    )


@requests_bp.route('/requests/new')
@roles_required('recipient', 'admin')
def new_request():
    """Render the request creation form."""
    current_user = get_current_user()
    default_org = current_user.get('organization') or current_user.get('display_name')
    return render_template(
        'request_form.html',
        req={'organization_name': default_org},
        categories=ALLOWED_CATEGORIES,
    )


@requests_bp.route('/requests', methods=['POST'])
@roles_required('recipient', 'admin')
def create_request_route():
    """Handle request creation form submission."""
    current_user = get_current_user()
    org_name = request.form.get('organization_name', '').strip()
    if current_user['role'] == 'recipient' and not org_name:
        org_name = current_user.get('organization') or current_user.get('display_name')

    data = {
        'organization_name': org_name,
        'recipient_id': current_user['id'] if current_user['role'] == 'recipient' else None,
        'food_category': request.form.get('food_category', ''),
        'requested_quantity': request.form.get('requested_quantity', ''),
        'quantity_unit': request.form.get('quantity_unit', ''),
        'min_shelf_life_hours': request.form.get('min_shelf_life_hours', '0'),
    }

    try:
        created = create_request(data)
        log_audit(
            'CREATE_REQUEST',
            'recipient_requests',
            created['request_id'],
            f"Created request for {created['requested_quantity']} {created['quantity_unit']} ({created['food_category']})",
        )
        flash(f"Request '{created['request_id']}' added to FIFO queue successfully.", 'success')
        return redirect(url_for('requests_bp.list_requests'))
    except ValueError as e:
        flash(str(e), 'error')
        return render_template(
            'request_form.html',
            req=data,
            categories=ALLOWED_CATEGORIES,
        ), 400


@requests_bp.route('/requests/<request_id>/cancel', methods=['POST'])
@roles_required('recipient', 'admin')
def cancel_request_route(request_id):
    """Handle request cancellation with ownership check."""
    req_item = get_request_by_id(request_id)
    if not req_item:
        flash(f"Request '{request_id}' not found.", 'error')
        return redirect(url_for('requests_bp.list_requests'))

    current_user = get_current_user()
    if not can_manage_request(req_item, current_user):
        if is_api_request():
            return jsonify({'error': 'Forbidden', 'message': 'You do not own this request.'}), 403
        return render_template('errors/403.html', user_role=current_user['role'], required_roles=['Owner or Admin']), 403

    if cancel_request(request_id):
        log_audit('CANCEL_REQUEST', 'recipient_requests', request_id, f"Cancelled request '{request_id}'")
        flash(f"Request '{request_id}' cancelled successfully.", 'success')
    else:
        flash(f"Request '{request_id}' could not be cancelled.", 'error')
    return redirect(url_for('requests_bp.list_requests'))


@requests_bp.route('/requests/<request_id>/confirm-receipt', methods=['POST'])
@roles_required('recipient', 'admin')
def confirm_receipt(request_id):
    """Recipient confirms receipt of allocated food."""
    req_item = get_request_by_id(request_id)
    if not req_item:
        flash(f"Request '{request_id}' not found.", 'error')
        return redirect(url_for('requests_bp.list_requests'))

    current_user = get_current_user()
    if not can_manage_request(req_item, current_user):
        if is_api_request():
            return jsonify({'error': 'Forbidden', 'message': 'You do not own this request.'}), 403
        return render_template('errors/403.html', user_role=current_user['role'], required_roles=['Owner or Admin']), 403

    from database.db import get_db
    db = get_db()
    db.execute(
        """UPDATE allocations SET status = 'confirmed'
           WHERE request_id = ? AND status != 'cancelled'""",
        (req_item['id'],),
    )
    db.commit()

    log_audit('CONFIRM_RECEIPT', 'recipient_requests', request_id, f"Recipient confirmed receipt for '{request_id}'")
    flash(f"Delivery receipt confirmed for '{req_item['organization_name']}'. Community nourished!", 'success')
    return redirect(url_for('requests_bp.list_requests'))


@requests_bp.route('/api/requests')
@login_required
def api_requests():
    """JSON API endpoint returning requests."""
    status_filter = request.args.get('status')
    category_filter = request.args.get('category')
    all_requests = get_all_requests(
        status_filter=status_filter,
        category_filter=category_filter,
    )
    return jsonify(all_requests)
