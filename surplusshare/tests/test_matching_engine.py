"""
tests/test_matching_engine.py — Unit Tests for Automatic Matching Engine

Tests:
- Integration of Merge Sort + FIFO Queue + Expiry Checks
- Soonest-expiring food matched first
- Fairness in request fulfillment
- Shelf life constraint compliance (min_shelf_life_hours)
- Prevention of double allocation (conservation of food quantity)
- Deterministic output
- Exclusion of expired food
"""

import pytest
from datetime import datetime, timedelta
from algorithms.matching_engine import MatchingEngine


def test_matching_engine_basic_flow():
    engine = MatchingEngine()

    now = datetime(2026, 1, 1, 10, 0, 0)

    # 2 food listings with different expiries
    listings = [
        {
            'id': 1,
            'listing_id': 'FL-001',
            'food_name': 'Bananas',
            'category': 'Fruits',
            'quantity': 50.0,
            'allocated_quantity': 0.0,
            'unit': 'kg',
            'donor_name': 'Fresh Market',
            'pickup_location': '123 Market St',
            'expiry_at': (now + timedelta(hours=48)).isoformat(),  # 2 days
            'status': 'available',
        },
        {
            'id': 2,
            'listing_id': 'FL-002',
            'food_name': 'Ripe Bananas',
            'category': 'Fruits',
            'quantity': 30.0,
            'allocated_quantity': 0.0,
            'unit': 'kg',
            'donor_name': 'Sunrise Grocery',
            'pickup_location': '456 Grocery Ave',
            'expiry_at': (now + timedelta(hours=8)).isoformat(),  # 8 hours (sooner!)
            'status': 'available',
        },
    ]

    # 1 recipient request needing 40 kg
    requests = [
        {
            'id': 101,
            'request_id': 'RR-001',
            'organization_name': 'Community Pantry',
            'food_category': 'Fruits',
            'requested_quantity': 40.0,
            'fulfilled_quantity': 0.0,
            'quantity_unit': 'kg',
            'min_shelf_life_hours': 4.0,
            'requested_at': (now - timedelta(hours=2)).isoformat(),
            'status': 'pending',
        }
    ]

    result = engine.run_matching(listings, requests, current_time=now)
    allocations = result['allocations']

    # The soonest-expiring item (FL-002, 8 hrs left) MUST be matched first by Merge Sort!
    assert len(allocations) == 2
    # Allocation 1: FL-002 yields 30 kg to RR-001
    assert allocations[0]['listing_id'] == 'FL-002'
    assert allocations[0]['allocated_quantity'] == 30.0

    # Allocation 2: FL-001 yields remaining 10 kg to RR-001
    assert allocations[1]['listing_id'] == 'FL-001'
    assert allocations[1]['allocated_quantity'] == 10.0

    # Total allocated to RR-001 is exactly 40 kg
    total_to_pantry = sum(a['allocated_quantity'] for a in allocations if a['request_id'] == 'RR-001')
    assert total_to_pantry == 40.0


def test_shelf_life_constraint_rejection():
    engine = MatchingEngine()
    now = datetime(2026, 1, 1, 10, 0, 0)

    # Food expires in 5 hours
    listings = [
        {
            'id': 1,
            'listing_id': 'FL-010',
            'food_name': 'Yogurt',
            'category': 'Dairy',
            'quantity': 20.0,
            'allocated_quantity': 0.0,
            'unit': 'packs',
            'donor_name': 'Dairy Store',
            'expiry_at': (now + timedelta(hours=5)).isoformat(),
            'status': 'available',
        }
    ]

    # Recipient requires AT LEAST 12 hours shelf life
    requests = [
        {
            'id': 201,
            'request_id': 'RR-010',
            'organization_name': 'Distant Shelter',
            'food_category': 'Dairy',
            'requested_quantity': 20.0,
            'fulfilled_quantity': 0.0,
            'quantity_unit': 'packs',
            'min_shelf_life_hours': 12.0,  # 12 > 5 -> should reject!
            'requested_at': now.isoformat(),
            'status': 'pending',
        }
    ]

    result = engine.run_matching(listings, requests, current_time=now)
    assert len(result['allocations']) == 0
    assert len(result['unmatched_listings']) == 1


def test_no_double_allocation():
    """Ensure that available surplus can never be allocated more than once."""
    engine = MatchingEngine()
    now = datetime(2026, 1, 1, 10, 0, 0)

    listings = [
        {
            'id': 1,
            'listing_id': 'FL-100',
            'food_name': 'Bread',
            'category': 'Bakery',
            'quantity': 25.0,
            'allocated_quantity': 0.0,
            'unit': 'pieces',
            'expiry_at': (now + timedelta(hours=24)).isoformat(),
            'status': 'available',
        }
    ]

    requests = [
        {'id': 1, 'request_id': 'RR-A', 'organization_name': 'Org A', 'food_category': 'Bakery', 'requested_quantity': 20.0, 'fulfilled_quantity': 0, 'quantity_unit': 'pieces', 'requested_at': '2026-01-01T08:00:00'},
        {'id': 2, 'request_id': 'RR-B', 'organization_name': 'Org B', 'food_category': 'Bakery', 'requested_quantity': 20.0, 'fulfilled_quantity': 0, 'quantity_unit': 'pieces', 'requested_at': '2026-01-01T09:00:00'},
    ]

    result = engine.run_matching(listings, requests, current_time=now)
    allocations = result['allocations']

    total_allocated = sum(a['allocated_quantity'] for a in allocations)
    assert total_allocated == 25.0  # Cannot exceed total quantity of 25!
    assert len(allocations) == 2
    assert allocations[0]['allocated_quantity'] == 20.0  # Org A gets 20
    assert allocations[1]['allocated_quantity'] == 5.0   # Org B gets remainder 5


def test_expired_listings_automatically_excluded():
    """Listings whose expiry timestamp is in the past must never be matched."""
    engine = MatchingEngine()
    now = datetime(2026, 1, 1, 10, 0, 0)

    listings = [
        {
            'id': 1,
            'listing_id': 'FL-EXPIRED',
            'food_name': 'Spoiled Milk',
            'category': 'Dairy',
            'quantity': 10.0,
            'allocated_quantity': 0.0,
            'unit': 'liters',
            'expiry_at': (now - timedelta(hours=2)).isoformat(),  # 2 hours expired!
            'status': 'available',
        }
    ]

    requests = [
        {
            'id': 1,
            'request_id': 'RR-DAIRY',
            'organization_name': 'Shelter',
            'food_category': 'Dairy',
            'requested_quantity': 10.0,
            'fulfilled_quantity': 0.0,
            'quantity_unit': 'liters',
            'requested_at': now.isoformat(),
            'status': 'pending',
        }
    ]

    result = engine.run_matching(listings, requests, current_time=now)
    assert len(result['allocations']) == 0
    assert result['stats']['listings_evaluated'] == 0
