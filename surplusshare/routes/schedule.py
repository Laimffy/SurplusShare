"""Schedule routes blueprint for SurplusShare."""

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify,
)

from database.db import get_db
from algorithms.doubly_linked_list import DoublyLinkedList, PickupNode, PickupScheduleList
from services.schedule_service import (
    get_all_schedules,
    get_schedule_by_id,
    create_schedule,
    get_stops_for_schedule,
    add_stop,
    remove_stop,
    update_stop_status,
    STOP_STATUSES,
)
from services.listing_service import get_all_listings
from services.auth_service import (
    login_required,
    roles_required,
    admin_required,
    get_current_user,
    can_manage_schedule,
    can_view_schedule,
    is_api_request,
)
from services.audit_service import log_audit

schedule = Blueprint('schedule', __name__)


@schedule.route('/schedule')
@login_required
def list_schedules():
    """Render the schedule list page filtered by role access."""
    current_user = get_current_user()
    all_scheds = get_all_schedules()

    if current_user['role'] == 'volunteer':
        schedules = [s for s in all_scheds if can_manage_schedule(s, current_user)]
    elif current_user['role'] == 'donor':
        schedules = [s for s in all_scheds if can_view_schedule(s, current_user)]
    elif current_user['role'] == 'recipient':
        schedules = [s for s in all_scheds if can_view_schedule(s, current_user)]
    else:
        schedules = all_scheds

    return render_template('schedule.html', schedules=schedules, current_user=current_user)


@schedule.route('/schedule/new')
@roles_required('volunteer', 'admin')
def new_schedule():
    """Render the schedule creation form."""
    current_user = get_current_user()
    default_name = current_user['display_name'] if current_user['role'] == 'volunteer' else ''
    return render_template('schedule_form.html', sched={'volunteer_name': default_name})


@schedule.route('/schedule', methods=['POST'])
@roles_required('volunteer', 'admin')
def create_schedule_route():
    """Handle schedule creation form submission."""
    current_user = get_current_user()
    vol_name = request.form.get('volunteer_name', '').strip()
    if current_user['role'] == 'volunteer' and not vol_name:
        vol_name = current_user['display_name']

    data = {
        'volunteer_name': vol_name,
        'schedule_date': request.form.get('schedule_date', ''),
    }

    try:
        created = create_schedule(data)
        log_audit(
            'CREATE_SCHEDULE',
            'pickup_schedules',
            created['schedule_id'],
            f"Created route for volunteer '{vol_name}' on {data['schedule_date']}",
        )
        flash(f"Schedule '{created['schedule_id']}' created successfully.", 'success')
        return redirect(url_for('schedule.schedule_detail', schedule_id=created['schedule_id']))
    except ValueError as e:
        flash(str(e), 'error')
        return render_template('schedule_form.html', sched=data), 400


@schedule.route('/schedule/<schedule_id>')
@login_required
def schedule_detail(schedule_id):
    """
    Render detail page for a single schedule with its stops.
    Reconstructs the Doubly Linked List to provide forward and backward
    traversal links and order inspection for DSA evaluation.
    """
    sched = get_schedule_by_id(schedule_id)
    if sched is None:
        flash('Schedule not found.', 'error')
        return redirect(url_for('schedule.list_schedules'))

    current_user = get_current_user()
    if current_user['role'] == 'volunteer':
        if not can_manage_schedule(sched, current_user):
            if is_api_request():
                return jsonify({'error': 'Forbidden', 'message': 'You can only view your own assigned pickup schedules.'}), 403
            return render_template('errors/403.html', user_role=current_user['role'], required_roles=['Assigned Volunteer or Admin']), 403
    elif current_user['role'] in ('donor', 'recipient'):
        if not can_view_schedule(sched, current_user):
            if is_api_request():
                return jsonify({'error': 'Forbidden', 'message': 'You can only view schedules relevant to your food donations.'}), 403
            return render_template('errors/403.html', user_role=current_user['role'], required_roles=['Owner or Admin']), 403

    user_can_manage = can_manage_schedule(sched, current_user)

    # Build Doubly Linked List from stops
    dll = DoublyLinkedList.from_list(sched.get('stops', []))
    forward_stops = dll.to_list()
    backward_stops = [node.to_dict() for node in dll.traverse_backward()]

    # Available listings for assigning stops
    available_listings = get_all_listings(status_filter='available')

    return render_template(
        'schedule_detail.html',
        schedule=sched,
        stops=forward_stops,
        backward_stops=backward_stops,
        stop_statuses=STOP_STATUSES,
        available_listings=available_listings,
        dll_size=dll.get_size(),
        user_can_manage=user_can_manage,
    )


@schedule.route('/schedule/<schedule_id>/stops', methods=['POST'])
@admin_required
def add_stop_route(schedule_id):
    """Add a new stop to a schedule."""
    sched = get_schedule_by_id(schedule_id)
    if sched is None:
        flash('Schedule not found.', 'error')
        return redirect(url_for('schedule.list_schedules'))

    data = {
        'donor_name': request.form.get('donor_name', ''),
        'pickup_location': request.form.get('pickup_location', ''),
        'scheduled_time': request.form.get('scheduled_time', ''),
        'stop_order': request.form.get('stop_order'),
        'listing_id': request.form.get('listing_id') or None,
        'notes': request.form.get('notes', ''),
    }

    try:
        stop = add_stop(sched['id'], data)
        log_audit('ADD_STOP', 'pickup_stops', stop['stop_id'], f"Appended stop at '{data['pickup_location']}' to {schedule_id}")
        flash(f"Stop '{stop['stop_id']}' added successfully to schedule.", 'success')
    except ValueError as e:
        flash(str(e), 'error')

    return redirect(url_for('schedule.schedule_detail', schedule_id=schedule_id))


@schedule.route('/schedule/<schedule_id>/stops/<stop_id>/move', methods=['POST'])
@roles_required('volunteer', 'admin')
def move_stop_route(schedule_id, stop_id):
    """
    Move a stop up or down in the schedule using Doubly Linked List pointer operations.
    Updates the database with the resulting node sequence.
    """
    sched = get_schedule_by_id(schedule_id)
    if sched is None:
        flash('Schedule not found.', 'error')
        return redirect(url_for('schedule.list_schedules'))

    current_user = get_current_user()
    if not can_manage_schedule(sched, current_user):
        if is_api_request():
            return jsonify({'error': 'Forbidden', 'message': 'You can only reorder stops on your own assigned schedule.'}), 403
        return render_template('errors/403.html', user_role=current_user['role'], required_roles=['Assigned Volunteer or Admin']), 403

    direction = request.form.get('direction', 'down')
    dll = DoublyLinkedList.from_list(sched.get('stops', []))

    if direction == 'up':
        success = dll.swap_adjacent_backward(stop_id)
    else:
        success = dll.swap_adjacent_forward(stop_id)

    if success:
        db = get_db()
        ordered_stops = dll.to_list()
        for idx, s in enumerate(ordered_stops, start=1):
            db.execute(
                "UPDATE pickup_stops SET stop_order = ? WHERE stop_id = ?",
                (idx, s['stop_id']),
            )
        db.commit()
        log_audit('MOVE_STOP', 'pickup_stops', stop_id, f"Exchanged DLL node pointers for stop '{stop_id}' ({direction})")
        flash(f"Stop '{stop_id}' moved {direction} via Doubly Linked List pointer exchange.", 'success')
    else:
        flash(f"Stop '{stop_id}' cannot be moved further in that direction.", 'info')

    return redirect(url_for('schedule.schedule_detail', schedule_id=schedule_id))


@schedule.route('/schedule/stops/<stop_id>/remove', methods=['POST'])
@admin_required
def remove_stop_route(stop_id):
    """Remove a stop from its schedule."""
    schedule_id = request.form.get('schedule_id', '')
    if remove_stop(stop_id):
        log_audit('REMOVE_STOP', 'pickup_stops', stop_id, f"Unlinked stop '{stop_id}'")
        flash(f"Stop '{stop_id}' removed.", 'success')
    else:
        flash(f"Stop '{stop_id}' not found.", 'error')

    if schedule_id:
        return redirect(url_for('schedule.schedule_detail', schedule_id=schedule_id))
    return redirect(url_for('schedule.list_schedules'))


@schedule.route('/schedule/stops/<stop_id>/status', methods=['POST'])
@roles_required('volunteer', 'admin')
def update_stop_status_route(stop_id):
    """Update the status of a pickup stop with schedule ownership check and valid state transitions."""
    new_status = request.form.get('status', '').strip().lower()
    schedule_id = request.form.get('schedule_id', '').strip()

    if new_status not in STOP_STATUSES:
        flash(f"Invalid stop status '{new_status}'.", 'error')
        if schedule_id:
            return redirect(url_for('schedule.schedule_detail', schedule_id=schedule_id))
        return redirect(url_for('schedule.list_schedules'))

    current_user = get_current_user()
    db = get_db()
    stop_row = db.execute(
        """SELECT pst.*, ps.schedule_id as sched_code, ps.volunteer_name 
           FROM pickup_stops pst 
           JOIN pickup_schedules ps ON pst.schedule_id = ps.id 
           WHERE pst.stop_id = ?""",
        (stop_id,),
    ).fetchone()

    if not stop_row:
        flash(f"Stop '{stop_id}' not found.", 'error')
        return redirect(url_for('schedule.list_schedules'))

    sched_dict = {'schedule_id': stop_row['sched_code'], 'volunteer_name': stop_row['volunteer_name']}
    if not can_manage_schedule(sched_dict, current_user):
        if is_api_request():
            return jsonify({'error': 'Forbidden', 'message': 'You can only update stops on your own assigned schedule.'}), 403
        return render_template('errors/403.html', user_role=current_user['role'], required_roles=['Assigned Volunteer or Admin']), 403

    try:
        if update_stop_status(stop_id, new_status):
            log_audit('UPDATE_STOP_STATUS', 'pickup_stops', stop_id, f"Volunteer updated stop '{stop_id}' status to '{new_status}'")
            flash(f"Stop '{stop_id}' status updated to '{new_status}'.", 'success')
        else:
            flash(f"Stop '{stop_id}' not found.", 'error')
    except ValueError as e:
        flash(str(e), 'error')

    target_sched = schedule_id or stop_row['sched_code']
    return redirect(url_for('schedule.schedule_detail', schedule_id=target_sched))


@schedule.route('/api/schedule/<schedule_id>/stops')
@login_required
def api_schedule_stops(schedule_id):
    """JSON API endpoint returning stops for a schedule."""
    sched = get_schedule_by_id(schedule_id)
    if sched is None:
        return jsonify({'error': 'Schedule not found'}), 404

    current_user = get_current_user()
    if not can_view_schedule(sched, current_user):
        return jsonify({'error': 'Forbidden', 'message': 'Access denied to this schedule.'}), 403

    stops = get_stops_for_schedule(sched['id'])
    return jsonify(stops)
