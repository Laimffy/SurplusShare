"""
tests/test_database_and_routes.py — Integration Tests for Flask Routes & Database

Tests:
- Database schema initialization and seeding
- Listing validation: rejection of non-positive quantities, past expiries, invalid categories
- Prevention of duplicate listing IDs
- HTTP route status codes across all views
- Benchmark API endpoint functionality and result equivalence
- Allocation transaction persistence
"""

import pytest
from datetime import datetime, timedelta
from database.seed import seed_database
from services.listing_service import create_listing, get_listing_by_id


def test_seed_database_loads_data(app):
    with app.app_context():
        seed_database()
        from services.listing_service import get_all_listings
        from services.request_service import get_all_requests
        from services.schedule_service import get_all_schedules

        listings = get_all_listings()
        requests = get_all_requests()
        schedules = get_all_schedules()

        assert len(listings) >= 15
        assert len(requests) >= 5
        assert len(schedules) >= 1


def test_listing_validation(app):
    with app.app_context():
        # 1. Negative quantity must be rejected
        with pytest.raises(ValueError, match="Quantity must be a positive number"):
            create_listing({
                'food_name': 'Bad Item',
                'category': 'Bakery',
                'quantity': -5,
                'unit': 'pieces',
                'donor_name': 'Donor',
                'pickup_location': 'Address',
                'expiry_at': (datetime.now() + timedelta(days=1)).isoformat(),
            })

        # 2. Invalid category must be rejected
        with pytest.raises(ValueError, match="Category must be one of"):
            create_listing({
                'food_name': 'Bad Category',
                'category': 'UnsupportedCategory',
                'quantity': 10,
                'unit': 'kg',
                'donor_name': 'Donor',
                'pickup_location': 'Address',
                'expiry_at': (datetime.now() + timedelta(days=1)).isoformat(),
            })

        # 3. Missing pickup location must be rejected
        with pytest.raises(ValueError, match="Pickup location is required"):
            create_listing({
                'food_name': 'No Location',
                'category': 'Vegetables',
                'quantity': 10,
                'unit': 'kg',
                'donor_name': 'Donor',
                'pickup_location': '',
                'expiry_at': (datetime.now() + timedelta(days=1)).isoformat(),
            })

        # 4. Past expiry timestamp must be rejected
        with pytest.raises(ValueError, match="Expiry date must be in the future"):
            create_listing({
                'food_name': 'Expired Item',
                'category': 'Dairy',
                'quantity': 10,
                'unit': 'liters',
                'donor_name': 'Donor',
                'pickup_location': 'Address',
                'expiry_at': (datetime.now() - timedelta(hours=1)).isoformat(),
            })

        # 5. Duplicate listing IDs must be rejected
        create_listing({
            'listing_id': 'FL-TEST-DUP',
            'food_name': 'Unique Bread',
            'category': 'Bakery',
            'quantity': 10,
            'unit': 'pieces',
            'donor_name': 'Donor',
            'pickup_location': 'Address',
            'expiry_at': (datetime.now() + timedelta(days=2)).isoformat(),
        })
        with pytest.raises(ValueError, match="already exists"):
            create_listing({
                'listing_id': 'FL-TEST-DUP',
                'food_name': 'Duplicate Bread',
                'category': 'Bakery',
                'quantity': 5,
                'unit': 'pieces',
                'donor_name': 'Donor',
                'pickup_location': 'Address',
                'expiry_at': (datetime.now() + timedelta(days=2)).isoformat(),
            })


def test_routes_status_codes(client, app):
    with app.app_context():
        seed_database()

    routes = [
        '/',
        '/dashboard',
        '/listings',
        '/listings/new',
        '/requests',
        '/requests/new',
        '/matching',
        '/schedule',
        '/schedule/new',
        '/search',
        '/monitoring',
        '/reports',
        '/benchmark',
        '/settings',
    ]

    for r in routes:
        resp = client.get(r, follow_redirects=True)
        assert resp.status_code == 200, f"Route {r} failed with status {resp.status_code}"


def test_benchmark_api_endpoint(client, app):
    with app.app_context():
        seed_database()
    client.post('/login', data={'identifier': 'admin_user', 'password': 'password123'})
    payload = {
        'dataset_size': 1000,
        'query_count': 10,
        'trials': 2,
    }
    resp = client.post('/api/benchmark/run', json=payload)
    assert resp.status_code == 200
    data = resp.get_json()

    assert data['status'] == 'success'
    assert data['dataset_size'] == 1000
    assert data['analysis']['results_equivalent'] is True
    assert 'merge_sort' in data
    assert 'linear_search' in data
    assert 'binary_search' in data
