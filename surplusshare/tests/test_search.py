"""
tests/test_search.py — Unit Tests for Linear and Binary Search

Tests:
- Linear Search sequential filtering correctness
- Binary Search lower bound and upper bound boundary conditions
- Range query window retrieval
- Algorithmic result equivalence between Linear and Binary Search
- Edge cases: window outside data range, empty dataset, single element
"""

import pytest
from datetime import datetime, timedelta
from algorithms.linear_search import linear_search, linear_search_by_name
from algorithms.binary_search import (
    binary_search_lower_bound,
    binary_search_upper_bound,
    binary_search_expiry_window,
)
from algorithms.merge_sort import sort_by_expiry


@pytest.fixture
def sample_sorted_listings():
    items = [
        {'listing_id': 'FL-001', 'food_name': 'Milk', 'category': 'Dairy', 'quantity': 10, 'expiry_at': '2026-01-01T12:00:00', 'status': 'available'},
        {'listing_id': 'FL-002', 'food_name': 'Pandesal', 'category': 'Bakery', 'quantity': 50, 'expiry_at': '2026-01-02T08:00:00', 'status': 'available'},
        {'listing_id': 'FL-003', 'food_name': 'Cheese', 'category': 'Dairy', 'quantity': 15, 'expiry_at': '2026-01-03T10:00:00', 'status': 'available'},
        {'listing_id': 'FL-004', 'food_name': 'Kangkong', 'category': 'Vegetables', 'quantity': 25, 'expiry_at': '2026-01-04T18:00:00', 'status': 'available'},
        {'listing_id': 'FL-005', 'food_name': 'Apples', 'category': 'Fruits', 'quantity': 30, 'expiry_at': '2026-01-05T12:00:00', 'status': 'available'},
    ]
    return sort_by_expiry(items)


def test_binary_search_bounds(sample_sorted_listings):
    # Lower bound for 2026-01-02T00:00:00 -> should land on index 1 (FL-002)
    lb, _ = binary_search_lower_bound(sample_sorted_listings, '2026-01-02T00:00:00')
    assert lb == 1

    # Upper bound for 2026-01-04T23:59:59 -> elements at index 1, 2, 3 are <= target; upper bound index is 4
    ub, _ = binary_search_upper_bound(sample_sorted_listings, '2026-01-04T23:59:59')
    assert ub == 4

    # Target before all elements
    lb_early, _ = binary_search_lower_bound(sample_sorted_listings, '2025-12-01T00:00:00')
    assert lb_early == 0

    # Target after all elements
    ub_late, _ = binary_search_upper_bound(sample_sorted_listings, '2026-12-31T00:00:00')
    assert ub_late == len(sample_sorted_listings)


def test_linear_and_binary_equivalence(sample_sorted_listings):
    """
    Core DSA requirement: Verify that Linear Search and Binary Search
    return the exact same set of matching listings for any query interval.
    """
    start_dt = '2026-01-02T00:00:00'
    end_dt = '2026-01-04T23:59:59'

    linear_res = linear_search(sample_sorted_listings, start_dt, end_dt)
    binary_res = binary_search_expiry_window(sample_sorted_listings, start_dt, end_dt)

    linear_ids = sorted([r['listing_id'] for r in linear_res['results']])
    binary_ids = sorted([r['listing_id'] for r in binary_res['results']])

    # Both must identify FL-002, FL-003, FL-004
    assert linear_ids == ['FL-002', 'FL-003', 'FL-004']
    assert binary_ids == ['FL-002', 'FL-003', 'FL-004']
    assert linear_ids == binary_ids


def test_secondary_filters(sample_sorted_listings):
    start_dt = '2026-01-01T00:00:00'
    end_dt = '2026-01-06T00:00:00'

    # Filter by category = 'Dairy'
    linear_res = linear_search(sample_sorted_listings, start_dt, end_dt, category='Dairy')
    binary_res = binary_search_expiry_window(sample_sorted_listings, start_dt, end_dt, category='Dairy')

    linear_ids = [r['listing_id'] for r in linear_res['results']]
    binary_ids = [r['listing_id'] for r in binary_res['results']]

    assert linear_ids == ['FL-001', 'FL-003']
    assert binary_ids == ['FL-001', 'FL-003']


def test_linear_search_by_name(sample_sorted_listings):
    res = linear_search_by_name(sample_sorted_listings, 'pan')
    assert len(res['results']) == 1
    assert res['results'][0]['listing_id'] == 'FL-002'

    # Case insensitivity
    res_caps = linear_search_by_name(sample_sorted_listings, 'PANDESAL')
    assert len(res_caps['results']) == 1
    assert res_caps['results'][0]['listing_id'] == 'FL-002'
