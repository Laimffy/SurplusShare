"""Service functions for food listing CRUD operations."""

from datetime import datetime, timedelta
from database.db import get_db

ALLOWED_CATEGORIES = [
    'Bakery', 'Vegetables', 'Fruits', 'Prepared Meals',
    'Dairy', 'Dry Goods', 'Other'
]

ALLOWED_STATUSES = [
    'available', 'partially_allocated', 'fully_allocated', 'expired', 'cancelled'
]


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


def _generate_listing_id():
    """Generate the next listing ID in FL-XXX pattern.

    Returns:
        str: A unique listing ID like 'FL-021'.
    """
    db = get_db()
    row = db.execute(
        "SELECT listing_id FROM food_listings ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return 'FL-001'
    last_id = row['listing_id']
    try:
        num = int(last_id.split('-')[1]) + 1
    except (IndexError, ValueError):
        num = 1
    return f'FL-{num:03d}'


def _validate_listing_data(data, is_update=False):
    """Validate listing data for create or update operations.

    Args:
        data: Dictionary containing listing fields.
        is_update: If True, skip validations only required for creation.

    Returns:
        tuple: (is_valid: bool, errors: list of str)
    """
    errors = []

    if 'quantity' in data:
        try:
            qty = float(data['quantity'])
            if qty <= 0:
                errors.append('Quantity must be a positive number.')
        except (TypeError, ValueError):
            errors.append('Quantity must be a valid number.')

    if 'category' in data:
        if data['category'] not in ALLOWED_CATEGORIES:
            errors.append(f"Category must be one of: {', '.join(ALLOWED_CATEGORIES)}.")

    if 'expiry_at' in data:
        try:
            expiry = datetime.fromisoformat(data['expiry_at'])
            if not is_update and expiry <= datetime.now():
                errors.append('Expiry date must be in the future for new listings.')
        except (TypeError, ValueError):
            errors.append('Expiry date must be in valid ISO 8601 format (e.g., 2024-01-15T10:30:00).')

    if not is_update:
        if not data.get('pickup_location', '').strip():
            errors.append('Pickup location is required.')
        if not data.get('food_name', '').strip():
            errors.append('Food name is required.')
        if not data.get('unit', '').strip():
            errors.append('Unit is required.')
        if not data.get('donor_name', '').strip():
            errors.append('Donor name is required.')

    if is_update and 'pickup_location' in data:
        if not data['pickup_location'].strip():
            errors.append('Pickup location cannot be empty.')

    return (len(errors) == 0, errors)


def get_all_listings(status_filter=None, category_filter=None):
    """Retrieve all food listings with optional filters.

    Args:
        status_filter: Filter by listing status (e.g., 'available').
        category_filter: Filter by food category (e.g., 'Bakery').

    Returns:
        list: List of listing dictionaries.
    """
    db = get_db()
    query = "SELECT * FROM food_listings WHERE 1=1"
    params = []

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)

    query += " ORDER BY posted_at DESC"
    rows = db.execute(query, params).fetchall()
    return _rows_to_list(rows)


def get_listing_by_id(listing_id):
    """Retrieve a listing by its text listing_id (e.g., 'FL-001').

    Args:
        listing_id: The text-based listing identifier.

    Returns:
        dict or None: Listing dictionary or None if not found.
    """
    db = get_db()
    row = db.execute(
        "SELECT * FROM food_listings WHERE listing_id = ?", (listing_id,)
    ).fetchone()
    return _row_to_dict(row)


def get_listing_by_pk(pk):
    """Retrieve a listing by its integer primary key.

    Args:
        pk: Integer primary key (id column).

    Returns:
        dict or None: Listing dictionary or None if not found.
    """
    db = get_db()
    row = db.execute(
        "SELECT * FROM food_listings WHERE id = ?", (pk,)
    ).fetchone()
    return _row_to_dict(row)


def create_listing(data):
    """Create a new food listing.

    Args:
        data: Dictionary with listing fields. Required: food_name, category,
              quantity, unit, donor_name, expiry_at, pickup_location.
              Optional: listing_id, posted_at, storage_requirements,
              food_condition, donor_id.

    Returns:
        dict: The created listing dictionary.

    Raises:
        ValueError: If validation fails or listing_id already exists.
    """
    is_valid, errors = _validate_listing_data(data, is_update=False)
    if not is_valid:
        raise ValueError('; '.join(errors))

    db = get_db()
    listing_id = data.get('listing_id', '').strip()
    if not listing_id:
        listing_id = _generate_listing_id()
    else:
        existing = db.execute(
            "SELECT id FROM food_listings WHERE listing_id = ?", (listing_id,)
        ).fetchone()
        if existing:
            raise ValueError(f"Listing ID '{listing_id}' already exists.")

    posted_at = data.get('posted_at', datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))

    db.execute(
        """INSERT INTO food_listings
           (listing_id, food_name, category, quantity, unit, donor_name, donor_id,
            posted_at, expiry_at, pickup_location, storage_requirements,
            food_condition, status, allocated_quantity)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            listing_id,
            data['food_name'].strip(),
            data['category'],
            float(data['quantity']),
            data['unit'].strip(),
            data['donor_name'].strip(),
            data.get('donor_id'),
            posted_at,
            data['expiry_at'],
            data.get('pickup_location', '').strip(),
            data.get('storage_requirements', ''),
            data.get('food_condition', 'Good'),
            'available',
            0,
        ),
    )
    db.commit()
    return get_listing_by_id(listing_id)


def update_listing(listing_id, data):
    """Update an existing food listing.

    Args:
        listing_id: The text-based listing identifier (e.g., 'FL-001').
        data: Dictionary with fields to update.

    Returns:
        dict: The updated listing dictionary.

    Raises:
        ValueError: If validation fails or listing not found.
    """
    existing = get_listing_by_id(listing_id)
    if existing is None:
        raise ValueError(f"Listing '{listing_id}' not found.")

    is_valid, errors = _validate_listing_data(data, is_update=True)
    if not is_valid:
        raise ValueError('; '.join(errors))

    db = get_db()
    updatable_fields = [
        'food_name', 'category', 'quantity', 'unit', 'donor_name',
        'expiry_at', 'pickup_location', 'storage_requirements',
        'food_condition', 'status', 'allocated_quantity'
    ]

    set_clauses = []
    params = []
    for field in updatable_fields:
        if field in data:
            set_clauses.append(f"{field} = ?")
            value = data[field]
            if field == 'quantity' or field == 'allocated_quantity':
                value = float(value)
            elif isinstance(value, str):
                value = value.strip()
            params.append(value)

    if not set_clauses:
        return existing

    params.append(listing_id)
    db.execute(
        f"UPDATE food_listings SET {', '.join(set_clauses)} WHERE listing_id = ?",
        params,
    )
    db.commit()
    return get_listing_by_id(listing_id)


def delete_listing(listing_id):
    """Delete a food listing by its text listing_id.

    Args:
        listing_id: The text-based listing identifier.

    Returns:
        bool: True if deleted, False if not found.
    """
    db = get_db()
    result = db.execute(
        "DELETE FROM food_listings WHERE listing_id = ?", (listing_id,)
    )
    db.commit()
    return result.rowcount > 0


def get_listings_by_category(category):
    """Retrieve all listings in a specific category.

    Args:
        category: Food category string.

    Returns:
        list: List of listing dictionaries.
    """
    db = get_db()
    rows = db.execute(
        "SELECT * FROM food_listings WHERE category = ? ORDER BY posted_at DESC",
        (category,),
    ).fetchall()
    return _rows_to_list(rows)


def get_expiring_listings(hours=24):
    """Retrieve available listings expiring within the specified hours.

    Args:
        hours: Number of hours from now to check for expiry.

    Returns:
        list: List of listing dictionaries expiring soon.
    """
    db = get_db()
    now_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    deadline_str = (datetime.now() + timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M:%S')
    rows = db.execute(
        """SELECT * FROM food_listings
           WHERE status IN ('available', 'partially_allocated')
             AND expiry_at > ?
             AND expiry_at <= ?
           ORDER BY expiry_at ASC""",
        (now_str, deadline_str),
    ).fetchall()
    return _rows_to_list(rows)


def get_expired_listings():
    """Retrieve all listings that have passed their expiry date.

    Returns:
        list: List of expired listing dictionaries.
    """
    db = get_db()
    now_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    rows = db.execute(
        """SELECT * FROM food_listings
           WHERE expiry_at <= ?
           ORDER BY expiry_at DESC""",
        (now_str,),
    ).fetchall()
    return _rows_to_list(rows)


def update_listing_status(listing_id, status):
    """Update the status of a food listing.

    Args:
        listing_id: The text-based listing identifier.
        status: New status value.

    Returns:
        bool: True if updated, False if not found.

    Raises:
        ValueError: If status is invalid.
    """
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Status must be one of: {', '.join(ALLOWED_STATUSES)}.")

    db = get_db()
    result = db.execute(
        "UPDATE food_listings SET status = ? WHERE listing_id = ?",
        (status, listing_id),
    )
    db.commit()
    return result.rowcount > 0


def get_dashboard_stats():
    """Get summary statistics for the dashboard.

    Returns:
        dict: Dictionary with counts and summary data including:
            - total_listings, available_listings, expired_listings
            - total_requests, pending_requests, fulfilled_requests
            - total_allocations, total_quantity_allocated
            - expiring_soon_count, urgent_count
            - categories breakdown
    """
    db = get_db()

    total_listings = db.execute("SELECT COUNT(*) as c FROM food_listings").fetchone()['c']
    available_listings = db.execute(
        "SELECT COUNT(*) as c FROM food_listings WHERE status = 'available'"
    ).fetchone()['c']
    expired_listings = db.execute(
        "SELECT COUNT(*) as c FROM food_listings WHERE status = 'expired'"
    ).fetchone()['c']
    fully_allocated = db.execute(
        "SELECT COUNT(*) as c FROM food_listings WHERE status = 'fully_allocated'"
    ).fetchone()['c']

    total_requests = db.execute("SELECT COUNT(*) as c FROM recipient_requests").fetchone()['c']
    pending_requests = db.execute(
        "SELECT COUNT(*) as c FROM recipient_requests WHERE status = 'pending'"
    ).fetchone()['c']
    fulfilled_requests = db.execute(
        "SELECT COUNT(*) as c FROM recipient_requests WHERE status = 'fulfilled'"
    ).fetchone()['c']

    total_allocations = db.execute("SELECT COUNT(*) as c FROM allocations").fetchone()['c']
    qty_row = db.execute(
        "SELECT COALESCE(SUM(allocated_quantity), 0) as total FROM allocations"
    ).fetchone()
    total_quantity_allocated = qty_row['total']

    from flask import current_app
    warning_hours = current_app.config.get('EXPIRY_WARNING_HOURS', 24)
    urgent_hours = current_app.config.get('EXPIRY_URGENT_HOURS', 6)

    now_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    warning_str = (datetime.now() + timedelta(hours=warning_hours)).strftime('%Y-%m-%dT%H:%M:%S')
    urgent_str = (datetime.now() + timedelta(hours=urgent_hours)).strftime('%Y-%m-%dT%H:%M:%S')

    expiring_soon_count = db.execute(
        """SELECT COUNT(*) as c FROM food_listings
           WHERE status IN ('available', 'partially_allocated')
             AND expiry_at > ? AND expiry_at <= ?""",
        (now_str, warning_str),
    ).fetchone()['c']

    urgent_count = db.execute(
        """SELECT COUNT(*) as c FROM food_listings
           WHERE status IN ('available', 'partially_allocated')
             AND expiry_at > ? AND expiry_at <= ?""",
        (now_str, urgent_str),
    ).fetchone()['c']

    category_rows = db.execute(
        """SELECT category, COUNT(*) as count
           FROM food_listings
           WHERE status IN ('available', 'partially_allocated')
           GROUP BY category ORDER BY count DESC"""
    ).fetchall()
    categories = {r['category']: r['count'] for r in category_rows}

    return {
        'total_listings': total_listings,
        'available_listings': available_listings,
        'expired_listings': expired_listings,
        'fully_allocated': fully_allocated,
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'fulfilled_requests': fulfilled_requests,
        'total_allocations': total_allocations,
        'total_quantity_allocated': total_quantity_allocated,
        'expiring_soon_count': expiring_soon_count,
        'urgent_count': urgent_count,
        'categories': categories,
    }
