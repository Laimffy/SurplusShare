"""Service functions for allocation operations."""

from datetime import datetime
from database.db import get_db


ALLOWED_STATUSES = ['pending', 'picked_up', 'delivered', 'confirmed', 'cancelled']


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


def _generate_allocation_id():
    """Generate the next allocation ID in AL-XXX pattern.

    Returns:
        str: A unique allocation ID like 'AL-003'.
    """
    db = get_db()
    row = db.execute(
        "SELECT allocation_id FROM allocations ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return 'AL-001'
    last_id = row['allocation_id']
    try:
        num = int(last_id.split('-')[1]) + 1
    except (IndexError, ValueError):
        num = 1
    return f'AL-{num:03d}'


def get_all_allocations():
    """Retrieve all allocations with listing and request details.

    Returns:
        list: List of allocation dictionaries with joined information.
    """
    db = get_db()
    rows = db.execute(
        """SELECT a.*,
                  fl.listing_id AS listing_text_id,
                  fl.food_name,
                  fl.category,
                  fl.donor_name,
                  rr.request_id AS request_text_id,
                  rr.organization_name
           FROM allocations a
           LEFT JOIN food_listings fl ON a.listing_id = fl.id
           LEFT JOIN recipient_requests rr ON a.request_id = rr.id
           ORDER BY a.allocated_at DESC"""
    ).fetchall()
    return _rows_to_list(rows)


def create_allocation(listing_pk, request_pk, quantity):
    """Create a new allocation linking a listing to a request.

    Args:
        listing_pk: Integer primary key of the food listing.
        request_pk: Integer primary key of the recipient request.
        quantity: Quantity to allocate (must be positive).

    Returns:
        dict: The created allocation dictionary.

    Raises:
        ValueError: If validation fails or referenced records not found.
    """
    db = get_db()

    quantity = float(quantity)
    if quantity <= 0:
        raise ValueError('Allocation quantity must be positive.')

    listing = db.execute(
        "SELECT * FROM food_listings WHERE id = ?", (listing_pk,)
    ).fetchone()
    if listing is None:
        raise ValueError(f"Listing with pk={listing_pk} not found.")

    request = db.execute(
        "SELECT * FROM recipient_requests WHERE id = ?", (request_pk,)
    ).fetchone()
    if request is None:
        raise ValueError(f"Request with pk={request_pk} not found.")

    available_qty = listing['quantity'] - listing['allocated_quantity']
    if quantity > available_qty:
        raise ValueError(
            f"Cannot allocate {quantity}. Only {available_qty} available from this listing."
        )

    allocation_id = _generate_allocation_id()
    allocated_at = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    db.execute(
        """INSERT INTO allocations
           (allocation_id, listing_id, request_id, allocated_quantity, allocated_at, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (allocation_id, listing_pk, request_pk, quantity, allocated_at, 'pending'),
    )

    new_alloc_qty = listing['allocated_quantity'] + quantity
    if new_alloc_qty >= listing['quantity']:
        new_status = 'fully_allocated'
    else:
        new_status = 'partially_allocated'

    db.execute(
        "UPDATE food_listings SET allocated_quantity = ?, status = ? WHERE id = ?",
        (new_alloc_qty, new_status, listing_pk),
    )

    new_fulfilled = request['fulfilled_quantity'] + quantity
    if new_fulfilled >= request['requested_quantity']:
        req_status = 'fulfilled'
    else:
        req_status = 'partially_fulfilled'

    db.execute(
        "UPDATE recipient_requests SET fulfilled_quantity = ?, status = ? WHERE id = ?",
        (new_fulfilled, req_status, request_pk),
    )

    db.commit()

    row = db.execute(
        "SELECT * FROM allocations WHERE allocation_id = ?", (allocation_id,)
    ).fetchone()
    return _row_to_dict(row)


def update_allocation_status(allocation_id, status):
    """Update the status of an allocation.

    Args:
        allocation_id: The text-based allocation identifier (e.g., 'AL-001').
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
        "UPDATE allocations SET status = ? WHERE allocation_id = ?",
        (status, allocation_id),
    )
    db.commit()
    return result.rowcount > 0


def get_allocations_for_listing(listing_pk):
    """Retrieve all allocations for a specific listing.

    Args:
        listing_pk: Integer primary key of the food listing.

    Returns:
        list: List of allocation dictionaries.
    """
    db = get_db()
    rows = db.execute(
        """SELECT a.*, rr.request_id AS request_text_id, rr.organization_name
           FROM allocations a
           LEFT JOIN recipient_requests rr ON a.request_id = rr.id
           WHERE a.listing_id = ?
           ORDER BY a.allocated_at DESC""",
        (listing_pk,),
    ).fetchall()
    return _rows_to_list(rows)


def get_allocations_for_request(request_pk):
    """Retrieve all allocations for a specific request.

    Args:
        request_pk: Integer primary key of the recipient request.

    Returns:
        list: List of allocation dictionaries.
    """
    db = get_db()
    rows = db.execute(
        """SELECT a.*, fl.listing_id AS listing_text_id, fl.food_name,
                  fl.donor_name
           FROM allocations a
           LEFT JOIN food_listings fl ON a.listing_id = fl.id
           WHERE a.request_id = ?
           ORDER BY a.allocated_at DESC""",
        (request_pk,),
    ).fetchall()
    return _rows_to_list(rows)
