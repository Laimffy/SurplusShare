"""Settings routes blueprint for SurplusShare."""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from services.auth_service import admin_required, get_current_user
from services.audit_service import log_audit

settings = Blueprint('settings', __name__)


@settings.route('/settings')
@admin_required
def settings_page():
    """Render the settings page."""
    current_user = get_current_user()
    return render_template('settings.html', current_user=current_user)


@settings.route('/settings', methods=['POST'])
@admin_required
def update_settings():
    """Handle settings form submission."""
    warning_h = request.form.get('warning_hours', '24')
    urgent_h = request.form.get('urgent_hours', '6')
    log_audit('UPDATE_SETTINGS', 'system_settings', None, f"Updated thresholds: warning={warning_h}h, urgent={urgent_h}h")
    flash('System settings updated successfully.', 'success')
    return redirect(url_for('settings.settings_page'))
