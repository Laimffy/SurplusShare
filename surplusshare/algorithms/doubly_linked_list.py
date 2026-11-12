"""
doubly_linked_list.py — Doubly Linked List for Pickup Schedules (SurplusShare)

DSA Concept: Doubly Linked List (DLL)
=====================================
A Doubly Linked List is a linear data structure where each node contains:
1. Data payload (here: volunteer pickup stop information)
2. A pointer/reference to the NEXT node (next)
3. A pointer/reference to the PREVIOUS node (prev)

Why Doubly Linked List for volunteer pickup schedules?
------------------------------------------------------
1. Bidirectional Traversal: Volunteers can navigate forward (from first stop to last)
   or backward (to review completed stops or handle returns) in O(n) time.
2. Dynamic Reordering: Moving a stop to an earlier or later position, inserting an
   urgent stop between two existing stops, or cancelling a stop can be performed in
   O(1) pointer updates once node references are identified, without shifting an
   entire contiguous array like in Python's built-in list.
3. Decoupled Route Sequencing: The DLL manages the execution sequence of pickup
   stops determined by dispatchers/volunteers. Note that this is a sequence manager,
   not an automated traveling-salesperson route optimization solver.

Complexity Summary:
    Operation                 Time Complexity    Auxiliary Space
    ------------------------------------------------------------
    append(node)              O(1)               O(1)
    prepend(node)             O(1)               O(1)
    insert_after(target, node)O(1)*              O(1)
    insert_before(target, node)O(1)*             O(1)
    remove(stop_id)           O(1)*              O(1)
    move_after/move_before    O(1)*              O(1)
    find(stop_id)             O(1)*              O(1)
    traverse_forward()        O(n)               O(n) for result list
    traverse_backward()       O(n)               O(n) for result list
    *Note: O(1) time is achieved by maintaining an internal hash map (_node_map)
     mapping stop_id -> PickupNode alongside head and tail pointers.

Author: SurplusShare DSA Final Project
"""

from typing import Optional, Dict, List, Any


class PickupNode:
    """
    A single node in the pickup schedule doubly linked list.

    Each node represents one volunteer pickup stop at a donor establishment.

    Attributes:
        stop_id (str): Unique identifier for this stop (e.g. 'ST-001').
        donor_name (str): Donor company or store name.
        pickup_location (str): Physical address for the pickup.
        listing_id (str or int, optional): Associated food listing reference.
        scheduled_time (str, optional): Planned ISO or time string for the pickup.
        status (str): Current status ('pending', 'completed', 'skipped', 'cancelled').
        notes (str): Special handling instructions or remarks.
        prev (PickupNode or None): Pointer to the preceding stop in the schedule.
        next (PickupNode or None): Pointer to the succeeding stop in the schedule.
    """

    def __init__(
        self,
        stop_id: str,
        donor_name: str,
        pickup_location: str,
        listing_id: Optional[Any] = None,
        scheduled_time: Optional[str] = None,
        status: str = 'pending',
        notes: str = '',
    ):
        self.stop_id = str(stop_id)
        self.donor_name = str(donor_name)
        self.pickup_location = str(pickup_location)
        self.listing_id = listing_id
        self.scheduled_time = scheduled_time or ''
        self.status = status
        self.notes = notes or ''

        # Doubly Linked List Pointers
        self.prev: Optional['PickupNode'] = None
        self.next: Optional['PickupNode'] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert node data to a dictionary suitable for JSON serialization
        or Jinja2 template rendering.
        """
        return {
            'stop_id': self.stop_id,
            'donor_name': self.donor_name,
            'pickup_location': self.pickup_location,
            'listing_id': self.listing_id,
            'scheduled_time': self.scheduled_time,
            'status': self.status,
            'notes': self.notes,
            'has_prev': self.prev is not None,
            'has_next': self.next is not None,
            'prev_stop_id': self.prev.stop_id if self.prev else None,
            'next_stop_id': self.next.stop_id if self.next else None,
        }

    def __repr__(self) -> str:
        return f"<PickupNode stop_id={self.stop_id} donor={self.donor_name} status={self.status}>"


class DoublyLinkedList:
    """
    Manually implemented Doubly Linked List for volunteer pickup schedules.

    Maintains head, tail, and an internal lookup dictionary for O(1) stop
    access by stop_id.
    """

    def __init__(self):
        self.head: Optional[PickupNode] = None
        self.tail: Optional[PickupNode] = None
        self._size: int = 0
        self._node_map: Dict[str, PickupNode] = {}

    # ------------------------------------------------------------------
    # Size and Status Queries
    # ------------------------------------------------------------------

    def get_size(self) -> int:
        """Return the number of stops currently in the list. Time: O(1)."""
        return self._size

    def __len__(self) -> int:
        return self._size

    def is_empty(self) -> bool:
        """Check whether the schedule contains any stops. Time: O(1)."""
        return self._size == 0

    def find(self, stop_id: str) -> Optional[PickupNode]:
        """
        Find and return a node by its stop_id.
        Time: O(1) using the internal hash map index.
        """
        return self._node_map.get(str(stop_id))

    def contains(self, stop_id: str) -> bool:
        """Check if a stop_id exists in the list. Time: O(1)."""
        return str(stop_id) in self._node_map

    # ------------------------------------------------------------------
    # Insertion Operations
    # ------------------------------------------------------------------

    def append(self, node: PickupNode) -> bool:
        """
        Add a pickup stop to the end (tail) of the schedule.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        if not isinstance(node, PickupNode):
            raise TypeError("Expected an instance of PickupNode")

        if node.stop_id in self._node_map:
            raise ValueError(f"Stop ID '{node.stop_id}' already exists in the schedule")

        # Clear any existing pointers on the node
        node.prev = None
        node.next = None

        if self.is_empty():
            self.head = node
            self.tail = node
        else:
            assert self.tail is not None
            node.prev = self.tail
            self.tail.next = node
            self.tail = node

        self._node_map[node.stop_id] = node
        self._size += 1
        return True

    def prepend(self, node: PickupNode) -> bool:
        """
        Add a pickup stop to the beginning (head) of the schedule.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        if not isinstance(node, PickupNode):
            raise TypeError("Expected an instance of PickupNode")

        if node.stop_id in self._node_map:
            raise ValueError(f"Stop ID '{node.stop_id}' already exists in the schedule")

        node.prev = None
        node.next = None

        if self.is_empty():
            self.head = node
            self.tail = node
        else:
            assert self.head is not None
            node.next = self.head
            self.head.prev = node
            self.head = node

        self._node_map[node.stop_id] = node
        self._size += 1
        return True

    def insert_after(self, target_stop_id: str, new_node: PickupNode) -> bool:
        """
        Insert new_node immediately after target_stop_id.

        Time Complexity: O(1) (O(1) hash map lookup + O(1) pointer updates)
        Space Complexity: O(1)
        """
        target = self.find(target_stop_id)
        if target is None:
            raise KeyError(f"Target stop '{target_stop_id}' not found in schedule")

        if new_node.stop_id in self._node_map:
            raise ValueError(f"Stop ID '{new_node.stop_id}' already exists in the schedule")

        new_node.prev = target
        new_node.next = target.next

        if target.next is not None:
            target.next.prev = new_node
        else:
            # Target was tail, so new_node becomes new tail
            self.tail = new_node

        target.next = new_node

        self._node_map[new_node.stop_id] = new_node
        self._size += 1
        return True

    def insert_before(self, target_stop_id: str, new_node: PickupNode) -> bool:
        """
        Insert new_node immediately before target_stop_id.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        target = self.find(target_stop_id)
        if target is None:
            raise KeyError(f"Target stop '{target_stop_id}' not found in schedule")

        if new_node.stop_id in self._node_map:
            raise ValueError(f"Stop ID '{new_node.stop_id}' already exists in the schedule")

        new_node.next = target
        new_node.prev = target.prev

        if target.prev is not None:
            target.prev.next = new_node
        else:
            # Target was head, so new_node becomes new head
            self.head = new_node

        target.prev = new_node

        self._node_map[new_node.stop_id] = new_node
        self._size += 1
        return True

    # ------------------------------------------------------------------
    # Deletion Operations
    # ------------------------------------------------------------------

    def remove(self, stop_id: str) -> Optional[PickupNode]:
        """
        Remove a stop by stop_id from the list and return it.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        node = self.find(stop_id)
        if node is None:
            return None

        self._unlink(node)
        del self._node_map[node.stop_id]
        self._size -= 1
        return node

    def _unlink(self, node: PickupNode) -> None:
        """
        Disconnect a node from its neighbors and adjust head/tail if necessary.
        Helper method that leaves node.prev and node.next intact until cleared.
        """
        if node.prev is not None:
            node.prev.next = node.next
        else:
            # Node was head
            self.head = node.next

        if node.next is not None:
            node.next.prev = node.prev
        else:
            # Node was tail
            self.tail = node.prev

        node.prev = None
        node.next = None

    def clear(self) -> None:
        """Remove all nodes from the schedule."""
        self.head = None
        self.tail = None
        self._size = 0
        self._node_map.clear()

    # ------------------------------------------------------------------
    # Reordering Operations
    # ------------------------------------------------------------------

    def move_to_head(self, stop_id: str) -> bool:
        """Move an existing stop to the head of the schedule."""
        node = self.find(stop_id)
        if node is None or node is self.head:
            return False

        self._unlink(node)
        # Prepend without increasing size or re-adding to map
        node.prev = None
        node.next = self.head
        if self.head is not None:
            self.head.prev = node
        self.head = node
        if self.tail is None:
            self.tail = node
        return True

    def move_to_tail(self, stop_id: str) -> bool:
        """Move an existing stop to the tail of the schedule."""
        node = self.find(stop_id)
        if node is None or node is self.tail:
            return False

        self._unlink(node)
        # Append without increasing size or re-adding to map
        node.next = None
        node.prev = self.tail
        if self.tail is not None:
            self.tail.next = node
        self.tail = node
        if self.head is None:
            self.head = node
        return True

    def move_before(self, stop_id: str, target_stop_id: str) -> bool:
        """
        Move stop_id so that it is positioned directly before target_stop_id.
        """
        if stop_id == target_stop_id:
            return False

        node = self.find(stop_id)
        target = self.find(target_stop_id)
        if node is None or target is None:
            return False

        # If already immediately before target, nothing to do
        if node.next is target:
            return True

        self._unlink(node)

        # Splice node before target
        node.next = target
        node.prev = target.prev

        if target.prev is not None:
            target.prev.next = node
        else:
            self.head = node

        target.prev = node
        return True

    def move_after(self, stop_id: str, target_stop_id: str) -> bool:
        """
        Move stop_id so that it is positioned directly after target_stop_id.
        """
        if stop_id == target_stop_id:
            return False

        node = self.find(stop_id)
        target = self.find(target_stop_id)
        if node is None or target is None:
            return False

        # If already immediately after target, nothing to do
        if target.next is node:
            return True

        self._unlink(node)

        # Splice node after target
        node.prev = target
        node.next = target.next

        if target.next is not None:
            target.next.prev = node
        else:
            self.tail = node

        target.next = node
        return True

    def swap_adjacent_forward(self, stop_id: str) -> bool:
        """
        Move a stop one position later (swap with its next neighbor).
        Useful for "Move Down" UI controls.
        """
        node = self.find(stop_id)
        if node is None or node.next is None:
            return False
        return self.move_after(stop_id, node.next.stop_id)

    def swap_adjacent_backward(self, stop_id: str) -> bool:
        """
        Move a stop one position earlier (swap with its previous neighbor).
        Useful for "Move Up" UI controls.
        """
        node = self.find(stop_id)
        if node is None or node.prev is None:
            return False
        return self.move_before(stop_id, node.prev.stop_id)

    # ------------------------------------------------------------------
    # Traversal and Export
    # ------------------------------------------------------------------

    def traverse_forward(self) -> List[PickupNode]:
        """
        Traverse the list from head to tail (start of pickup to end).

        Time Complexity: O(n)
        Space Complexity: O(n) for list container
        """
        result: List[PickupNode] = []
        curr = self.head
        while curr is not None:
            result.append(curr)
            curr = curr.next
        return result

    def traverse_backward(self) -> List[PickupNode]:
        """
        Traverse the list from tail to head (end of pickup to start).

        Time Complexity: O(n)
        Space Complexity: O(n) for list container
        """
        result: List[PickupNode] = []
        curr = self.tail
        while curr is not None:
            result.append(curr)
            curr = curr.prev
        return result

    def to_list(self) -> List[Dict[str, Any]]:
        """
        Convert all nodes in order into a list of dictionaries with
        explicit 1-based stop_order values.
        """
        result: List[Dict[str, Any]] = []
        curr = self.head
        order = 1
        while curr is not None:
            d = curr.to_dict()
            d['stop_order'] = order
            result.append(d)
            curr = curr.next
            order += 1
        return result

    def update_status(self, stop_id: str, new_status: str) -> bool:
        """Update the status of a specific stop."""
        node = self.find(stop_id)
        if node is None:
            return False
        node.status = new_status
        return True

    # ------------------------------------------------------------------
    # Serialization / Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_list(cls, stops_data: List[Dict[str, Any]]) -> 'DoublyLinkedList':
        """
        Reconstruct a DoublyLinkedList from an ordered list of stop dictionaries.
        Expected keys per dict: stop_id, donor_name, pickup_location, etc.
        """
        dll = cls()
        for item in stops_data:
            node = PickupNode(
                stop_id=str(item.get('stop_id', '')),
                donor_name=item.get('donor_name', ''),
                pickup_location=item.get('pickup_location', ''),
                listing_id=item.get('listing_id'),
                scheduled_time=item.get('scheduled_time', ''),
                status=item.get('status', 'pending'),
                notes=item.get('notes', ''),
            )
            dll.append(node)
        return dll


# Alias for semantic clarity with pickup schedule
PickupScheduleList = DoublyLinkedList
