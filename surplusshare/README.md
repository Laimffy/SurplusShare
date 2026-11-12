# SurplusShare — Food Waste Reallocation System

> **Tagline:** *"Share More. Waste Less. Nourish Communities."*

[![Python](https://img.shields.io/badge/Python-3.13-285943?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-6B8E4E?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-795548?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![DSA](https://img.shields.io/badge/DSA-Final%20Project-D7A64B)](.)
[![Tests](https://img.shields.io/badge/Tests-28%20Passed%20(100%25)-success)](.)
[![UN SDG](https://img.shields.io/badge/UN%20SDGs-Zero%20Hunger%20%7C%20Responsible%20Consumption-C77850)](https://sdgs.un.org/goals)

SurplusShare is a modern, full-stack web application designed for university-level Data Structures and Algorithms demonstration. It bridges the gap between commercial surplus food donors (bakeries, groceries, caterers, and markets) and community recipients (pantries, shelters, and feeding programs).

All core algorithms — **FIFO Queues**, **Doubly Linked Lists**, **Merge Sort**, **Linear Search**, **Binary Search**, and the **Automatic Matching Engine** — are implemented **manually in pure Python** without relying on built-in sorting libraries or third-party search engines.

---

## 1. Project Architecture & Modular Design

```
surplusshare/
├── app.py                      # Flask application factory, filters, context processors
├── config.py                   # Centralized application configuration
├── requirements.txt            # Python dependencies (Flask, pytest)
├── README.md                   # Complete academic documentation
├── database/
│   ├── __init__.py
│   ├── db.py                   # SQLite connection management & row factory
│   ├── schema.sql              # Normalized relational SQLite schema
│   ├── seed.py                 # Deterministic sample dataset generator
│   └── surplusshare.db         # Persistent SQLite database file
├── algorithms/
│   ├── __init__.py             # Algorithms package exports
│   ├── fifo_queue.py           # Manual FIFO Queue (collections.deque)
│   ├── doubly_linked_list.py   # Manual Doubly Linked List for pickup stops
│   ├── merge_sort.py           # Manual divide-and-conquer stable Merge Sort
│   ├── linear_search.py        # Manual sequential scan with filter predicates
│   ├── binary_search.py        # Manual lower/upper bound binary search range query
│   └── matching_engine.py      # Integrated deterministic matching engine
├── services/
│   ├── __init__.py
│   ├── listing_service.py      # Food listing CRUD, validation & stats
│   ├── request_service.py      # Recipient requests CRUD & FIFO ordering
│   ├── allocation_service.py   # Allocation history & persistence
│   └── schedule_service.py     # Volunteer schedule management
├── routes/
│   ├── __init__.py
│   ├── main.py                 # Dashboard & landing routes
│   ├── listings.py             # Food listing management routes
│   ├── requests.py             # Recipient request routes
│   ├── matching.py             # Automatic matching engine execution
│   ├── schedule.py             # Doubly linked list pickup route routes
│   ├── search.py               # Linear vs Binary search evaluation
│   ├── monitoring.py           # Real-time expiry countdowns & alerts
│   ├── reports.py              # Visual analytics & CSV export
│   ├── benchmark.py            # Synthetic dataset benchmark suite
│   └── settings.py             # Threshold configuration & project credits
├── static/
│   ├── css/
│   │   └── style.css           # 1,900+ lines custom nature-inspired design system
│   └── js/
│       └── app.js              # Real-time countdowns, Chart.js, Lucide, AJAX benchmark
├── templates/
│   ├── base.html               # Master layout with responsive sidebar and header
│   ├── _sidebar.html           # Forest-green sidebar with Lucide navigation icons
│   ├── _header.html            # Header with quick search, alerts, user info
│   ├── dashboard.html          # Sustainability dashboard with metrics & charts
│   ├── listings.html           # Food surplus catalog with filters & status badges
│   ├── listing_detail.html     # Single listing logistics, expiry & history
│   ├── listing_form.html       # Food entry & validation form
│   ├── requests.html           # Recipient FIFO queue visualization
│   ├── request_form.html       # Community food assistance request form
│   ├── matching.html           # Automated matching engine execution trace
│   ├── schedule.html           # Volunteer pickup schedule list
│   ├── schedule_detail.html    # Interactive Doubly Linked List stop sequence
│   ├── schedule_form.html      # Volunteer schedule creator
│   ├── search.html             # Side-by-side Linear vs Binary search lab
│   ├── monitoring.html         # Expiry watch (Urgent, Warning, Expired)
│   ├── reports.html            # Sustainability impact charts & CSV export
│   ├── benchmark.html          # Interactive multi-query empirical benchmark
│   └── settings.html           # Preferences & academic project details
└── tests/
    ├── conftest.py             # Pytest fixtures with temporary database
    ├── test_fifo_queue.py      # FIFO queue & fair allocation tests
    ├── test_merge_sort.py      # Merge sort correctness, stability & edge cases
    ├── test_search.py          # Linear & Binary search equivalence tests
    ├── test_doubly_linked_list.py # DLL operations & bidirectional traversal
    ├── test_matching_engine.py # Matching engine, shelf life & double allocation tests
    └── test_database_and_routes.py # Flask routes, validation & persistence tests
```

---

## 2. Academic DSA Foundations & Complexity Analysis

### Algorithm 1: FIFO Request Queue (`algorithms/fifo_queue.py`)
- **DSA Concept:** First-In-First-Out (FIFO) Queue via `collections.deque`.
- **Purpose:** Ensures community fairness. Recipient organizations requesting aid earlier are fulfilled strictly in arrival order.
- **Fair Allocation & Partial Fulfillment:**
  - When available food is less than the requested amount, the recipient receives a partial allocation.
  - The remaining need stays at the front of the queue until subsequent surplus becomes available.
  - **Academic Demonstration Scenario:**
    - Pantry A requests 20 loaves.
    - Shelter B requests 30 loaves.
    - Feeding Program C requests 15 loaves.
    - 35 loaves are donated.
    - Result: Pantry A receives 20 (dequeued). Shelter B receives 15 (retained at front with 15 outstanding). Program C remains pending.
- **Complexity:**
  - `enqueue(item)`: $O(1)$ amortized
  - `dequeue()`: $O(1)$
  - `peek()`: $O(1)$
  - Space: $O(n)$ where $n$ is the number of queued requests.

### Algorithm 2: Merge Sort for Expiry Prioritization (`algorithms/merge_sort.py`)
- **DSA Concept:** Divide-and-Conquer Sorting.
- **Manual Implementation:** Does **not** invoke Python's built-in `sort()` or `sorted()`.
- **Stability Guarantee:** Uses `<=` during the merge phase so that equal expiry timestamps preserve their original posting precedence.
- **Complexity:**
  - Best, Average, Worst Case: $O(n \log n)$
  - Auxiliary Space: $O(n)$ for temporary sublist buffers.

### Algorithm 3: Linear Search vs. Binary Search (`algorithms/linear_search.py`, `algorithms/binary_search.py`)
- **Linear Search:** Scans all $n$ listings sequentially. Complexity: $O(n)$ per query.
- **Binary Search (Range Window Query):** Operates on listings pre-sorted by Merge Sort.
  - `binary_search_lower_bound`: Finds the leftmost element where `expiry_at >= start_window` in $O(\log n)$.
  - `binary_search_upper_bound`: Finds the rightmost element where `expiry_at <= end_window` in $O(\log n)$.
  - Range Scan: Iterates across the $k$ elements within the bounds and applies secondary filters in $O(k)$.
  - Total Query Complexity: $O(\log n + k)$.
- **Empirical Break-Even Amortization Equation:**
  $$\text{Workload}_{\text{Linear}} = Q \cdot T_{\text{linear}}$$
  $$\text{Workload}_{\text{Sorted}} = T_{\text{sort}} + Q \cdot T_{\text{binary}}$$
  $$\text{Break-Even Query Threshold: } Q_{\text{break-even}} = \left\lceil \frac{T_{\text{sort}}}{T_{\text{linear}} - T_{\text{binary}}} \right\rceil$$

### Algorithm 4: Doubly Linked List for Pickup Schedules (`algorithms/doubly_linked_list.py`)
- **DSA Concept:** Bidirectional Linked List with `prev` and `next` pointers.
- **Nodes (`PickupNode`):** Stores `stop_id`, `donor_name`, `pickup_location`, `scheduled_time`, `status`, `prev`, and `next`.
- **Operations:**
  - `append(node)`, `prepend(node)`: $O(1)$
  - `insert_after(target_id, node)`, `insert_before(target_id, node)`: $O(1)$ via node hash map index.
  - `remove(stop_id)`: $O(1)$
  - `swap_adjacent_forward(stop_id)`, `swap_adjacent_backward(stop_id)`: $O(1)$ pointer exchange.
  - `traverse_forward()`, `traverse_backward()`: $O(n)$ bidirectional traversal.

### Algorithm 5: Automatic Food Matching Engine (`algorithms/matching_engine.py`)
- Coordinates the complete reallocation pipeline:
  1. Validates and excludes expired or fully allocated surplus.
  2. Applies **Merge Sort** to rank listings by earliest expiry time.
  3. Uses **FIFO Queues** to match recipient requests in arrival order.
  4. Enforces minimum acceptable shelf life (`min_shelf_life_hours`) and unit compatibility.
  5. Computes fair allocations and writes changes to the database inside an atomic transaction.

---

## 3. Visual Identity & Color System

| Token | Hex | UI Application |
|---|---|---|
| **Forest Green** | `#285943` | Primary branding, sidebar, headings, card headers |
| **Leaf Green** | `#6B8E4E` | Primary action buttons, active states, fresh badges |
| **Sage Green** | `#A8BFA0` | Soft accents, subtle badge backgrounds, borders |
| **Cream** | `#FAF7EF` | Global application background |
| **Warm Ivory** | `#FFFDF8` | Card and modal surface background |
| **Earth Brown** | `#795548` | Secondary typography, metadata, subtle borders |
| **Terracotta** | `#C77850` | Expiry urgency warnings (&lt;6h), delete buttons |
| **Harvest Gold**| `#D7A64B` | Impact statistics, warning badges (&lt;24h) |
| **Charcoal** | `#29352C` | High-contrast readable body text |

**Typography:**
- Primary Body: **DM Sans** (Google Fonts)
- Headings & Branding: **Lora** (Google Fonts)

---

## 4. Installation & Local Setup

The system runs entirely locally and requires **no external paid cloud services**.

### Prerequisites
- Python 3.10 or higher
- pip package manager

### Step 1: Navigate to the Project Directory
```powershell
cd "d:\3rd year\DSA_Final_Project\surplusshare"
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Initialize and Seed the Database
```powershell
python -c "from app import create_app; from database.db import init_db; from database.seed import seed_database
app = create_app()
with app.app_context():
    init_db()
    seed_database()
    print('Database initialized and seeded successfully!')"
```

### Step 4: Run the Application
```powershell
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

---

## 5. Running Automated Tests

SurplusShare includes 28 automated unit and integration tests using `pytest`.

Run all tests:
```powershell
pytest -v
```

### Test Suite Coverage
- `tests/test_fifo_queue.py`: FIFO ordering, dequeue, peek, fair allocation, 35-loaves scenario.
- `tests/test_merge_sort.py`: Divide-and-conquer correctness, stability, edge cases, SortTracker.
- `tests/test_search.py`: Lower/upper bounds, range queries, 100% equivalence of Linear vs Binary.
- `tests/test_doubly_linked_list.py`: Insertion, unlinking, pointer integrity, bidirectional traversals.
- `tests/test_matching_engine.py`: Priority matching, shelf life checks, prevention of duplicate allocation.
- `tests/test_database_and_routes.py`: Flask status codes, validation rules, transactional persistence.

---

## 6. Academic License & Credits
- **Course:** Data Structures and Algorithms (DSA) Final Project
- **University:** Bachelor of Science in Computer Engineering / Computer Science
- **United Nations Sustainable Development Goals:**
  - **SDG 2:** Zero Hunger
  - **SDG 12:** Responsible Consumption and Production
