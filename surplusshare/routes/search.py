"""
routes/search.py — Search & Sort Blueprint (SurplusShare)

Implements and benchmarks:
- Merge Sort: Manual stable divide-and-conquer sorting by expiry
- Linear Search: O(n) sequential search across all listings
- Binary Search: O(log n + k) range query on expiry-sorted listings
"""

import time
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, flash, jsonify

from database.db import get_db
from algorithms.merge_sort import merge_sort, sort_by_expiry, SortTracker
from algorithms.linear_search import linear_search, linear_search_by_name
from algorithms.binary_search import (
    binary_search_expiry_window,
    binary_search_lower_bound,
    binary_search_upper_bound,
)
from services.auth_service import login_required, get_current_user

search = Blueprint('search', __name__)


@search.route('/search', methods=['GET', 'POST'])
@login_required
def search_page():
    """
    Search and Sort demonstration page.
    
    Supports:
    - Text search by name (Linear Search)
    - Expiry window search comparing Linear vs Binary Search
    - Merge Sort before/after demonstration
    """
    db = get_db()
    raw_listings = db.execute(
        "SELECT * FROM food_listings ORDER BY id ASC"
    ).fetchall()
    all_listings = [dict(r) for r in raw_listings]

    # Pre-sort listings using Merge Sort to show before/after
    sort_tracker = SortTracker()
    sorted_by_expiry = sort_tracker.sort(
        all_listings,
        key_func=lambda x: str(x.get('expiry_at') or '')
    )

    if request.method == 'GET':
        # Default expiry window: now to 7 days in future
        now_dt = datetime.now()
        default_start = now_dt.strftime('%Y-%m-%dT%H:%M')
        default_end = (now_dt + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M')

        return render_template(
            'search.html',
            all_listings=all_listings,
            sorted_listings=sorted_by_expiry[:8],
            unsorted_sample=all_listings[:8],
            sort_stats={
                'comparisons': sort_tracker.comparisons,
                'copies': sort_tracker.copies,
                'time_ms': round(sort_tracker.time_ms, 3),
            },
            results=None,
            search_params={
                'start': default_start,
                'end': default_end,
                'category': '',
                'min_quantity': '',
                'method': 'both',
            },
        )

    # POST handling
    mode = request.form.get('search_mode', 'window')  # 'window' or 'text'
    category = request.form.get('category', '').strip()
    min_quantity = request.form.get('min_quantity', '').strip()
    min_qty_val = float(min_quantity) if min_quantity else None
    method = request.form.get('method', 'both')  # 'linear', 'binary', 'both'

    if mode == 'text':
        query = request.form.get('query', '').strip()
        linear_res = linear_search_by_name(all_listings, query)
        return render_template(
            'search.html',
            all_listings=all_listings,
            sorted_listings=sorted_by_expiry[:8],
            unsorted_sample=all_listings[:8],
            sort_stats={
                'comparisons': sort_tracker.comparisons,
                'copies': sort_tracker.copies,
                'time_ms': round(sort_tracker.time_ms, 3),
            },
            text_query=query,
            text_results=linear_res,
            results=None,
            search_params={'method': 'text'},
        )

    # Window search
    start_str = request.form.get('expiry_start', '').strip()
    end_str = request.form.get('expiry_end', '').strip()

    if not start_str or not end_str:
        flash('Please select both start and end timestamps for the expiry window.', 'warning')
        return render_template(
            'search.html',
            all_listings=all_listings,
            sorted_listings=sorted_by_expiry[:8],
            unsorted_sample=all_listings[:8],
            sort_stats={'comparisons': 0, 'copies': 0, 'time_ms': 0},
            results=None,
            search_params={'start': start_str, 'end': end_str, 'category': category, 'min_quantity': min_quantity, 'method': method},
        )

    # Execute Linear Search
    linear_output = linear_search(
        all_listings,
        expiry_start=start_str,
        expiry_end=end_str,
        category=category if category else None,
        min_quantity=min_qty_val,
        status=None,  # evaluate all matching records
    )

    # Execute Binary Search on pre-sorted listings
    binary_output = binary_search_expiry_window(
        sorted_by_expiry,
        expiry_start=start_str,
        expiry_end=end_str,
        category=category if category else None,
        min_quantity=min_qty_val,
        status=None,
    )

    # Verify algorithmic result equivalence
    linear_ids = sorted([r['listing_id'] for r in linear_output['results']])
    binary_ids = sorted([r['listing_id'] for r in binary_output['results']])
    results_equivalent = (linear_ids == binary_ids)

    comparison_data = {
        'total_listings': len(all_listings),
        'linear': linear_output,
        'binary': binary_output,
        'results_equivalent': results_equivalent,
        'matches_count': len(linear_output['results']),
        'method_selected': method,
    }

    return render_template(
        'search.html',
        all_listings=all_listings,
        sorted_listings=sorted_by_expiry[:8],
        unsorted_sample=all_listings[:8],
        sort_stats={
            'comparisons': sort_tracker.comparisons,
            'copies': sort_tracker.copies,
            'time_ms': round(sort_tracker.time_ms, 3),
        },
        results=comparison_data,
        search_params={
            'start': start_str,
            'end': end_str,
            'category': category,
            'min_quantity': min_quantity,
            'method': method,
        },
    )
