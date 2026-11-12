"""
merge_sort.py — Merge Sort for Expiry Prioritization (SurplusShare)

DSA Concept: Merge Sort — Divide and Conquer
=============================================
Merge Sort divides the input list into two halves, recursively sorts each
half, then merges the two sorted halves into one sorted list. It is the
canonical example of the divide-and-conquer paradigm.

Why Merge Sort for food listings?
- Guaranteed O(n log n) in ALL cases (no worst-case degradation like QuickSort)
- Stable sort: preserves the relative order of listings with the same expiry
  date, so earlier-posted listings stay first among equals
- Predictable performance for real-time food allocation systems

IMPORTANT: This implementation does NOT use Python's built-in sort() or
sorted(). Every comparison and element movement is done explicitly.

Complexity Summary:
    Time:  O(n log n) — best, average, AND worst case
    Space: O(n) — auxiliary space for merging
    Stable: Yes — uses <= in merge to preserve order of equal elements

Author: SurplusShare DSA Final Project
"""

import time
from datetime import datetime


# ======================================================================
#  Sort Tracker — Educational Statistics
# ======================================================================

class SortTracker:
    """
    Wraps merge_sort to count comparisons and copy operations for
    educational display.

    This is useful for demonstrating the O(n log n) behavior: students
    can see that doubling the input roughly doubles n and adds one more
    level of recursion (log n), so the total work grows as n log n.

    Attributes:
        comparisons (int): Number of key comparisons performed.
        copies (int):      Number of element copy/move operations.
        time_ms (float):   Wall-clock time for the sort in milliseconds.

    Usage:
        tracker = SortTracker()
        sorted_list = tracker.sort(listings, key_func=lambda x: x['expiry_at'])
        print(tracker.get_stats())
    """

    def __init__(self):
        self.comparisons = 0
        self.copies = 0
        self.time_ms = 0.0
        self._key_func = None

    def sort(self, listings, key_func=None):
        """
        Sort the listings using merge sort while tracking statistics.

        Args:
            listings (list): List of items to sort.
            key_func (callable): Function to extract comparison key.

        Returns:
            list: New sorted list (original is not modified).

        Time Complexity: O(n log n)
        Space Complexity: O(n)
        """
        # --- Reset counters ---
        self.comparisons = 0
        self.copies = 0

        # --- Default key function: sort by expiry_at ---
        if key_func is None:
            key_func = lambda x: x.get('expiry_at', '')
        self._key_func = key_func

        # --- Time the sort ---
        start = time.perf_counter()

        # --- Make a shallow copy so we don't modify the original list ---
        items = list(listings)
        self.copies += len(items)  # Count the initial copy

        # --- Run the tracked merge sort ---
        result = self._merge_sort_tracked(items)

        end = time.perf_counter()
        self.time_ms = (end - start) * 1000.0

        return result

    def _merge_sort_tracked(self, arr):
        """
        Recursive merge sort with comparison/copy tracking.

        Base case: a list of length 0 or 1 is already sorted.
        Recursive case: split, sort halves, merge.

        Time Complexity: O(n log n)
        Space Complexity: O(n) auxiliary
        """
        n = len(arr)

        # --- BASE CASE ---
        # A list of 0 or 1 elements is trivially sorted
        if n <= 1:
            return arr

        # --- DIVIDE ---
        # Split the list into two approximately equal halves
        mid = n // 2
        left_half = arr[:mid]    # First half:  indices [0, mid)
        right_half = arr[mid:]   # Second half: indices [mid, n)
        self.copies += n         # Count the copy operations for splitting

        # --- CONQUER ---
        # Recursively sort each half
        left_sorted = self._merge_sort_tracked(left_half)
        right_sorted = self._merge_sort_tracked(right_half)

        # --- COMBINE ---
        # Merge the two sorted halves into one sorted list
        return self._merge_tracked(left_sorted, right_sorted)

    def _merge_tracked(self, left, right):
        """
        Merge two sorted lists into one sorted list (with tracking).

        Uses <= (not <) for stability: when elements are equal, the one
        from the LEFT list is placed first, preserving original order.

        Time Complexity: O(n) where n = len(left) + len(right)
        Space Complexity: O(n) for the merged result
        """
        merged = []
        i = 0  # Pointer into the left sublist
        j = 0  # Pointer into the right sublist

        key = self._key_func

        # --- Main merge loop ---
        # Compare the front elements of both sublists and take the smaller one
        while i < len(left) and j < len(right):
            self.comparisons += 1  # Count each comparison

            # Use <= for STABILITY: equal elements from left come first
            if key(left[i]) <= key(right[j]):
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1
            self.copies += 1  # Count each element placement

        # --- Copy remaining elements from left sublist ---
        while i < len(left):
            merged.append(left[i])
            i += 1
            self.copies += 1

        # --- Copy remaining elements from right sublist ---
        while j < len(right):
            merged.append(right[j])
            j += 1
            self.copies += 1

        return merged

    def get_stats(self):
        """
        Return a dictionary of sort statistics for display.

        Returns:
            dict: Comparisons, copies, time, and complexity info.

        Time Complexity: O(1)
        """
        return {
            'algorithm': 'Merge Sort',
            'comparisons': self.comparisons,
            'copies': self.copies,
            'time_ms': round(self.time_ms, 4),
            'complexity': 'O(n log n)',
            'space_complexity': 'O(n)',
            'stable': True,
        }


# ======================================================================
#  Core Merge Sort Implementation
# ======================================================================

def merge_sort(listings, key_func=None):
    """
    Merge Sort — manually implemented, stable sort.

    DO NOT use Python's built-in sort() or sorted(). This function
    implements every step of the merge sort algorithm explicitly.

    DSA Concept: Divide and Conquer
    ===============================
    1. DIVIDE:   Split the list into two halves at the midpoint.
    2. CONQUER:  Recursively sort each half (base case: length ≤ 1).
    3. COMBINE:  Merge the two sorted halves by comparing front elements.

    The merge step is where the real work happens: we maintain two pointers,
    one for each sorted sublist, and always pick the smaller element. This
    produces a sorted combined list in O(n) time. With log n levels of
    recursion, the total is O(n log n).

    Stability:
        When two elements have equal keys, the one from the LEFT sublist
        is placed first (using <=). Since the left sublist contains
        elements with lower original indices, relative order is preserved.

    Args:
        listings (list): List of dict objects (food listings) to sort.
        key_func (callable or None): Function to extract comparison key
            from each element. Default: extract 'expiry_at' field.

    Returns:
        list: A NEW sorted list. The original list is NOT modified.

    Time Complexity:  O(n log n) — all cases (best, average, worst)
    Space Complexity: O(n) — auxiliary space for sublists during merging
    """
    # --- Default key function: sort by expiry_at timestamp ---
    if key_func is None:
        key_func = lambda x: x.get('expiry_at', '')

    # --- Make a copy to avoid mutating the original ---
    items = list(listings)

    # --- Delegate to the recursive implementation ---
    return _merge_sort_recursive(items, key_func)


def _merge_sort_recursive(arr, key_func):
    """
    Internal recursive merge sort.

    This is separated from the public function so the key_func does
    not need to be passed or defaulted on every recursive call.

    Args:
        arr (list): The list (or sublist) to sort.
        key_func (callable): Key extraction function.

    Returns:
        list: Sorted list.

    Time Complexity: O(n log n)
    Space Complexity: O(n)
    """
    n = len(arr)

    # ================================================================
    # BASE CASE: A list of 0 or 1 elements is already sorted.
    # ================================================================
    if n <= 1:
        return arr

    # ================================================================
    # DIVIDE: Split the list into two halves.
    # ================================================================
    # We find the midpoint and create two sublists.
    # For a list of length 5: mid=2, left=[0,1], right=[2,3,4]
    mid = n // 2
    left_half = arr[:mid]
    right_half = arr[mid:]

    # ================================================================
    # CONQUER: Recursively sort each half.
    # ================================================================
    # Each recursive call handles a smaller subproblem until we reach
    # the base case of single elements.
    left_sorted = _merge_sort_recursive(left_half, key_func)
    right_sorted = _merge_sort_recursive(right_half, key_func)

    # ================================================================
    # COMBINE: Merge the two sorted halves.
    # ================================================================
    return _merge(left_sorted, right_sorted, key_func)


def _merge(left, right, key_func):
    """
    Merge two sorted sublists into one sorted list.

    This is the heart of merge sort. We maintain two pointers (i, j)
    starting at the beginning of each sublist. At each step, we compare
    the elements at the pointers and place the SMALLER one into the
    result. When one sublist is exhausted, we copy the remainder of the
    other.

    Stability: We use <= (less-than-or-equal) when comparing. If
    key(left[i]) == key(right[j]), the left element is placed first.
    Since left elements have lower original indices, this preserves
    the original relative order among equal elements.

    Args:
        left (list):  Sorted left sublist.
        right (list): Sorted right sublist.
        key_func (callable): Key extraction function.

    Returns:
        list: Merged sorted list of length len(left) + len(right).

    Time Complexity:  O(n) where n = len(left) + len(right)
    Space Complexity: O(n) for the result list
    """
    merged = []           # Result list
    i = 0                 # Pointer into left sublist
    j = 0                 # Pointer into right sublist
    len_left = len(left)
    len_right = len(right)

    # ------------------------------------------------------------------
    # Main merge loop: both sublists have remaining elements
    # ------------------------------------------------------------------
    while i < len_left and j < len_right:
        # Extract keys for comparison
        left_key = key_func(left[i])
        right_key = key_func(right[j])

        # Use <= for STABILITY:
        # If keys are equal, prefer the left element (lower original index)
        if left_key <= right_key:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1

    # ------------------------------------------------------------------
    # Copy remaining elements from the left sublist
    # ------------------------------------------------------------------
    # If the right sublist was exhausted first, all remaining left
    # elements are >= everything already in merged, so append them.
    while i < len_left:
        merged.append(left[i])
        i += 1

    # ------------------------------------------------------------------
    # Copy remaining elements from the right sublist
    # ------------------------------------------------------------------
    while j < len_right:
        merged.append(right[j])
        j += 1

    return merged


# ======================================================================
#  Convenience Sort Functions
# ======================================================================

def sort_by_expiry(listings):
    """
    Sort food listings by expiry_at timestamp (earliest expiry first).

    Food that expires soonest should be distributed first to minimize
    waste. This is the primary sort used in the matching engine.

    Args:
        listings (list[dict]): Food listings with 'expiry_at' field
                               (ISO-8601 string or datetime).

    Returns:
        list[dict]: New list sorted by expiry_at ascending.

    Time Complexity:  O(n log n)
    Space Complexity: O(n)
    """
    def expiry_key(listing):
        """Extract expiry timestamp as a comparable string."""
        expiry = listing.get('expiry_at', '')
        # If it's a datetime object, convert to ISO string for comparison
        if isinstance(expiry, datetime):
            return expiry.isoformat()
        return str(expiry)

    return merge_sort(listings, key_func=expiry_key)


def sort_by_quantity(listings):
    """
    Sort food listings by quantity (ascending — smallest first).

    Useful for finding small donations that might fill small requests,
    or for identifying the largest available quantities.

    Args:
        listings (list[dict]): Food listings with 'quantity' field.

    Returns:
        list[dict]: New list sorted by quantity ascending.

    Time Complexity:  O(n log n)
    Space Complexity: O(n)
    """
    def quantity_key(listing):
        """Extract quantity as a float for numeric comparison."""
        try:
            return float(listing.get('quantity', 0))
        except (ValueError, TypeError):
            return 0.0

    return merge_sort(listings, key_func=quantity_key)


def sort_by_posted(listings):
    """
    Sort food listings by posted_at timestamp (earliest post first).

    Older listings should be prioritized to ensure they don't get
    forgotten in favor of newer ones.

    Args:
        listings (list[dict]): Food listings with 'posted_at' field
                               (ISO-8601 string or datetime).

    Returns:
        list[dict]: New list sorted by posted_at ascending.

    Time Complexity:  O(n log n)
    Space Complexity: O(n)
    """
    def posted_key(listing):
        """Extract posted_at timestamp as a comparable string."""
        posted = listing.get('posted_at', '')
        if isinstance(posted, datetime):
            return posted.isoformat()
        return str(posted)

    return merge_sort(listings, key_func=posted_key)


# ======================================================================
#  Statistics Helper
# ======================================================================

def get_sort_stats(listings, key_func=None):
    """
    Sort listings with merge sort and return both the sorted result
    and detailed operation statistics.

    This is an educational function that shows students exactly how
    many comparisons and copies merge sort performs, confirming the
    O(n log n) theoretical analysis.

    Args:
        listings (list): Items to sort.
        key_func (callable or None): Key extraction function.

    Returns:
        tuple: (sorted_list, stats_dict)
            sorted_list: The sorted list.
            stats_dict: {
                'algorithm': 'Merge Sort',
                'comparisons': int,
                'copies': int,
                'time_ms': float,
                'input_size': int,
                'complexity': 'O(n log n)',
                'space_complexity': 'O(n)',
                'stable': True,
            }

    Time Complexity:  O(n log n)
    Space Complexity: O(n)
    """
    tracker = SortTracker()
    sorted_list = tracker.sort(listings, key_func=key_func)
    stats = tracker.get_stats()
    stats['input_size'] = len(listings)
    return sorted_list, stats
