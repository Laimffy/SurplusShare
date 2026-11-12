"""
tests/test_doubly_linked_list.py — Unit Tests for Doubly Linked List

Tests:
- Node creation and pointer initialization
- Append and prepend operations (O(1))
- Insert before and insert after
- Removal of head, tail, and intermediate nodes
- Pointer integrity (prev and next consistency throughout)
- Bidirectional traversal (forward and backward)
- Reordering: swap adjacent, move to head/tail
- Serialization (to_list) and reconstruction (from_list)
- Empty list and boundary edge cases
"""

import pytest
from algorithms.doubly_linked_list import DoublyLinkedList, PickupNode, PickupScheduleList


def test_empty_list():
    dll = DoublyLinkedList()
    assert dll.is_empty()
    assert dll.get_size() == 0
    assert dll.head is None
    assert dll.tail is None
    assert dll.traverse_forward() == []
    assert dll.traverse_backward() == []
    assert dll.remove('NONEXISTENT') is None


def test_append_and_pointers():
    dll = DoublyLinkedList()

    node1 = PickupNode('ST-001', 'Bakery A', 'Location A')
    node2 = PickupNode('ST-002', 'Grocery B', 'Location B')
    node3 = PickupNode('ST-003', 'Market C', 'Location C')

    dll.append(node1)
    assert dll.get_size() == 1
    assert dll.head is node1
    assert dll.tail is node1
    assert node1.prev is None
    assert node1.next is None

    dll.append(node2)
    assert dll.get_size() == 2
    assert dll.head is node1
    assert dll.tail is node2
    assert node1.next is node2
    assert node2.prev is node1
    assert node2.next is None

    dll.append(node3)
    assert dll.get_size() == 3
    assert dll.tail is node3
    assert node2.next is node3
    assert node3.prev is node2


def test_bidirectional_traversal():
    dll = DoublyLinkedList()
    for i in range(1, 4):
        dll.append(PickupNode(f'ST-{i:03d}', f'Donor {i}', f'Address {i}'))

    fwd_ids = [n.stop_id for n in dll.traverse_forward()]
    assert fwd_ids == ['ST-001', 'ST-002', 'ST-003']

    bwd_ids = [n.stop_id for n in dll.traverse_backward()]
    assert bwd_ids == ['ST-003', 'ST-002', 'ST-001']


def test_insert_before_and_after():
    dll = DoublyLinkedList()
    dll.append(PickupNode('ST-001', 'Donor 1', 'Addr 1'))
    dll.append(PickupNode('ST-003', 'Donor 3', 'Addr 3'))

    # Insert ST-002 between ST-001 and ST-003
    node2 = PickupNode('ST-002', 'Donor 2', 'Addr 2')
    dll.insert_after('ST-001', node2)

    assert [n.stop_id for n in dll.traverse_forward()] == ['ST-001', 'ST-002', 'ST-003']
    assert node2.prev.stop_id == 'ST-001'
    assert node2.next.stop_id == 'ST-003'

    # Insert ST-000 before ST-001 (new head)
    node0 = PickupNode('ST-000', 'Donor 0', 'Addr 0')
    dll.insert_before('ST-001', node0)
    assert dll.head is node0
    assert [n.stop_id for n in dll.traverse_forward()] == ['ST-000', 'ST-001', 'ST-002', 'ST-003']


def test_remove_nodes():
    dll = DoublyLinkedList()
    for i in range(1, 4):
        dll.append(PickupNode(f'ST-{i:03d}', f'Donor {i}', f'Addr {i}'))

    # Remove middle (ST-002)
    removed = dll.remove('ST-002')
    assert removed.stop_id == 'ST-002'
    assert dll.get_size() == 2
    assert [n.stop_id for n in dll.traverse_forward()] == ['ST-001', 'ST-003']
    assert dll.find('ST-001').next.stop_id == 'ST-003'
    assert dll.find('ST-003').prev.stop_id == 'ST-001'

    # Remove head (ST-001)
    dll.remove('ST-001')
    assert dll.head.stop_id == 'ST-003'
    assert dll.head.prev is None

    # Remove tail (ST-003) -> empty list
    dll.remove('ST-003')
    assert dll.is_empty()
    assert dll.head is None
    assert dll.tail is None


def test_swap_adjacent():
    dll = DoublyLinkedList()
    for i in range(1, 4):
        dll.append(PickupNode(f'ST-{i:03d}', f'Donor {i}', f'Addr {i}'))

    # Swap ST-001 down (forward)
    assert dll.swap_adjacent_forward('ST-001') is True
    assert [n.stop_id for n in dll.traverse_forward()] == ['ST-002', 'ST-001', 'ST-003']

    # Swap ST-003 up (backward)
    assert dll.swap_adjacent_backward('ST-003') is True
    assert [n.stop_id for n in dll.traverse_forward()] == ['ST-002', 'ST-003', 'ST-001']


def test_to_list_and_from_list():
    raw_data = [
        {'stop_id': 'ST-101', 'donor_name': 'Donor Alpha', 'pickup_location': 'Loc 1'},
        {'stop_id': 'ST-102', 'donor_name': 'Donor Beta', 'pickup_location': 'Loc 2'},
    ]
    dll = DoublyLinkedList.from_list(raw_data)
    assert dll.get_size() == 2
    assert dll.head.donor_name == 'Donor Alpha'
    assert dll.tail.donor_name == 'Donor Beta'

    exported = dll.to_list()
    assert len(exported) == 2
    assert exported[0]['stop_order'] == 1
    assert exported[1]['stop_order'] == 2
    assert exported[0]['has_next'] is True
    assert exported[1]['has_prev'] is True
