"""
routes/benchmark.py — Algorithm Benchmark Blueprint (SurplusShare)

Conducts rigorous empirical runtime benchmarks comparing:
1. Merge Sort: O(n log n) divide-and-conquer
2. Linear Search: O(n) sequential scan
3. Binary Search: O(log n + k) range query
4. Multi-query amortization & break-even threshold analysis:
   Q_break_even = T_sort / (T_linear - T_binary)
"""

import time
import random
import statistics
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify

from algorithms.merge_sort import merge_sort
from algorithms.linear_search import linear_search
from algorithms.binary_search import binary_search_expiry_window
from services.auth_service import roles_required

benchmark = Blueprint('benchmark', __name__)

CATEGORIES = ['Bakery', 'Vegetables', 'Fruits', 'Prepared Meals', 'Dairy', 'Dry Goods', 'Other']
UNITS = ['pieces', 'kg', 'liters', 'packs', 'boxes']


def _generate_synthetic_dataset(n: int, seed: int = 42) -> list:
    """
    Generate a deterministic synthetic dataset of n food listings.
    Uses a fixed random seed for 100% reproducible benchmarks.
    """
    rng = random.Random(seed)
    base_time = datetime(2026, 1, 1, 8, 0, 0)
    dataset = []

    for i in range(1, n + 1):
        # Expiry between 1 hour and 30 days into future
        expiry_offset_hours = rng.uniform(1.0, 720.0)
        expiry_dt = base_time + timedelta(hours=expiry_offset_hours)
        posted_dt = base_time - timedelta(hours=rng.uniform(0.5, 48.0))

        dataset.append({
            'listing_id': f"SYN-{i:06d}",
            'food_name': f"Synthetic Food Item {i}",
            'category': rng.choice(CATEGORIES),
            'quantity': round(rng.uniform(1.0, 100.0), 1),
            'unit': rng.choice(UNITS),
            'donor_name': f"Donor {rng.randint(1, 50)}",
            'posted_at': posted_dt.isoformat(),
            'expiry_at': expiry_dt.isoformat(),
            'pickup_location': f"Location {rng.randint(1, 20)}",
            'status': 'available',
            'allocated_quantity': 0.0,
        })

    return dataset


def _generate_synthetic_queries(num_queries: int, seed: int = 999) -> list:
    """Generate realistic expiry window query intervals."""
    rng = random.Random(seed)
    base_time = datetime(2026, 1, 1, 8, 0, 0)
    queries = []

    for _ in range(num_queries):
        start_offset = rng.uniform(10.0, 500.0)
        window_width = rng.uniform(6.0, 72.0)  # 6 to 72 hour windows
        start_dt = base_time + timedelta(hours=start_offset)
        end_dt = start_dt + timedelta(hours=window_width)

        queries.append((start_dt.isoformat(), end_dt.isoformat()))

    return queries


@benchmark.route('/benchmark')
@roles_required('admin')
def benchmark_page():
    """Render the educational algorithm benchmark dashboard."""
    return render_template('benchmark.html')


@benchmark.route('/api/benchmark/run', methods=['POST'])
@roles_required('admin')
def run_benchmark():
    """
    Execute benchmark trial across selected dataset size and query count.

    POST payload (JSON or Form):
    - dataset_size: int (e.g. 1000, 10000, 50000)
    - query_count: int (e.g. 1, 100, 1000)
    - trials: int (default: 3)
    """
    data = request.get_json(silent=True) or request.form

    dataset_size = int(data.get('dataset_size', 1000))
    query_count = int(data.get('query_count', 100))
    num_trials = min(int(data.get('trials', 3)), 5)

    # Cap dataset size for responsive web requests
    if dataset_size > 50000:
        dataset_size = 50000
    if query_count > 1000:
        query_count = 1000

    # 1. Generate Dataset & Queries
    dataset = _generate_synthetic_dataset(dataset_size)
    queries = _generate_synthetic_queries(query_count)

    # 2. Benchmark Merge Sort across trials
    sort_times_ms = []
    sorted_dataset = None
    for trial_idx in range(num_trials):
        data_copy = list(dataset)
        t0 = time.perf_counter()
        sorted_dataset = merge_sort(
            data_copy,
            key_func=lambda x: str(x.get('expiry_at') or '')
        )
        t1 = time.perf_counter()
        sort_times_ms.append((t1 - t0) * 1000.0)

    median_sort_time_ms = round(statistics.median(sort_times_ms), 3)

    # 3. Benchmark Linear Search for Q queries
    linear_times_ms = []
    linear_matches_total = 0
    sample_linear_result_ids = []

    for trial_idx in range(num_trials):
        t0 = time.perf_counter()
        total_matches = 0
        for start_dt, end_dt in queries:
            res = linear_search(dataset, start_dt, end_dt)
            total_matches += len(res['results'])
            if trial_idx == 0 and not sample_linear_result_ids:
                sample_linear_result_ids = [r['listing_id'] for r in res['results']]
        t1 = time.perf_counter()
        linear_times_ms.append((t1 - t0) * 1000.0)
        linear_matches_total = total_matches

    median_linear_total_ms = round(statistics.median(linear_times_ms), 3)
    median_linear_per_query_ms = round(median_linear_total_ms / query_count, 4)

    # 4. Benchmark Binary Search on Pre-Sorted Dataset for Q queries
    binary_times_ms = []
    binary_matches_total = 0
    sample_binary_result_ids = []

    for trial_idx in range(num_trials):
        t0 = time.perf_counter()
        total_matches = 0
        for start_dt, end_dt in queries:
            res = binary_search_expiry_window(sorted_dataset, start_dt, end_dt)
            total_matches += len(res['results'])
            if trial_idx == 0 and not sample_binary_result_ids:
                sample_binary_result_ids = [r['listing_id'] for r in res['results']]
        t1 = time.perf_counter()
        binary_times_ms.append((t1 - t0) * 1000.0)
        binary_matches_total = total_matches

    median_binary_total_ms = round(statistics.median(binary_times_ms), 3)
    median_binary_per_query_ms = round(median_binary_total_ms / query_count, 4)

    # Total combined time: Sort + Q * Binary Search
    total_sorted_search_ms = round(median_sort_time_ms + median_binary_total_ms, 3)

    # 5. Break-Even Query Count Calculation
    # Linear Search: Q * T_linear
    # Sorted Search: T_sort + Q * T_binary
    # Break-even when Q * T_linear >= T_sort + Q * T_binary
    # Q >= T_sort / (T_linear - T_binary)
    diff_per_query = median_linear_per_query_ms - median_binary_per_query_ms
    if diff_per_query > 0.0001:
        break_even_queries = int(median_sort_time_ms / diff_per_query) + 1
    else:
        break_even_queries = None

    # 6. Verify result equivalence
    results_equivalent = (sorted(sample_linear_result_ids) == sorted(sample_binary_result_ids))

    response_data = {
        'status': 'success',
        'dataset_size': dataset_size,
        'query_count': query_count,
        'trials_evaluated': num_trials,
        'merge_sort': {
            'median_time_ms': median_sort_time_ms,
            'complexity': 'O(n log n)',
            'all_trial_times_ms': [round(t, 2) for t in sort_times_ms],
        },
        'linear_search': {
            'total_time_ms': median_linear_total_ms,
            'time_per_query_ms': median_linear_per_query_ms,
            'total_matches': linear_matches_total,
            'complexity': 'O(n) per query',
        },
        'binary_search': {
            'total_time_ms': median_binary_total_ms,
            'time_per_query_ms': median_binary_per_query_ms,
            'total_matches': binary_matches_total,
            'complexity': 'O(log n + k) per query',
        },
        'sorted_pipeline': {
            'total_time_ms': total_sorted_search_ms,
            'formula': 'T_sort + Q * T_binary',
        },
        'analysis': {
            'speedup_per_query': round(median_linear_per_query_ms / max(median_binary_per_query_ms, 0.00001), 2),
            'break_even_query_count': break_even_queries,
            'results_equivalent': results_equivalent,
        },
    }

    return jsonify(response_data)
