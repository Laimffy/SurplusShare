"""
tests/test_fifo_queue.py — Unit Tests for FIFO Queue (CategoryRequestQueue)

Tests:
- Enqueue, dequeue, peek operations (O(1))
- Category queue segregation
- Strict arrival timestamp FIFO ordering
- Partial fulfillment and outstanding need tracking
- Academic requirement demonstration:
  Pantry A requests 20, Shelter B requests 30, Program C requests 15.
  35 units available.
  Allocation: A receives 20, B receives 15 (retains 15 need), C remains pending.
"""

import pytest
from datetime import datetime, timedelta
from algorithms.fifo_queue import CategoryRequestQueue, RequestItem


def test_enqueue_and_peek():
    queue = CategoryRequestQueue()
    assert queue.is_empty('bakery')

    req1 = RequestItem(
        request_id='REQ-001',
        organization_name='Pantry Alpha',
        food_category='Bakery',
        requested_quantity=20,
        quantity_unit='pieces',
        requested_at='2026-01-01T10:00:00',
    )
    queue.enqueue(req1)

    assert not queue.is_empty('bakery')
    assert queue.size('bakery') == 1

    front = queue.peek('bakery')
    assert front is not None
    assert front.request_id == 'REQ-001'
    assert queue.size('bakery') == 1  # peek does not remove


def test_fifo_order_preserved():
    queue = CategoryRequestQueue()

    req1 = RequestItem('REQ-001', 'Pantry A', 'Bakery', 10, 'pieces', requested_at='2026-01-01T10:00:00')
    req2 = RequestItem('REQ-002', 'Shelter B', 'Bakery', 15, 'pieces', requested_at='2026-01-01T10:05:00')
    req3 = RequestItem('REQ-003', 'Program C', 'Bakery', 20, 'pieces', requested_at='2026-01-01T10:10:00')

    queue.enqueue(req1)
    queue.enqueue(req2)
    queue.enqueue(req3)

    assert queue.size('bakery') == 3

    # Dequeue must return strictly in arrival order
    first = queue.dequeue('bakery')
    assert first.request_id == 'REQ-001'

    second = queue.dequeue('bakery')
    assert second.request_id == 'REQ-002'

    third = queue.dequeue('bakery')
    assert third.request_id == 'REQ-003'

    assert queue.is_empty('bakery')
    assert queue.dequeue('bakery') is None


def test_core_fifo_allocation_scenario():
    """
    Academic scenario:
    - Pantry A requests 20 loaves.
    - Shelter B requests 30 loaves.
    - Feeding Program C requests 15 loaves.
    - Bakery donates 35 loaves.

    Expected:
    - Pantry A receives 20.
    - Shelter B receives 15 (retains 15 outstanding).
    - Feeding Program C receives 0 (remains pending).
    """
    queue = CategoryRequestQueue()

    req_a = RequestItem('REQ-A', 'Pantry A', 'Bakery', 20, 'loaves', requested_at='2026-01-01T09:00:00')
    req_b = RequestItem('REQ-B', 'Shelter B', 'Bakery', 30, 'loaves', requested_at='2026-01-01T09:15:00')
    req_c = RequestItem('REQ-C', 'Feeding Program C', 'Bakery', 15, 'loaves', requested_at='2026-01-01T09:30:00')

    queue.enqueue(req_a)
    queue.enqueue(req_b)
    queue.enqueue(req_c)

    # 35 loaves available
    allocations = queue.allocate_food(category='Bakery', available_quantity=35)

    assert len(allocations) == 2

    # First allocation: Pantry A gets 20
    assert allocations[0]['request_id'] == 'REQ-A'
    assert allocations[0]['organization'] == 'Pantry A'
    assert allocations[0]['allocated'] == 20
    assert allocations[0]['remaining_need'] == 0

    # Second allocation: Shelter B gets 15
    assert allocations[1]['request_id'] == 'REQ-B'
    assert allocations[1]['organization'] == 'Shelter B'
    assert allocations[1]['allocated'] == 15
    assert allocations[1]['remaining_need'] == 15

    # Check queue state:
    # Pantry A was fully satisfied and dequeued
    # Shelter B is at front of queue with 15 outstanding need
    front = queue.peek('bakery')
    assert front is not None
    assert front.request_id == 'REQ-B'
    assert front.fulfilled_quantity == 15
    assert (front.requested_quantity - front.fulfilled_quantity) == 15
    assert front.status == 'partially_fulfilled'

    # Program C is still in queue with 15 need
    pending = queue.get_pending_requests('bakery')
    assert len(pending) == 2
    assert pending[0].request_id == 'REQ-B'
    assert pending[1].request_id == 'REQ-C'


def test_remove_cancelled_request():
    queue = CategoryRequestQueue()
    req1 = RequestItem('REQ-001', 'Pantry A', 'Dairy', 10, 'liters')
    req2 = RequestItem('REQ-002', 'Pantry B', 'Dairy', 20, 'liters')
    queue.enqueue(req1)
    queue.enqueue(req2)

    assert queue.size('dairy') == 2
    removed = queue.remove_request('REQ-001')
    assert removed is True
    assert queue.size('dairy') == 1
    assert queue.peek('dairy').request_id == 'REQ-002'

    # Non-existent ID returns False
    assert queue.remove_request('NON-EXISTENT') is False
