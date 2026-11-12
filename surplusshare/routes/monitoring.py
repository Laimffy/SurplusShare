"""Monitoring routes blueprint for SurplusShare."""

from flask import Blueprint, render_template, request
from services.listing_service import get_expiring_listings, get_expired_listings
from services.auth_service import roles_required, get_current_user

monitoring = Blueprint('monitoring', __name__)


@monitoring.route('/monitoring')
@roles_required('donor', 'admin')
def monitoring_page():
    """Render the monitoring page showing expiring and expired listings."""
    current_user = get_current_user()
    hours = request.args.get('hours', 24, type=int)
    expiring = get_expiring_listings(hours=hours)
    expired = get_expired_listings()

    # If donor, scope to their own inventory
    if current_user['role'] == 'donor':
        donor_org = (current_user.get('organization') or '').strip().lower()
        donor_disp = (current_user.get('display_name') or '').strip().lower()
        donor_user = (current_user.get('username') or '').strip().lower()

        def _is_donor_item(item):
            if item.get('donor_id') and item['donor_id'] == current_user['id']:
                return True
            dname = (item.get('donor_name') or '').strip().lower()
            return dname in (donor_org, donor_disp, donor_user)

        expiring = [item for item in expiring if _is_donor_item(item)]
        expired = [item for item in expired if _is_donor_item(item)]

    return render_template(
        'monitoring.html',
        expiring_listings=expiring,
        expired_listings=expired,
        hours=hours,
        current_user=current_user,
    )
