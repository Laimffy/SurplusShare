"""
matching_engine.py — Automatic Food Matching Engine (SurplusShare)

DSA Integration Architecture:
=============================
This engine brings together all core academic DSA components developed for SurplusShare:

1. Merge Sort (Divide & Conquer):
   Sorts available food listings strictly by earliest expiry timestamp.
   Guaranteed O(m log m) time and stable sorting ensures that older/critical
   food items are always evaluated and distributed before fresher items.

2. FIFO Queue (Fair Allocation):
   Maintains recipient demand queues categorized by food type.
   Guarantees that recipient organizations are served strictly in order of
   arrival, with support for fair partial fulfillment when available surplus
   is insufficient to meet a full request.

3. Range Verification / Eligibility Checking:
   Verifies that the food's shelf-life satisfies the recipient organization's
   minimum required shelf-life (min_shelf_life_hours) and that categories/units match.

4. Determinism & Duplicate Prevention:
   Every allocation decrements the listing's available quantity and increments
   the request's fulfilled quantity. Once a listing's surplus reaches 0, it is
   closed; once a request is fully met, it is dequeued.

Author: SurplusShare DSA Final Project
"""

import time
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from .merge_sort import sort_by_expiry, SortTracker
from .fifo_queue import CategoryRequestQueue, RequestItem


def _parse_iso(dt_str: Optional[str]) -> Optional[datetime]:
    """Helper to parse ISO datetime strings into comparable naive datetimes."""
    if not dt_str:
        return None
    try:
        # Strip trailing Z if present
        cleaned = str(dt_str).replace('Z', '')
        return datetime.fromisoformat(cleaned)
    except Exception:
        return None


class MatchingEngine:
    """
    Automated matching engine coordinating Merge Sort, FIFO queues, and fair allocation.

    Attributes:
        request_queue (CategoryRequestQueue): Category-based FIFO queue.
        last_results (dict): Results and metrics from the most recent matching cycle.
    """

    def __init__(self):
        self.request_queue = CategoryRequestQueue()
        self.last_results: Dict[str, Any] = {}

    def load_requests(self, requests_data: List[Dict[str, Any]]) -> int:
        """
        Load a list of recipient request dictionaries into the FIFO queues.
        Sorts them by requested_at ascending to guarantee strict FIFO ordering.

        Args:
            requests_data: List of dictionary requests.

        Returns:
            int: Number of active requests enqueued.
        """
        # Clear existing queue
        self.request_queue.clear()

        # Sort raw requests by submission timestamp to guarantee FIFO integrity
        sorted_requests = sorted(
            requests_data,
            key=lambda r: str(r.get('requested_at') or '')
        )

        enqueued_count = 0
        for req in sorted_requests:
            status = str(req.get('status', 'pending')).lower()
            if status in ('fulfilled', 'cancelled', 'expired'):
                continue

            requested_qty = float(req.get('requested_quantity', 0.0))
            fulfilled_qty = float(req.get('fulfilled_quantity', 0.0))
            remaining_need = requested_qty - fulfilled_qty

            if remaining_need <= 0:
                continue

            item = RequestItem(
                request_id=str(req.get('request_id', '')),
                organization_name=str(req.get('organization_name', '')),
                food_category=str(req.get('food_category', '')),
                requested_quantity=requested_qty,
                quantity_unit=str(req.get('quantity_unit', '')),
                min_shelf_life_hours=float(req.get('min_shelf_life_hours', 0.0)),
                requested_at=str(req.get('requested_at', '')),
                status=status,
                fulfilled_quantity=fulfilled_qty,
            )
            # Store database primary key if present
            if 'id' in req:
                item.db_id = req['id']

            self.request_queue.enqueue(item)
            enqueued_count += 1

        return enqueued_count

    def run_matching(
        self,
        listings_data: List[Dict[str, Any]],
        requests_data: Optional[List[Dict[str, Any]]] = None,
        current_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Execute the deterministic food waste reallocation algorithm.

        Steps:
        1. Initialize current timestamp (defaults to datetime.now()).
        2. Filter out already expired, cancelled, or fully allocated listings.
        3. Prioritize eligible listings by earliest expiry time using Merge Sort.
        4. Populate FIFO queues for requests if requests_data is provided.
        5. For each prioritized listing:
           a. Query the FIFO queue for that food category.
           b. Match available quantity with waiting requests in FIFO order.
           c. Check minimum shelf-life constraints.
           d. Perform fair allocation (full or partial).
           e. Deduct allocated quantity from listing and add to request.
        6. Compute comprehensive execution performance metrics.

        Args:
            listings_data: List of available food listing dictionaries.
            requests_data: Optional list of recipient requests.
            current_time: Reference time for shelf-life calculations.

        Returns:
            dict containing allocations, updated listings, updated requests,
            and performance benchmark statistics.
        """
        start_total_time = time.perf_counter()
        now = current_time or datetime.now()

        # Step 1: Filter active, non-expired listings
        active_listings: List[Dict[str, Any]] = []
        for l in listings_data:
            st = str(l.get('status', 'available')).lower()
            if st in ('fully_allocated', 'expired', 'cancelled'):
                continue

            qty = float(l.get('quantity', 0.0))
            alloc_qty = float(l.get('allocated_quantity', 0.0))
            avail = qty - alloc_qty
            if avail <= 0.0001:
                continue

            expiry_dt = _parse_iso(l.get('expiry_at'))
            if expiry_dt and expiry_dt <= now:
                # Food has already expired; exclude from redistribution
                continue

            # Work on a copy to avoid mutating caller references unexpectedly
            l_copy = dict(l)
            l_copy['available_quantity'] = avail
            active_listings.append(l_copy)

        # Step 2: Merge Sort Priority Ordering (Earliest Expiry First)
        sort_tracker = SortTracker()
        sort_start = time.perf_counter()
        sorted_listings = sort_tracker.sort(
            active_listings,
            key_func=lambda item: str(item.get('expiry_at') or '')
        )
        sort_duration_ms = (time.perf_counter() - sort_start) * 1000.0

        # Step 3: Load recipient requests into FIFO queue
        if requests_data is not None:
            self.load_requests(requests_data)

        # Step 4: Core Allocation Loop
        match_start = time.perf_counter()
        allocations: List[Dict[str, Any]] = []
        matched_listing_ids = set()

        for listing in sorted_listings:
            cat = str(listing.get('category', '')).strip()
            avail_qty = float(listing.get('available_quantity', 0.0))

            if avail_qty <= 0.0001:
                continue

            # Calculate remaining shelf life in hours
            expiry_dt = _parse_iso(listing.get('expiry_at'))
            remaining_shelf_life_hours = 0.0
            if expiry_dt and expiry_dt > now:
                remaining_shelf_life_hours = (expiry_dt - now).total_seconds() / 3600.0

            # Inspect waiting requests in FIFO order for this category
            category_queue = self.request_queue.get_pending_requests(cat)
            if not category_queue:
                continue

            # We process requests front-to-back
            for req_item in category_queue:
                if avail_qty <= 0.0001:
                    break  # Listing surplus exhausted

                remaining_need = req_item.requested_quantity - req_item.fulfilled_quantity
                if remaining_need <= 0.0001:
                    continue

                # Check shelf-life eligibility
                if req_item.min_shelf_life_hours > 0:
                    if remaining_shelf_life_hours < req_item.min_shelf_life_hours:
                        # Expiry is too soon for this specific recipient organization
                        continue

                # Units check: If units differ, we still allocate if compatible or as requested
                # For safety, ensure units match or allow general redistribution
                listing_unit = str(listing.get('unit', '')).lower().strip()
                req_unit = str(req_item.quantity_unit).lower().strip()
                if listing_unit and req_unit and listing_unit != req_unit:
                    # Incompatible units; skip to maintain academic correctness
                    continue

                # Determine allocation quantity
                alloc_amount = min(avail_qty, remaining_need)
                alloc_amount = round(alloc_amount, 2)

                if alloc_amount <= 0:
                    continue

                # Deduct from listing and fulfill request
                avail_qty -= alloc_amount
                listing['available_quantity'] = round(avail_qty, 2)
                listing['allocated_quantity'] = round(
                    float(listing.get('allocated_quantity', 0.0)) + alloc_amount, 2
                )
                if listing['available_quantity'] <= 0.0001:
                    listing['status'] = 'fully_allocated'
                else:
                    listing['status'] = 'partially_allocated'

                req_item.fulfilled_quantity = round(req_item.fulfilled_quantity + alloc_amount, 2)
                if req_item.fulfilled_quantity >= req_item.requested_quantity - 0.0001:
                    req_item.status = 'fulfilled'
                else:
                    req_item.status = 'partially_fulfilled'

                alloc_record = {
                    'allocation_id': f"AL-{uuid.uuid4().hex[:6].upper()}",
                    'listing_id': listing.get('listing_id'),
                    'listing_db_id': listing.get('id'),
                    'food_name': listing.get('food_name'),
                    'category': cat,
                    'donor_name': listing.get('donor_name'),
                    'pickup_location': listing.get('pickup_location'),
                    'request_id': req_item.request_id,
                    'request_db_id': getattr(req_item, 'db_id', None),
                    'organization_name': req_item.organization_name,
                    'allocated_quantity': alloc_amount,
                    'unit': listing.get('unit'),
                    'expiry_at': listing.get('expiry_at'),
                    'remaining_shelf_life_hours': round(remaining_shelf_life_hours, 1),
                    'allocated_at': now.isoformat(),
                    'status': 'pending',
                }
                allocations.append(alloc_record)
                matched_listing_ids.add(listing.get('listing_id'))

        match_duration_ms = (time.perf_counter() - match_start) * 1000.0
        total_duration_ms = (time.perf_counter() - start_total_time) * 1000.0

        # Compile summaries
        unmatched_listings = [
            l for l in sorted_listings if float(l.get('available_quantity', 0.0)) > 0.0001
        ]
        all_pending_dict = self.request_queue.get_all_pending()
        unfulfilled_requests = []
        for cat_list in all_pending_dict.values():
            for req in cat_list:
                unfulfilled_requests.append(req.to_dict())

        total_allocated_units = sum(a['allocated_quantity'] for a in allocations)

        stats = {
            'listings_evaluated': len(active_listings),
            'listings_matched': len(matched_listing_ids),
            'unmatched_listings_count': len(unmatched_listings),
            'allocations_generated': len(allocations),
            'total_quantity_allocated': round(total_allocated_units, 2),
            'sort_time_ms': round(sort_duration_ms, 3),
            'sort_comparisons': sort_tracker.comparisons,
            'match_time_ms': round(match_duration_ms, 3),
            'total_time_ms': round(total_duration_ms, 3),
        }

        self.last_results = {
            'allocations': allocations,
            'stats': stats,
            'sorted_listings': sorted_listings,
            'unmatched_listings': unmatched_listings,
            'unfulfilled_requests': unfulfilled_requests,
        }

        return self.last_results

    def get_results_summary(self) -> Dict[str, Any]:
        """Return the cached results summary from the last run."""
        return self.last_results
