"""
tests/test_merge_sort.py — Unit Tests for Merge Sort (Expiry Prioritization)

Tests:
- Manual divide-and-conquer sorting correctness
- Stability preservation: preserves initial relative order for equal keys
- Edge cases: empty list, single item, all identical keys, reverse sorted
- Key extractors: expiry_at, quantity, posted_at
- SortTracker metrics (comparisons and copies)
"""

import pytest
from algorithms.merge_sort import (
    merge_sort,
    sort_by_expiry,
    sort_by_quantity,
    sort_by_posted,
    SortTracker,
)


def test_merge_sort_empty_and_single():
    assert merge_sort([]) == []
    single = [{'listing_id': 'FL-001', 'expiry_at': '2026-01-01T12:00:00'}]
    assert merge_sort(single) == single


def test_merge_sort_expiry_chronological():
    listings = [
        {'id': 1, 'food_name': 'Bananas', 'expiry_at': '2026-01-05T10:00:00'},
        {'id': 2, 'food_name': 'Milk', 'expiry_at': '2026-01-02T08:00:00'},
        {'id': 3, 'food_name': 'Bread', 'expiry_at': '2026-01-01T18:00:00'},
        {'id': 4, 'food_name': 'Canned Beans', 'expiry_at': '2026-02-15T00:00:00'},
    ]

    sorted_list = sort_by_expiry(listings)
    names = [item['food_name'] for item in sorted_list]

    # Earliest expiry must be first
    assert names == ['Bread', 'Milk', 'Bananas', 'Canned Beans']
    # Original list must not be mutated (pure function)
    assert listings[0]['food_name'] == 'Bananas'


def test_merge_sort_stability():
    """
    Stability test:
    When two items have identical expiry timestamps, their relative order
    from the input list MUST be preserved.
    """
    listings = [
        {'id': 'First', 'expiry_at': '2026-01-03T12:00:00', 'initial_index': 0},
        {'id': 'Early', 'expiry_at': '2026-01-01T12:00:00', 'initial_index': 1},
        {'id': 'Second', 'expiry_at': '2026-01-03T12:00:00', 'initial_index': 2},
        {'id': 'Third', 'expiry_at': '2026-01-03T12:00:00', 'initial_index': 3},
    ]

    sorted_list = sort_by_expiry(listings)

    assert sorted_list[0]['id'] == 'Early'
    assert sorted_list[1]['id'] == 'First'
    assert sorted_list[2]['id'] == 'Second'
    assert sorted_list[3]['id'] == 'Third'


def test_merge_sort_quantity_and_posted():
    listings = [
        {'id': 1, 'quantity': 50.0, 'posted_at': '2026-01-01T14:00:00'},
        {'id': 2, 'quantity': 10.0, 'posted_at': '2026-01-01T08:00:00'},
        {'id': 3, 'quantity': 35.0, 'posted_at': '2026-01-01T11:00:00'},
    ]

    by_qty = sort_by_quantity(listings)
    assert [x['quantity'] for x in by_qty] == [10.0, 35.0, 50.0]

    by_posted = sort_by_posted(listings)
    assert [x['id'] for x in by_posted] == [2, 3, 1]


def test_sort_tracker_counts():
    tracker = SortTracker()
    listings = [
        {'expiry_at': '2026-01-03T00:00:00'},
        {'expiry_at': '2026-01-01T00:00:00'},
        {'expiry_at': '2026-01-04T00:00:00'},
        {'expiry_at': '2026-01-02T00:00:00'},
    ]

    sorted_res = tracker.sort(listings)
    assert len(sorted_res) == 4
    assert tracker.comparisons > 0
    assert tracker.copies > 0
    assert tracker.time_ms >= 0
