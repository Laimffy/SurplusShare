"""
binary_search.py — Binary Search on Sorted Data (SurplusShare)

DSA Concept: Binary Search
==========================
Binary search finds a target value (or range) within a SORTED list by
repeatedly dividing the search interval in half. Each comparison
eliminates half of the remaining elements, yielding O(log n) time.

PREREQUISITE: The input list MUST be sorted by the search key (expiry_at).
Use merge_sort.sort_by_expiry() to sort before calling these functions.

How it works:
    1. Start with the full range [low, high].
    2. Find the midpoint: mid = (low + high) // 2.
    3. Compare the target with arr[mid]:
       - If target <= arr[mid]: search left half [low, mid]
       - If target >  arr[mid]: search right half [mid+1, high]
    4. Repeat until low >= high. The answer is at position low.

Why Binary Search for SurplusShare?
- Food listings sorted by expiry → can find "expiring in next 24 hours"
  in O(log n) instead of O(n)
- Range queries: find all listings expiring between two dates using
  two binary searches (lower + upper bound) in O(log n + k)
- Dramatically faster than linear search on large datasets

Complexity Summary:
    binary_search_lower_bound:   O(log n) time, O(1) space
    binary_search_upper_bound:   O(log n) time, O(1) space
    binary_search_expiry_window: O(log n + k) time, O(k) space
        where k = number of results within the window

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

    Time Complexity: O(1)
    """
    if dt_value is None:
        return None

    if isinstance(dt_value, datetime):
        return dt_value

    dt_str = str(dt_value).strip()
    if not dt_str:
        return None

    dt_str = dt_str.replace('Z', '+00:00')

    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def _get_expiry_str(listing):
    """
    Extract a normalized expiry string from a listing for comparison.

    We compare as ISO strings which sort lexicographically the same as
    chronologically (a key property of ISO-8601 format).

    Args:
        listing (dict): A food listing with 'expiry_at' field.

    Returns:
        str: Normalized expiry string.

    Time Complexity: O(1)
    """
    expiry = listing.get('expiry_at', '')
    if isinstance(expiry, datetime):
        return expiry.isoformat()
    return str(expiry).replace('Z', '+00:00')


def binary_search_lower_bound(sorted_listings, target_expiry):
    """
    Find the LEFTMOST position where expiry_at >= target_expiry.

    DSA Concept: Binary Search — Lower Bound (bisect_left)
    ======================================================
    This finds the insertion point for target_expiry such that all
    elements to the LEFT have expiry_at < target_expiry. This is the
    first element that is >= the target.

    Algorithm:
        low = 0, high = len(arr)
        WHILE low < high:
            mid = (low + high) // 2
            IF arr[mid].expiry_at < target:
                low = mid + 1          ← Target is in the right half
            ELSE:
                high = mid             ← Target is in the left half (or at mid)
        RETURN low

    Visual Example:
        Sorted by expiry: [Jan 1, Jan 3, Jan 5, Jan 7, Jan 9]
        Target: Jan 4
        
        Iteration 1: low=0, high=5, mid=2 → Jan 5 >= Jan 4 → high=2
        Iteration 2: low=0, high=2, mid=1 → Jan 3 <  Jan 4 → low=2
        Result: low=2 (index of Jan 5, first element >= Jan 4)

    Args:
        sorted_listings (list[dict]): Listings PRE-SORTED by expiry_at.
        target_expiry (str): ISO-8601 datetime string to search for.

    Returns:
        tuple: (index, comparisons)
            index (int): Leftmost index where expiry_at >= target.
                         Returns len(sorted_listings) if all are smaller.
            comparisons (int): Number of comparisons performed.

    Time Complexity:  O(log n) — halves the search space each iteration
    Space Complexity: O(1) — only uses a few index variables
    """
    # --- Normalize target for comparison ---
    target = str(target_expiry).replace('Z', '+00:00')

    # --- Initialize search bounds ---
    low = 0                       # Left boundary (inclusive)
    high = len(sorted_listings)   # Right boundary (exclusive)
    comparisons = 0               # Track comparisons for analysis

    # --- Binary search loop ---
    # Each iteration halves the search space: [low, high) → [low, mid) or [mid+1, high)
    while low < high:
        # --- Find midpoint (avoids overflow in other languages) ---
        mid = (low + high) // 2

        # --- Extract the expiry at the midpoint ---
        mid_expiry = _get_expiry_str(sorted_listings[mid])
        comparisons += 1

        # --- Compare and narrow the search space ---
        if mid_expiry < target:
            # Midpoint expires BEFORE our target → search RIGHT half
            # All elements at indices [low, mid] are too early
            low = mid + 1
        else:
            # Midpoint expires AT or AFTER our target → search LEFT half
            # The answer could be at mid or earlier
            high = mid

    # --- low == high: this is the lower bound ---
    # sorted_listings[low] is the first element with expiry_at >= target
    return low, comparisons


def binary_search_upper_bound(sorted_listings, target_expiry):
    """
    Find the RIGHTMOST position where expiry_at <= target_expiry.

    DSA Concept: Binary Search — Upper Bound (bisect_right)
    ======================================================
    This finds the insertion point for target_expiry such that all
    elements to the LEFT have expiry_at <= target_expiry. The returned
    index is ONE PAST the last matching element (exclusive upper bound).

    Algorithm:
        low = 0, high = len(arr)
        WHILE low < high:
            mid = (low + high) // 2
            IF arr[mid].expiry_at <= target:
                low = mid + 1          ← Answer might be further right
            ELSE:
                high = mid             ← arr[mid] is too large
        RETURN low

    The result is an EXCLUSIVE upper bound: the range of matching
    elements is [lower_bound, upper_bound).

    Visual Example:
        Sorted by expiry: [Jan 1, Jan 3, Jan 5, Jan 7, Jan 9]
        Target: Jan 6
        
        Iteration 1: low=0, high=5, mid=2 → Jan 5 <= Jan 6 → low=3
        Iteration 2: low=3, high=5, mid=4 → Jan 9 >  Jan 6 → high=4
        Iteration 3: low=3, high=4, mid=3 → Jan 7 >  Jan 6 → high=3
        Result: low=3 (exclusive; elements [0,1,2] have expiry <= Jan 6)

    Args:
        sorted_listings (list[dict]): Listings PRE-SORTED by expiry_at.
        target_expiry (str): ISO-8601 datetime string to search for.

    Returns:
        tuple: (index, comparisons)
            index (int): Exclusive upper bound. Elements with
                         expiry_at <= target are at indices [0, index).
                         Returns 0 if all are greater.
            comparisons (int): Number of comparisons performed.

    Time Complexity:  O(log n)
    Space Complexity: O(1)
    """
    # --- Normalize target ---
    target = str(target_expiry).replace('Z', '+00:00')

    # --- Initialize search bounds ---
    low = 0
    high = len(sorted_listings)
    comparisons = 0

    # --- Binary search loop ---
    while low < high:
        mid = (low + high) // 2

        mid_expiry = _get_expiry_str(sorted_listings[mid])
        comparisons += 1

        if mid_expiry <= target:
            # Midpoint expires AT or BEFORE target → search RIGHT
            # There might be more matching elements after mid
            low = mid + 1
        else:
            # Midpoint expires AFTER target → search LEFT
            # mid is too large; the last valid element is before mid
            high = mid

    # --- low == high: exclusive upper bound ---
    # Elements at indices [0, low) have expiry_at <= target
    return low, comparisons


def binary_search_expiry_window(sorted_listings, expiry_start, expiry_end,
                                 category=None, min_quantity=None,
                                 status=None):
    """
    Binary Search with Range Query — find all listings in an expiry window.

    DSA Concept: Binary Search with Range Query
    ============================================
    Instead of scanning every listing (O(n)), we use two binary searches
    to find the START and END of the matching range in O(log n) time,
    then only scan elements within that window.

    Algorithm:
        1. Binary search for LOWER BOUND: first index where expiry >= start
           → O(log n)
        2. Binary search for UPPER BOUND: first index where expiry > end
           → O(log n)
        3. The matching range is [lower, upper)
        4. Scan only the window and apply additional filters (category, etc.)
           → O(k) where k = elements in the window

    Total: O(log n + k) vs O(n) for linear search

    Visual Example:
        100 listings sorted by expiry.
        We want listings expiring between Jan 5 and Jan 10.
        
        Binary search finds: lower=23, upper=31
        Only 8 listings need to be checked (indices 23-30)
        instead of all 100. This is a 12.5x speedup!

    IMPORTANT: sorted_listings MUST be pre-sorted by expiry_at.
    Use merge_sort.sort_by_expiry() first!

    Args:
        sorted_listings (list[dict]): Listings PRE-SORTED by expiry_at.
        expiry_start (str): ISO-8601 start of expiry window (inclusive).
        expiry_end (str): ISO-8601 end of expiry window (inclusive).
        category (str or None): Optional category filter.
        min_quantity (float or None): Optional minimum quantity filter.
        status (str or None): Status filter (default: 'available').

    Returns:
        dict: {
            'results': list[dict]         — Matching listings
            'comparisons': int            — Binary search comparisons
            'window_comparisons': int     — Filtering comparisons in window
            'total_comparisons': int      — Sum of both
            'time_ms': float              — Execution time
            'algorithm': 'Binary Search'
            'complexity': 'O(log n + k)'
            'total_scanned': int          — Total listings available
            'window_size': int            — Elements in the binary-search window
            'matches_found': int          — Final match count
            'lower_bound_index': int      — Where the window starts
            'upper_bound_index': int      — Where the window ends (exclusive)
        }

    Time Complexity:  O(log n + k) where k = window size
    Space Complexity: O(m) where m = number of final matches
    """
    # --- Start timing ---
    start_time = time.perf_counter()

    # --- Normalize optional filters ---
    if category is not None:
        category = category.lower().strip()
    if status is None:
        status = 'available'

    # --- Initialize ---
    results = []
    binary_comparisons = 0
    window_comparisons = 0

    # =====================================================================
    # STEP 1: Binary search for LOWER BOUND
    # =====================================================================
    # Find the first listing whose expiry_at >= expiry_start
    # This narrows our search from the left side
    lower_idx, lower_comps = binary_search_lower_bound(
        sorted_listings, expiry_start
    )
    binary_comparisons += lower_comps

    # =====================================================================
    # STEP 2: Binary search for UPPER BOUND
    # =====================================================================
    # Find the first listing whose expiry_at > expiry_end
    # Everything before this index has expiry_at <= expiry_end
    upper_idx, upper_comps = binary_search_upper_bound(
        sorted_listings, expiry_end
    )
    binary_comparisons += upper_comps

    # =====================================================================
    # STEP 3: Scan only the window [lower_idx, upper_idx)
    # =====================================================================
    # This is the key advantage: instead of scanning ALL n listings,
    # we only look at the k listings within our expiry window.
    window_size = upper_idx - lower_idx

    for i in range(lower_idx, upper_idx):
        listing = sorted_listings[i]

        # --- Filter by status ---
        window_comparisons += 1
        listing_status = listing.get('status', '')
        if listing_status != status:
            continue

        # --- Filter by category (optional) ---
        if category is not None:
            window_comparisons += 1
            listing_category = listing.get('category', '').lower().strip()
            if listing_category != category:
                continue

        # --- Filter by minimum quantity (optional) ---
        if min_quantity is not None:
            window_comparisons += 1
            try:
                listing_qty = float(listing.get('quantity', 0))
            except (ValueError, TypeError):
                listing_qty = 0.0
            if listing_qty < float(min_quantity):
                continue

        # --- All filters passed: add to results ---
        results.append(listing)

    # --- Stop timing ---
    end_time = time.perf_counter()
    elapsed_ms = (end_time - start_time) * 1000.0

    # --- Total comparisons = binary search + window filtering ---
    total_comparisons = binary_comparisons + window_comparisons

    return {
        'results': results,
        'comparisons': binary_comparisons,
        'window_comparisons': window_comparisons,
        'total_comparisons': total_comparisons,
        'time_ms': round(elapsed_ms, 4),
        'algorithm': 'Binary Search',
        'complexity': 'O(log n + k)',
        'total_scanned': len(sorted_listings),
        'window_size': max(0, window_size),
        'matches_found': len(results),
        'lower_bound_index': lower_idx,
        'upper_bound_index': upper_idx,
    }
