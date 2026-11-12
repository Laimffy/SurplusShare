"""Service functions for pickup schedule operations."""

from datetime import datetime
from database.db import get_db


SCHEDULE_STATUSES = ['planned', 'in_progress', 'completed', 'cancelled']
STOP_STATUSES = ['pending', 'completed', 'skipped', 'cancelled']


def _row_to_dict(row):
    """Convert a sqlite3.Row to a dictionary.

    Args:
        row: A sqlite3.Row object.

    Returns:
        dict or None: Dictionary representation of the row.
    """
    if row is None:
        return None
    return dict(row)


def _rows_to_list(rows):
    """Convert a list of sqlite3.Row objects to a list of dicts.

    Args:
        rows: List of sqlite3.Row objects.

    Returns:
        list: List of dictionaries.
    """
    return [dict(r) for r in rows]


def _generate_schedule_id():
    """Generate the next schedule ID in PS-XXX pattern.

    Returns:
        str: A unique schedule ID.
    """
    db = get_db()
    row = db.execute(
        "SELECT schedule_id FROM pickup_schedules ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return 'PS-001'
    last_id = row['schedule_id']
    try:
        num = int(last_id.split('-')[1]) + 1
    except (IndexError, ValueError):
        num = 1
    return f'PS-{num:03d}'


def _generate_stop_id():
    """Generate the next stop ID in ST-XXX pattern.

    Returns:
        str: A unique stop ID.
    """
    db = get_db()
    row = db.execute(
        "SELECT stop_id FROM pickup_stops ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return 'ST-001'
    last_id = row['stop_id']
    try:
        num = int(last_id.split('-')[1]) + 1
    except (IndexError, ValueError):
        num = 1
    return f'ST-{num:03d}'


def get_all_schedules():
    """Retrieve all pickup schedules with stop counts.

    Returns:
        list: List of schedule dictionaries with stop_count field.
    """
    db = get_db()
    rows = db.execute(
        """SELECT ps.*, COUNT(pst.id) AS stop_count
           FROM pickup_schedules ps
           LEFT JOIN pickup_stops pst ON ps.id = pst.schedule_id
           GROUP BY ps.id
           ORDER BY ps.schedule_date DESC"""
    ).fetchall()
    return _rows_to_list(rows)


def get_schedule_by_id(schedule_id):
    """Retrieve a schedule by its text schedule_id with its stops.

    Args:
        schedule_id: The text-based schedule identifier (e.g., 'PS-001').

    Returns:
        dict or None: Schedule dictionary with 'stops' list, or None.
    """
    db = get_db()
    row = db.execute(
        "SELECT * FROM pickup_schedules WHERE schedule_id = ?", (schedule_id,)
    ).fetchone()
    if row is None:
        return None

    schedule = dict(row)
    stops = db.execute(
        """SELECT * FROM pickup_stops
           WHERE schedule_id = ?
           ORDER BY stop_order ASC""",
        (schedule['id'],),
    ).fetchall()
    schedule['stops'] = _rows_to_list(stops)
    return schedule


def create_schedule(data):
    """Create a new pickup schedule.

    Args:
        data: Dictionary with fields: volunteer_name, schedule_date.
              Optional: schedule_id, status.

    Returns:
        dict: The created schedule dictionary with empty stops list.

    Raises:
        ValueError: If required fields are missing.
    """
    if not data.get('volunteer_name', '').strip():
        raise ValueError('Volunteer name is required.')
    if not data.get('schedule_date', '').strip():
        raise ValueError('Schedule date is required.')

    db = get_db()
    schedule_id = data.get('schedule_id', '').strip()
    if not schedule_id:
        schedule_id = _generate_schedule_id()

    db.execute(
        """INSERT INTO pickup_schedules
           (schedule_id, volunteer_name, schedule_date, status)
           VALUES (?, ?, ?, ?)""",
        (
            schedule_id,
            data['volunteer_name'].strip(),
            data['schedule_date'].strip(),
            data.get('status', 'planned'),
        ),
    )
    db.commit()
    return get_schedule_by_id(schedule_id)


def get_stops_for_schedule(schedule_pk):
    """Retrieve all stops for a schedule, ordered by stop_order.

    Args:
        schedule_pk: Integer primary key of the schedule.

    Returns:
        list: List of stop dictionaries ordered by stop_order.
    """
    db = get_db()
    rows = db.execute(
        """SELECT * FROM pickup_stops
           WHERE schedule_id = ?
           ORDER BY stop_order ASC""",
        (schedule_pk,),
    ).fetchall()
    return _rows_to_list(rows)


def add_stop(schedule_pk, data):
    """Add a new stop to a pickup schedule.

    Args:
        schedule_pk: Integer primary key of the schedule.
        data: Dictionary with fields: donor_name, pickup_location,
              scheduled_time, stop_order. Optional: listing_id, notes.

    Returns:
        dict: The created stop dictionary.

    Raises:
        ValueError: If required fields are missing or schedule not found.
    """
    db = get_db()

    schedule = db.execute(
        "SELECT * FROM pickup_schedules WHERE id = ?", (schedule_pk,)
    ).fetchone()
    if schedule is None:
        raise ValueError(f"Schedule with pk={schedule_pk} not found.")

    if not data.get('donor_name', '').strip():
        raise ValueError('Donor name is required.')
    if not data.get('pickup_location', '').strip():
        raise ValueError('Pickup location is required.')
    if not data.get('scheduled_time', '').strip():
        raise ValueError('Scheduled time is required.')

    stop_order = data.get('stop_order')
    if stop_order is None:
        max_row = db.execute(
            "SELECT COALESCE(MAX(stop_order), 0) AS max_order FROM pickup_stops WHERE schedule_id = ?",
            (schedule_pk,),
        ).fetchone()
        stop_order = max_row['max_order'] + 1
    else:
        stop_order = int(stop_order)

    stop_id = _generate_stop_id()

    db.execute(
        """INSERT INTO pickup_stops
           (stop_id, schedule_id, donor_name, pickup_location, listing_id,
            scheduled_time, stop_order, status, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            stop_id,
            schedule_pk,
            data['donor_name'].strip(),
            data['pickup_location'].strip(),
            data.get('listing_id'),
            data['scheduled_time'].strip(),
            stop_order,
            'pending',
            data.get('notes', ''),
        ),
    )
    db.commit()

    row = db.execute(
        "SELECT * FROM pickup_stops WHERE stop_id = ?", (stop_id,)
    ).fetchone()
    return _row_to_dict(row)


def remove_stop(stop_id):
    """Remove a stop from a schedule.

    Args:
        stop_id: The text-based stop identifier (e.g., 'ST-001').

    Returns:
        bool: True if removed, False if not found.
    """
    db = get_db()
    result = db.execute(
        "DELETE FROM pickup_stops WHERE stop_id = ?", (stop_id,)
    )
    db.commit()
    return result.rowcount > 0


def reorder_stop(stop_id, new_order):
    """Change the order of a stop within its schedule.

    Args:
        stop_id: The text-based stop identifier.
        new_order: The new integer stop_order value.

    Returns:
        bool: True if updated, False if not found.
    """
    db = get_db()
    new_order = int(new_order)
    result = db.execute(
        "UPDATE pickup_stops SET stop_order = ? WHERE stop_id = ?",
        (new_order, stop_id),
    )
    db.commit()
    return result.rowcount > 0


def update_stop_status(stop_id, status):
    """Update the status of a pickup stop.

    Args:
        stop_id: The text-based stop identifier.
        status: New status value.

    Returns:
        bool: True if updated, False if not found.

    Raises:
        ValueError: If status is invalid.
    """
    if status not in STOP_STATUSES:
        raise ValueError(f"Stop status must be one of: {', '.join(STOP_STATUSES)}.")

    db = get_db()
    result = db.execute(
        "UPDATE pickup_stops SET status = ? WHERE stop_id = ?",
        (status, stop_id),
    )
    db.commit()
    return result.rowcount > 0
