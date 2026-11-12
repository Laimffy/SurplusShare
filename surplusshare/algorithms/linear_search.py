"""
linear_search.py — Linear Search for Food Listings (SurplusShare)

DSA Concept: Sequential / Linear Search
========================================
Linear search examines every element in the collection one by one, checking
each against the search criteria. It is the simplest search algorithm and
works on UNSORTED data — no pre-processing or indexing required.

When to use Linear Search:
- Data is unsorted or cannot easily be sorted
- Multiple filter criteria need to be checked simultaneously
- Dataset is small enough that O(n) is acceptable
- One-off searches where building an index isn't worthwhile

Comparison with Binary Search:
- Linear Search:  O(n) per query,  works on unsorted data
- Binary Search:  O(log n) per query, REQUIRES sorted data + O(n log n) sort

For SurplusShare, linear search is used for:
- Name-based substring searches (can't binary-search substrings)
- Multi-criteria filtering on unsorted data
- Baseline comparison to demonstrate binary search's advantage

Complexity Summary:
    linear_search:         O(n) time, O(k) space  (k = matches)
    linear_search_by_name: O(n * m) time  (m = avg name length for substring)

Author: SurplusShare DSA Final Project
"""

import time
from datetime import datetime


def _parse_datetime(dt_value):
    """
    Parse a datetime value from various formats into a comparable datetime.

    Handles:
    - datetime objects (returned as-is)
    - ISO-8601 strings (with or without timezone, with 'Z' suffix)
    - Empty/None (returns None)

    Args:
        dt_value: A datetime object, ISO string, or None.

    Returns:
        datetime or None: Parsed datetime, or None if unparseable.

    Time Complexity: O(1) — string parsing is constant-time for fixed formats
    """
    if dt_value is None:
        return None

    # Already a datetime object
    if isinstance(dt_value, datetime):
        return dt_value

    # Convert to string and handle ISO format
    dt_str = str(dt_value).strip()
    if not dt_str:
        return None

    # Replace 'Z' (Zulu time) with '+00:00' for Python's fromisoformat
    dt_str = dt_str.replace('Z', '+00:00')

    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def linear_search(listings, expiry_start, expiry_end,
                  category=None, min_quantity=None,
                  status=None):
    """
    Linear Search — scan every listing to find matches in an expiry window.

    DSA Concept: Sequential / Linear Search
    ========================================
    This function iterates through EVERY element in the listings list,
    checking each one against ALL specified criteria. There is no early
    termination optimization (except skipping to the next element once
    a criterion fails) — every listing is visited.

    Algorithm:
        FOR each listing in listings:           ← O(n) iterations
            IF listing matches ALL criteria:     ← O(1) per check
                Add to results                   ← O(1) amortized
        RETURN results

    Filter Criteria (ALL must match):
        1. expiry_at is within [expiry_start, expiry_end]
        2. category matches (if specified)
        3. quantity >= min_quantity (if specified)
        4. status matches (if specified; defaults to 'available')

    Args:
        listings (list[dict]): List of food listing dicts. Can be unsorted.
            Each dict should have: 'expiry_at', 'category', 'quantity',
            'status', and other fields.
        expiry_start (str): ISO-8601 datetime string — start of expiry window.
        expiry_end (str): ISO-8601 datetime string — end of expiry window.
        category (str or None): Optional category filter (case-insensitive).
        min_quantity (float or None): Optional minimum quantity filter.
        status (str or None): Optional status filter. If None, defaults to
                              'available'.

    Returns:
        dict: {
            'results': list[dict]      — Matching listings
            'comparisons': int         — Total comparisons performed
            'time_ms': float           — Execution time in milliseconds
            'algorithm': 'Linear Search'
            'complexity': 'O(n)'
            'total_scanned': int       — Total listings scanned
            'matches_found': int       — Number of matches
        }

    Time Complexity:  O(n) where n = len(listings)
    Space Complexity: O(k) where k = number of matching listings
    """
    # --- Start timing ---
    start_time = time.perf_counter()

    # --- Parse the expiry window boundaries ---
    window_start = _parse_datetime(expiry_start)
    window_end = _parse_datetime(expiry_end)

    # --- Normalize optional filters ---
    if category is not None:
        category = category.lower().strip()

    # Default status filter: only show available listings
    if status is None:
        status = 'available'

    # --- Initialize counters and results ---
    results = []
    comparisons = 0  # Count every comparison for educational purposes

    # =====================================================================
    # LINEAR SEARCH: Visit every listing, one by one
    # =====================================================================
    for listing in listings:
        # --- Comparison 1: Status check ---
        comparisons += 1
        listing_status = listing.get('status', '')
        if listing_status != status:
            # This listing's status doesn't match — skip to next
            continue

        # --- Comparison 2: Parse and check expiry_at ---
        listing_expiry = _parse_datetime(listing.get('expiry_at'))
        comparisons += 1
        if listing_expiry is None:
            # Can't compare — skip listings without valid expiry
            continue

        # --- Comparison 3: Check lower bound (expiry >= window_start) ---
        comparisons += 1
        if window_start is not None and listing_expiry < window_start:
            # Expires before our window — not a match
            continue

        # --- Comparison 4: Check upper bound (expiry <= window_end) ---
        comparisons += 1
        if window_end is not None and listing_expiry > window_end:
            # Expires after our window — not a match
            continue

        # --- Comparison 5: Category filter (optional) ---
        if category is not None:
            comparisons += 1
            listing_category = listing.get('category', '').lower().strip()
            if listing_category != category:
                # Category doesn't match — skip
                continue

        # --- Comparison 6: Minimum quantity filter (optional) ---
        if min_quantity is not None:
            comparisons += 1
            try:
                listing_qty = float(listing.get('quantity', 0))
            except (ValueError, TypeError):
                listing_qty = 0.0
            if listing_qty < float(min_quantity):
                # Quantity too small — skip
                continue

        # --- All criteria passed: this listing is a match! ---
        results.append(listing)

    # --- Stop timing ---
    end_time = time.perf_counter()
    elapsed_ms = (end_time - start_time) * 1000.0

    # --- Return results with statistics ---
    return {
        'results': results,
        'comparisons': comparisons,
        'time_ms': round(elapsed_ms, 4),
        'algorithm': 'Linear Search',
        'complexity': 'O(n)',
        'total_scanned': len(listings),
        'matches_found': len(results),
    }


def linear_search_by_name(listings, search_term):
    """
    Search listings by food name using case-insensitive substring matching.

    This cannot be done with binary search because substring matching
    doesn't have a natural sort order. Linear search is the appropriate
    algorithm here.

    Algorithm:
        Normalize search_term to lowercase.
        FOR each listing in listings:
            Normalize the listing's food_name to lowercase.
            IF search_term is a substring of food_name:
                Add to results.

    Args:
        listings (list[dict]): Food listing dicts with 'food_name' field.
        search_term (str): Substring to search for (case-insensitive).

    Returns:
        dict: {
            'results': list[dict]     — Matching listings
            'comparisons': int        — Total comparisons
            'time_ms': float          — Execution time in milliseconds
            'algorithm': 'Linear Search (Name)'
            'complexity': 'O(n * m)'
            'search_term': str        — The normalized search term
            'total_scanned': int
            'matches_found': int
        }

    Time Complexity:  O(n * m) where n = listings, m = avg name length
                      (substring search within each name is O(m))
    Space Complexity: O(k) where k = number of matches
    """
    # --- Start timing ---
    start_time = time.perf_counter()

    # --- Normalize search term ---
    search_lower = search_term.lower().strip()

    # --- Initialize ---
    results = []
    comparisons = 0

    # =====================================================================
    # LINEAR SEARCH: Check every listing's name for the substring
    # =====================================================================
    for listing in listings:
        comparisons += 1

        # Get the food name and normalize to lowercase
        food_name = listing.get('food_name', '')
        if food_name is None:
            food_name = ''
        food_name_lower = food_name.lower()

        # --- Substring check ---
        # Python's `in` operator performs a substring search, which is
        # O(m) where m = length of food_name_lower. This cannot be
        # optimized with binary search.
        if search_lower in food_name_lower:
            results.append(listing)

    # --- Stop timing ---
    end_time = time.perf_counter()
    elapsed_ms = (end_time - start_time) * 1000.0

    return {
        'results': results,
        'comparisons': comparisons,
        'time_ms': round(elapsed_ms, 4),
        'algorithm': 'Linear Search (Name)',
        'complexity': 'O(n * m)',
        'search_term': search_lower,
        'total_scanned': len(listings),
        'matches_found': len(results),
    }
