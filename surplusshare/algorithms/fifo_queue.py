"""
fifo_queue.py — FIFO Queue for Recipient Requests (SurplusShare)

DSA Concept: First-In-First-Out (FIFO) Queue
============================================
A FIFO queue processes elements in the exact order they arrive — the first
element enqueued is the first element dequeued. This guarantees fairness:
organizations that request food earlier are served before those that request
later, regardless of request size.

Underlying Data Structure: collections.deque (double-ended queue)
- Implemented as a doubly-linked list of fixed-size blocks in CPython
- Provides O(1) append and popleft operations
- Superior to list for queue operations (list.pop(0) is O(n))

Complexity Summary:
    enqueue:          O(1) amortized
    dequeue:          O(1)
    peek:             O(1)
    get_pending:      O(n) where n = items in category queue
    size:             O(1) per category, O(c) for total (c = num categories)
    remove_request:   O(n) — must scan the queue
    update_fulfilled: O(n) — must scan the queue
    allocate_food:    O(k) where k = requests processed before food runs out

Author: SurplusShare DSA Final Project
"""

from collections import deque
from datetime import datetime, timezone
import uuid
import copy


class RequestItem:
    """
    Represents a single recipient request in the queue.

    Each RequestItem captures who is asking for food, what category,
    how much they need, and any shelf-life constraints. The request
    tracks its own fulfillment progress so partial allocations are
    supported.

    Attributes:
        request_id (str):           Unique identifier for this request.
        organization_name (str):    Name of the requesting organization.
        food_category (str):        Food category (e.g., 'bread', 'dairy').
        requested_quantity (float): Total quantity originally requested.
        quantity_unit (str):        Unit of measure (e.g., 'kg', 'loaves').
        min_shelf_life_hours (float): Minimum remaining shelf life the org
                                      will accept (0 = no constraint).
        requested_at (str):         ISO-8601 timestamp of when the request
                                    was submitted (FIFO ordering key).
        status (str):               'pending', 'partially_fulfilled', or
                                    'fulfilled'.
        fulfilled_quantity (float): Quantity allocated so far.
    """

    def __init__(self, request_id, organization_name, food_category,
                 requested_quantity, quantity_unit, min_shelf_life_hours=0,
                 requested_at=None, status='pending', fulfilled_quantity=0):
        # --- Store identifiers ---
        # Generate a UUID if no request_id is provided
        self.request_id = request_id or str(uuid.uuid4())
        self.organization_name = organization_name

        # --- Food matching criteria ---
        # Normalize category to lowercase for consistent matching
        self.food_category = food_category.lower().strip() if food_category else ''
        self.requested_quantity = float(requested_quantity)
        self.quantity_unit = quantity_unit

        # Minimum shelf life constraint: the food must have at least this
        # many hours of shelf life remaining for this org to accept it
        self.min_shelf_life_hours = float(min_shelf_life_hours)

        # --- Timing ---
        # Record when the request was made; this determines FIFO order
        if requested_at is None:
            self.requested_at = datetime.now(timezone.utc).isoformat()
        else:
            self.requested_at = requested_at

        # --- Fulfillment tracking ---
        self.status = status
        self.fulfilled_quantity = float(fulfilled_quantity)

    @property
    def remaining_need(self):
        """
        Calculate how much more food this request still needs.

        Returns:
            float: requested_quantity minus fulfilled_quantity, clamped >= 0.

        Time Complexity: O(1)
        """
        return max(0.0, self.requested_quantity - self.fulfilled_quantity)

    def to_dict(self):
        """
        Convert this RequestItem to a plain dictionary for JSON serialization
        or template rendering.

        Returns:
            dict: All fields as a dictionary.

        Time Complexity: O(1)
        """
        return {
            'request_id': self.request_id,
            'organization_name': self.organization_name,
            'food_category': self.food_category,
            'requested_quantity': self.requested_quantity,
            'quantity_unit': self.quantity_unit,
            'min_shelf_life_hours': self.min_shelf_life_hours,
            'requested_at': self.requested_at,
            'status': self.status,
            'fulfilled_quantity': self.fulfilled_quantity,
            'remaining_need': self.remaining_need,
        }

    def __repr__(self):
        return (f"RequestItem(id={self.request_id!r}, org={self.organization_name!r}, "
                f"cat={self.food_category!r}, qty={self.requested_quantity}, "
                f"fulfilled={self.fulfilled_quantity}, status={self.status!r})")


class CategoryRequestQueue:
    """
    FIFO Queue for managing recipient requests per food category.

    DSA Concept: First-In-First-Out (FIFO) Queue
    =============================================
    This class maintains one deque per food category. When food becomes
    available in a category, requests are served strictly in arrival order
    (front of the deque first). This is the fairest possible allocation
    strategy and is the core DSA demonstration of a queue.

    Internal structure:
        _queues:  dict[str, deque[RequestItem]]
            Maps each food category to its FIFO deque.
        _request_index:  dict[str, (str, RequestItem)]
            Maps request_id → (category, RequestItem) for O(1) lookup.

    Complexity:
        Enqueue:  O(1) — deque.append
        Dequeue:  O(1) — deque.popleft
        Peek:     O(1) — deque[0]
        Size:     O(1) per category, O(c) total
        Remove:   O(n) — must rebuild deque without the item
        Search:   O(1) via _request_index
    """

    def __init__(self):
        # ---- Primary storage: category → deque of RequestItem ----
        # Each deque preserves FIFO order for that food category.
        self._queues = {}

        # ---- Secondary index: request_id → (category, RequestItem) ----
        # Allows O(1) lookup of any request regardless of category,
        # which is useful for update/cancel operations.
        self._request_index = {}

    # ------------------------------------------------------------------
    #  Core Queue Operations
    # ------------------------------------------------------------------

    def enqueue(self, request):
        """
        Add a request to the back of the appropriate category queue.

        Algorithm:
            1. Normalize the food_category to lowercase.
            2. If no deque exists for this category, create one.
            3. Append the request to the back of the deque (FIFO).
            4. Register in _request_index for O(1) future lookup.

        Args:
            request (RequestItem): The request to enqueue.

        Returns:
            bool: True if successfully enqueued, False if duplicate ID.

        Time Complexity: O(1) amortized
        Space Complexity: O(1) amortized (one node added)
        """
        # --- Guard: reject duplicate request IDs ---
        if request.request_id in self._request_index:
            return False

        # --- Step 1: Determine the category key ---
        category = request.food_category.lower().strip()

        # --- Step 2: Create the category deque if it doesn't exist ---
        if category not in self._queues:
            self._queues[category] = deque()

        # --- Step 3: Append to the BACK of the deque (FIFO enqueue) ---
        # This is the fundamental queue operation: new arrivals go to the end
        self._queues[category].append(request)

        # --- Step 4: Register in the lookup index ---
        self._request_index[request.request_id] = (category, request)

        return True

    def peek(self, category):
        """
        View the front request for a category WITHOUT removing it.

        This lets us inspect who would be served next without actually
        modifying the queue — useful for UI display and pre-checks.

        Args:
            category (str): The food category to peek at.

        Returns:
            RequestItem or None: The front request, or None if empty.

        Time Complexity: O(1) — direct index access on deque
        """
        # --- Normalize category ---
        category = category.lower().strip()

        # --- Check that the category exists and has items ---
        if category not in self._queues or len(self._queues[category]) == 0:
            return None

        # --- Return the FRONT element (index 0) without removing ---
        return self._queues[category][0]

    def dequeue(self, category):
        """
        Remove and return the FRONT request for a category.

        This is the core FIFO operation: the earliest-arriving request
        is removed and returned. After dequeue, the next request moves
        to the front position.

        Args:
            category (str): The food category to dequeue from.

        Returns:
            RequestItem or None: The front request, or None if empty.

        Time Complexity: O(1) — deque.popleft is O(1)
        """
        # --- Normalize category ---
        category = category.lower().strip()

        # --- Check that the category exists and has items ---
        if category not in self._queues or len(self._queues[category]) == 0:
            return None

        # --- Remove from the FRONT (popleft is the FIFO dequeue) ---
        request = self._queues[category].popleft()

        # --- Clean up the lookup index ---
        if request.request_id in self._request_index:
            del self._request_index[request.request_id]

        return request

    # ------------------------------------------------------------------
    #  Query Operations
    # ------------------------------------------------------------------

    def get_pending_requests(self, category):
        """
        Get all pending (not yet fully fulfilled) requests for a category,
        preserving their FIFO order.

        Algorithm:
            Iterate through the deque front-to-back, collecting only those
            requests whose status is 'pending' or 'partially_fulfilled'.

        Args:
            category (str): The food category.

        Returns:
            list[RequestItem]: Pending requests in FIFO order.

        Time Complexity: O(n) where n = items in this category's deque
        Space Complexity: O(k) where k = number of pending items
        """
        category = category.lower().strip()

        if category not in self._queues:
            return []

        # --- Scan front-to-back, keeping only pending/partial items ---
        pending = []
        for req in self._queues[category]:
            if req.status in ('pending', 'partially_fulfilled'):
                pending.append(req)

        return pending

    def get_all_pending(self):
        """
        Get all pending requests across ALL categories, grouped by category.

        Returns:
            dict[str, list[RequestItem]]: Category → list of pending requests.

        Time Complexity: O(n) where n = total items across all categories
        Space Complexity: O(n) worst case
        """
        result = {}
        for category in self._queues:
            pending = self.get_pending_requests(category)
            if pending:
                result[category] = pending
        return result

    def size(self, category=None):
        """
        Get the number of items in the queue.

        Args:
            category (str or None): If provided, count only that category.
                                    If None, count all items across all categories.

        Returns:
            int: Number of items.

        Time Complexity:
            O(1) if category is specified (deque stores its length)
            O(c) if category is None (c = number of categories)
        """
        if category is not None:
            category = category.lower().strip()
            if category not in self._queues:
                return 0
            return len(self._queues[category])

        # --- Sum across all categories ---
        total = 0
        for cat_deque in self._queues.values():
            total += len(cat_deque)
        return total

    def is_empty(self, category=None):
        """
        Check if the queue is empty.

        Args:
            category (str or None): If provided, check only that category.
                                    If None, check ALL categories.

        Returns:
            bool: True if empty.

        Time Complexity: O(1) if category specified, O(c) otherwise
        """
        if category is not None:
            return self.size(category) == 0

        # --- Check all categories ---
        return self.size() == 0

    def clear(self):
        """Remove all requests from all category queues. Time Complexity: O(1)."""
        self._queues.clear()
        self._request_index.clear()

    # ------------------------------------------------------------------
    #  Modification Operations
    # ------------------------------------------------------------------

    def remove_request(self, request_id):
        """
        Remove a specific request by its ID (for cancellation).

        Since deque does not support efficient removal by value from an
        arbitrary position, we must rebuild the deque without the target
        item. This is an O(n) operation, which is acceptable for
        cancellations (infrequent operations).

        Algorithm:
            1. Look up the request in _request_index → O(1).
            2. Rebuild the deque for that category, excluding the target → O(n).
            3. Remove from _request_index → O(1).

        Args:
            request_id (str): The ID of the request to remove.

        Returns:
            bool: True if the request was found and removed.

        Time Complexity: O(n) where n = items in that category's deque
        Space Complexity: O(n) for the rebuilt deque
        """
        # --- Step 1: O(1) lookup ---
        if request_id not in self._request_index:
            return False

        category, target_request = self._request_index[request_id]

        # --- Step 2: Rebuild the deque without the target item ---
        # We create a new deque containing all items except the one to remove.
        # This preserves FIFO order for the remaining items.
        old_deque = self._queues[category]
        new_deque = deque()
        for req in old_deque:
            if req.request_id != request_id:
                new_deque.append(req)
        self._queues[category] = new_deque

        # --- Step 3: Remove from index ---
        del self._request_index[request_id]

        return True

    def update_fulfilled(self, request_id, additional_quantity):
        """
        Add to a request's fulfilled quantity and update its status.

        This is called during allocation: when food is assigned to a
        request, we increment its fulfilled_quantity and check whether
        it's now fully satisfied.

        Algorithm:
            1. Look up the request in _request_index → O(1).
            2. Add additional_quantity to fulfilled_quantity.
            3. Update status based on fulfillment level.

        Args:
            request_id (str): The ID of the request to update.
            additional_quantity (float): Additional quantity just allocated.

        Returns:
            RequestItem or None: The updated request, or None if not found.

        Time Complexity: O(1) — direct lookup via index
        """
        # --- Step 1: Look up the request ---
        if request_id not in self._request_index:
            return None

        _category, request = self._request_index[request_id]

        # --- Step 2: Increment fulfilled quantity ---
        request.fulfilled_quantity += float(additional_quantity)

        # --- Step 3: Update status ---
        # If fulfilled >= requested, the request is fully satisfied.
        # If partially fulfilled, mark as such.
        if request.fulfilled_quantity >= request.requested_quantity:
            request.fulfilled_quantity = request.requested_quantity  # clamp
            request.status = 'fulfilled'
        elif request.fulfilled_quantity > 0:
            request.status = 'partially_fulfilled'
        # else: status stays 'pending'

        return request

    # ------------------------------------------------------------------
    #  Core FIFO Allocation Algorithm
    # ------------------------------------------------------------------

    def allocate_food(self, category, available_quantity,
                      min_remaining_life_hours=0):
        """
        Allocate available food to requests in strict FIFO order.

        ======================================================
        THIS IS THE CORE FIFO DEMONSTRATION
        ======================================================

        The algorithm processes requests front-to-back (earliest first).
        Each request receives as much food as possible up to its remaining
        need. Once the available supply is exhausted, remaining requests
        get nothing and stay in the queue for future allocations.

        Partially fulfilled requests remain in the queue with an updated
        fulfilled_quantity; fully fulfilled requests are dequeued.

        Example (from project spec):
            Pantry A wants 20 loaves (arrives first)
            Shelter B wants 30 loaves (arrives second)
            Program C wants 15 loaves (arrives third)
            Available: 35 loaves

            FIFO processing:
            1. A is at front → gets min(20, 35) = 20 → remaining supply = 15
            2. B is next     → gets min(30, 15) = 15 → remaining supply = 0
            3. C is last     → gets min(15,  0) =  0 → still pending

            Result: A=20 (fulfilled), B=15 (partial), C=0 (pending)

        Algorithm:
            1. Normalize category name.
            2. Get the deque for this category.
            3. Iterate front-to-back:
               a. Skip requests whose shelf-life requirement exceeds
                  what the food offers.
               b. Calculate allocation = min(remaining_need, available).
               c. Deduct from available supply.
               d. Update the request's fulfilled quantity and status.
               e. Record the allocation.
               f. If supply exhausted, stop.
            4. Remove fully-fulfilled requests from the deque.
            5. Return the list of allocations made.

        Args:
            category (str): Food category to match against.
            available_quantity (float): Total food quantity available for
                                       allocation.
            min_remaining_life_hours (float): The shelf life (in hours)
                                             that the available food
                                             actually has remaining.

        Returns:
            list[dict]: List of allocation records, each containing:
                - 'request_id': str
                - 'organization': str
                - 'allocated': float  (quantity given in this allocation)
                - 'remaining_need': float  (what the org still needs)
                - 'status': str  ('fulfilled' or 'partially_fulfilled')

        Time Complexity: O(k) where k = number of requests processed
                         before supply runs out
        Space Complexity: O(k) for the allocations list
        """
        # --- Step 1: Normalize category ---
        category = category.lower().strip()
        allocations = []

        # --- Step 2: Check that the category queue exists ---
        if category not in self._queues or len(self._queues[category]) == 0:
            return allocations

        # Track remaining supply
        remaining_supply = float(available_quantity)

        # --- Step 3: Process requests front-to-back (FIFO order) ---
        # We iterate over the deque but do NOT popleft during iteration.
        # Instead, we mark fulfilled items and remove them afterward.
        fulfilled_ids = []

        for request in self._queues[category]:
            # --- 3f: If supply is exhausted, stop processing ---
            if remaining_supply <= 0:
                break

            # --- Skip already-fulfilled requests ---
            if request.status == 'fulfilled':
                fulfilled_ids.append(request.request_id)
                continue

            # --- 3a: Check shelf-life constraint ---
            # If this organization requires more shelf life than the food has,
            # skip it (the food would expire too soon for their needs).
            if request.min_shelf_life_hours > min_remaining_life_hours:
                continue

            # --- 3b: Calculate allocation amount ---
            # The request gets the MINIMUM of what it still needs and what's
            # available. This ensures no over-allocation.
            need = request.remaining_need
            allocation_amount = min(need, remaining_supply)

            # --- 3c: Deduct from available supply ---
            remaining_supply -= allocation_amount

            # --- 3d: Update the request's fulfillment state ---
            self.update_fulfilled(request.request_id, allocation_amount)

            # --- 3e: Record the allocation ---
            allocation_record = {
                'request_id': request.request_id,
                'organization': request.organization_name,
                'allocated': allocation_amount,
                'remaining_need': request.remaining_need,
                'status': request.status,
            }
            allocations.append(allocation_record)

            # Track fulfilled requests for removal
            if request.status == 'fulfilled':
                fulfilled_ids.append(request.request_id)

        # --- Step 4: Remove fully-fulfilled requests from the deque ---
        # Rebuild the deque without fulfilled items to keep the queue clean.
        if fulfilled_ids:
            fulfilled_set = set(fulfilled_ids)
            old_deque = self._queues[category]
            new_deque = deque()
            for req in old_deque:
                if req.request_id not in fulfilled_set:
                    new_deque.append(req)
                else:
                    # Also clean up the index for fulfilled requests
                    if req.request_id in self._request_index:
                        del self._request_index[req.request_id]
            self._queues[category] = new_deque

        # --- Step 5: Return allocations ---
        return allocations

    # ------------------------------------------------------------------
    #  Utility Methods
    # ------------------------------------------------------------------

    def get_categories(self):
        """
        Get a list of all categories that have at least one request.

        Returns:
            list[str]: Category names.

        Time Complexity: O(c) where c = number of categories
        """
        return [cat for cat, dq in self._queues.items() if len(dq) > 0]

    def get_queue_snapshot(self, category):
        """
        Get a snapshot of the queue for a category as a list of dicts.
        Useful for debugging and UI display.

        Args:
            category (str): The food category.

        Returns:
            list[dict]: Each request as a dictionary, in FIFO order.

        Time Complexity: O(n)
        """
        category = category.lower().strip()
        if category not in self._queues:
            return []
        return [req.to_dict() for req in self._queues[category]]

    def __repr__(self):
        parts = []
        for cat, dq in self._queues.items():
            parts.append(f"  {cat}: {len(dq)} requests")
        body = "\n".join(parts) if parts else "  (empty)"
        return f"CategoryRequestQueue(\n{body}\n)"
