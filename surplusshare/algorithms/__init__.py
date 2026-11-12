"""
SurplusShare Algorithms Package

Manually implemented Data Structures & Algorithms for academic demonstration:
- FIFO Queue: CategoryRequestQueue, RequestItem
- Merge Sort: merge_sort, sort_by_expiry, sort_by_quantity, sort_by_posted, SortTracker
- Linear Search: linear_search, linear_search_by_name
- Binary Search: binary_search_lower_bound, binary_search_upper_bound, binary_search_expiry_window
- Doubly Linked List: PickupNode, DoublyLinkedList, PickupScheduleList
- Matching Engine: MatchingEngine
"""

from .fifo_queue import CategoryRequestQueue, RequestItem
from .merge_sort import (
    merge_sort,
    sort_by_expiry,
    sort_by_quantity,
    sort_by_posted,
    SortTracker,
)
from .linear_search import linear_search, linear_search_by_name
from .binary_search import (
    binary_search_lower_bound,
    binary_search_upper_bound,
    binary_search_expiry_window,
)
from .doubly_linked_list import PickupNode, DoublyLinkedList, PickupScheduleList
from .matching_engine import MatchingEngine

__all__ = [
    'CategoryRequestQueue',
    'RequestItem',
    'merge_sort',
    'sort_by_expiry',
    'sort_by_quantity',
    'sort_by_posted',
    'SortTracker',
    'linear_search',
    'linear_search_by_name',
    'binary_search_lower_bound',
    'binary_search_upper_bound',
    'binary_search_expiry_window',
    'PickupNode',
    'DoublyLinkedList',
    'PickupScheduleList',
    'MatchingEngine',
]
