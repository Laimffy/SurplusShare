"""Reports routes blueprint for SurplusShare."""

import csv
import io
from flask import Blueprint, render_template, make_response
from services.listing_service import get_all_listings, get_dashboard_stats
from services.request_service import get_all_requests
from services.allocation_service import get_all_allocations
from services.auth_service import admin_required, get_current_user

reports = Blueprint('reports', __name__)


@reports.route('/reports')
@admin_required
def reports_page():
    """Render the reports page with summary data and statistics."""
    current_user = get_current_user()
    stats = get_dashboard_stats()
    all_listings = get_all_listings()
    all_requests = get_all_requests()
    all_allocations = get_all_allocations()

    return render_template(
        'reports.html',
        stats=stats,
        listings=all_listings,
        requests=all_requests,
        allocations=all_allocations,
        current_user=current_user,
    )


@reports.route('/reports/export/csv')
@admin_required
def export_csv():
    """Export all food listings as a CSV file download."""
    all_listings = get_all_listings()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Listing ID', 'Food Name', 'Category', 'Quantity', 'Unit',
        'Donor Name', 'Posted At', 'Expiry At', 'Pickup Location',
        'Storage Requirements', 'Food Condition', 'Status',
        'Allocated Quantity', 'Created At',
    ])

    for listing in all_listings:
        writer.writerow([
            listing.get('listing_id', ''),
            listing.get('food_name', ''),
            listing.get('category', ''),
            listing.get('quantity', ''),
            listing.get('unit', ''),
            listing.get('donor_name', ''),
            listing.get('posted_at', ''),
            listing.get('expiry_at', ''),
            listing.get('pickup_location', ''),
            listing.get('storage_requirements', ''),
            listing.get('food_condition', ''),
            listing.get('status', ''),
            listing.get('allocated_quantity', ''),
            listing.get('created_at', ''),
        ])

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=surplusshare_listings.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response
