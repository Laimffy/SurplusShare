"""Service functions for recipient request CRUD operations."""

from datetime import datetime
from database.db import get_db

ALLOWED_CATEGORIES = [
    'Bakery', 'Vegetables', 'Fruits', 'Prepared Meals',
    'Dairy', 'Dry Goods', 'Other'
]

ALLOWED_STATUSES = [
    'pending', 'partially_fulfilled', 'fulfilled', 'cancelled', 'expired'
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


def _generate_request_id():
    """Generate the next request ID in RR-XXX pattern.

    Returns:
        str: A unique request ID like 'RR-011'.
    """
    db = get_db()
    row = db.execute(
        "SELECT request_id FROM recipient_requests ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return 'RR-001'
    last_id = row['request_id']
    try:
        num = int(last_id.split('-')[1]) + 1
    except (IndexError, ValueError):
        num = 1
    return f'RR-{num:03d}'


def _validate_request_data(data, is_update=False):
    """Validate request data for create or update operations.

    Args:
        data: Dictionary containing request fields.
        is_update: If True, skip validations only required for creation.

    Returns:
        tuple: (is_valid: bool, errors: list of str)
    """
    errors = []

    if 'requested_quantity' in data:
        try:
            qty = float(data['requested_quantity'])
            if qty <= 0:
                errors.append('Requested quantity must be a positive number.')
        except (TypeError, ValueError):
            errors.append('Requested quantity must be a valid number.')

    if 'food_category' in data:
        if data['food_category'] not in ALLOWED_CATEGORIES:
            errors.append(f"Food category must be one of: {', '.join(ALLOWED_CATEGORIES)}.")

    if not is_update:
        if not data.get('organization_name', '').strip():
            errors.append('Organization name is required.')
        if not data.get('food_category', '').strip():
            errors.append('Food category is required.')
        if not data.get('quantity_unit', '').strip():
            errors.append('Quantity unit is required.')

    return (len(errors) == 0, errors)


def get_all_requests(status_filter=None, category_filter=None):
    """Retrieve all recipient requests with optional filters.

    Args:
        status_filter: Filter by request status (e.g., 'pending').
        category_filter: Filter by food category (e.g., 'Bakery').

    Returns:
        list: List of request dictionaries.
    """
    db = get_db()
    query = "SELECT * FROM recipient_requests WHERE 1=1"
    params = []

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
    if category_filter:
        query += " AND food_category = ?"
        params.append(category_filter)

    query += " ORDER BY requested_at DESC"
    rows = db.execute(query, params).fetchall()
    return _rows_to_list(rows)


def get_request_by_id(request_id):
    """Retrieve a request by its text request_id (e.g., 'RR-001').

    Args:
        request_id: The text-based request identifier.

    Returns:
        dict or None: Request dictionary or None if not found.
    """
    db = get_db()
    row = db.execute(
        "SELECT * FROM recipient_requests WHERE request_id = ?", (request_id,)
    ).fetchone()
    return _row_to_dict(row)


def create_request(data):
    """Create a new recipient request.

    Args:
        data: Dictionary with request fields. Required: organization_name,
              food_category, requested_quantity, quantity_unit.
              Optional: request_id, min_shelf_life_hours, recipient_id.

    Returns:
        dict: The created request dictionary.

    Raises:
        ValueError: If validation fails.
    """
    is_valid, errors = _validate_request_data(data, is_update=False)
    if not is_valid:
        raise ValueError('; '.join(errors))

    db = get_db()
    request_id = data.get('request_id', '').strip()
    if not request_id:
        request_id = _generate_request_id()
    else:
        existing = db.execute(
            "SELECT id FROM recipient_requests WHERE request_id = ?", (request_id,)
        ).fetchone()
        if existing:
            raise ValueError(f"Request ID '{request_id}' already exists.")

    requested_at = data.get('requested_at', datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))

    min_shelf = 0
    if 'min_shelf_life_hours' in data:
        try:
            min_shelf = float(data['min_shelf_life_hours'])
        except (TypeError, ValueError):
            min_shelf = 0

    db.execute(
        """INSERT INTO recipient_requests
           (request_id, organization_name, food_category, requested_quantity,
            quantity_unit, min_shelf_life_hours, requested_at, status,
            fulfilled_quantity, recipient_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            request_id,
            data['organization_name'].strip(),
            data['food_category'],
            float(data['requested_quantity']),
            data['quantity_unit'].strip(),
            min_shelf,
            requested_at,
            'pending',
            0,
            data.get('recipient_id'),
        ),
    )
    db.commit()
    return get_request_by_id(request_id)


def update_request(request_id, data):
    """Update an existing recipient request.

    Args:
        request_id: The text-based request identifier.
        data: Dictionary with fields to update.

    Returns:
        dict: The updated request dictionary.

    Raises:
        ValueError: If validation fails or request not found.
    """
    existing = get_request_by_id(request_id)
    if existing is None:
        raise ValueError(f"Request '{request_id}' not found.")

    is_valid, errors = _validate_request_data(data, is_update=True)
    if not is_valid:
        raise ValueError('; '.join(errors))

    db = get_db()
    updatable_fields = [
        'organization_name', 'food_category', 'requested_quantity',
        'quantity_unit', 'min_shelf_life_hours', 'status', 'fulfilled_quantity'
    ]

    set_clauses = []
    params = []
    for field in updatable_fields:
        if field in data:
            set_clauses.append(f"{field} = ?")
            value = data[field]
            if field in ('requested_quantity', 'fulfilled_quantity', 'min_shelf_life_hours'):
                value = float(value)
            elif isinstance(value, str):
                value = value.strip()
            params.append(value)

    if not set_clauses:
        return existing

    params.append(request_id)
    db.execute(
        f"UPDATE recipient_requests SET {', '.join(set_clauses)} WHERE request_id = ?",
        params,
    )
    db.commit()
    return get_request_by_id(request_id)


def cancel_request(request_id):
    """Cancel a recipient request.

    Args:
        request_id: The text-based request identifier.

    Returns:
        bool: True if cancelled, False if not found.
    """
    db = get_db()
    result = db.execute(
        "UPDATE recipient_requests SET status = 'cancelled' WHERE request_id = ? AND status NOT IN ('fulfilled', 'cancelled')",
        (request_id,),
    )
    db.commit()
    return result.rowcount > 0


def get_requests_by_category(category):
    """Retrieve all requests for a specific food category.

    Args:
        category: Food category string.

    Returns:
        list: List of request dictionaries.
    """
    db = get_db()
    rows = db.execute(
        "SELECT * FROM recipient_requests WHERE food_category = ? ORDER BY requested_at DESC",
        (category,),
    ).fetchall()
    return _rows_to_list(rows)


def get_pending_requests_by_category(category):
    """Retrieve pending requests for a category, ordered by request time (FIFO).

    Args:
        category: Food category string.

    Returns:
        list: List of pending request dictionaries, oldest first.
    """
    db = get_db()
    rows = db.execute(
        """SELECT * FROM recipient_requests
           WHERE food_category = ? AND status IN ('pending', 'partially_fulfilled')
           ORDER BY requested_at ASC""",
        (category,),
    ).fetchall()
    return _rows_to_list(rows)
