"""Seed the database with realistic sample data for SurplusShare."""

import click
from datetime import datetime, timedelta
from flask import current_app
from database.db import get_db, init_db


def seed_database():
    """Populate the database with realistic sample data.

    Creates users, food listings, recipient requests, allocations,
    and pickup schedules with stops. All timestamps are calculated
    relative to the current time so the data stays fresh.
    """
    db = get_db()
    now = datetime.now()

    from werkzeug.security import generate_password_hash
    default_pwd_hash = generate_password_hash('password123')

    # Ensure password_hash column exists in users table
    try:
        user_cols = [row['name'] for row in db.execute("PRAGMA table_info(users)").fetchall()]
        if 'password_hash' not in user_cols:
            db.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
            db.commit()
    except Exception:
        pass

    # ── Users ──────────────────────────────────────────────────────────
    users = [
        ('admin_user', 'Admin User', 'admin', None, 'admin@surplusshare.ph', default_pwd_hash),
        ('green_basket', 'Green Basket Grocery', 'donor', 'Green Basket Grocery', 'contact@greenbasket.ph', default_pwd_hash),
        ('sunrise_bakery', 'Sunrise Bakery', 'donor', 'Sunrise Bakery', 'hello@sunrisebakery.ph', default_pwd_hash),
        ('harvest_kitchen', 'Harvest Kitchen', 'donor', 'Harvest Kitchen', 'info@harvestkitchen.ph', default_pwd_hash),
        ('fresh_fields', 'Fresh Fields Market', 'donor', 'Fresh Fields Market', 'orders@freshfields.ph', default_pwd_hash),
        ('community_pantry_a', 'Community Pantry A', 'recipient', 'Community Pantry A', 'pantry_a@community.ph', default_pwd_hash),
        ('hope_feeding', 'Hope Feeding Program', 'recipient', 'Hope Feeding Program', 'contact@hopefeeding.ph', default_pwd_hash),
        ('brgy_food_center', 'Barangay Food Center', 'recipient', 'Barangay Food Center', 'brgyfoodcenter@gov.ph', default_pwd_hash),
        ('helping_hands', 'Helping Hands Shelter', 'recipient', 'Helping Hands Shelter', 'info@helpinghands.ph', default_pwd_hash),
        ('juan_volunteer', 'Juan Volunteer', 'volunteer', None, 'juan@volunteer.ph', default_pwd_hash),
        ('maria_volunteer', 'Maria Volunteer', 'volunteer', None, 'maria@volunteer.ph', default_pwd_hash),
    ]

    for u in users:
        db.execute(
            """INSERT OR IGNORE INTO users (username, display_name, role, organization, email, password_hash)
               VALUES (?, ?, ?, ?, ?, ?)""",
            u,
        )
        # Update existing records without password
        db.execute(
            "UPDATE users SET password_hash = ? WHERE username = ? AND (password_hash IS NULL OR password_hash = '')",
            (default_pwd_hash, u[0]),
        )

    # ── Food Listings ─────────────────────────────────────────────────
    listings = [
        # (listing_id, food_name, category, qty, unit, donor_name, donor_idx(1-based), posted_offset_hrs, expiry_offset_hrs, location, storage, condition, status, alloc_qty)
        ('FL-001', 'Pandesal Bread Rolls', 'Bakery', 50.0, 'pieces', 'Sunrise Bakery', 3,
         -2, 10, '78 Maginhawa Street, Quezon City', 'Room temperature', 'Good', 'available', 0),
        ('FL-002', 'Ensaymada Pastries', 'Bakery', 30.0, 'pieces', 'Sunrise Bakery', 3,
         -4, 8, '78 Maginhawa Street, Quezon City', 'Room temperature', 'Good', 'available', 0),
        ('FL-003', 'Fresh Kangkong', 'Vegetables', 20.0, 'kg', 'Green Basket Grocery', 2,
         -3, 36, '123 Rizal Avenue, Quezon City', 'Refrigerated', 'Good', 'available', 0),
        ('FL-004', 'Fresh Pechay', 'Vegetables', 15.0, 'kg', 'Green Basket Grocery', 2,
         -6, 30, '123 Rizal Avenue, Quezon City', 'Refrigerated', 'Good', 'available', 0),
        ('FL-005', 'Ripe Lakatan Bananas', 'Fruits', 25.0, 'kg', 'Fresh Fields Market', 5,
         -5, 20, '290 Commonwealth Avenue, Quezon City', 'Room temperature', 'Good', 'available', 0),
        ('FL-006', 'Carabao Mangoes', 'Fruits', 30.0, 'kg', 'Fresh Fields Market', 5,
         -8, 48, '290 Commonwealth Avenue, Quezon City', 'Room temperature', 'Good', 'available', 0),
        ('FL-007', 'Chicken Adobo', 'Prepared Meals', 40.0, 'servings', 'Harvest Kitchen', 4,
         -1, 4, '45 Bonifacio Street, Makati', 'Refrigerated', 'Good', 'available', 0),
        ('FL-008', 'Sinigang na Baboy', 'Prepared Meals', 35.0, 'servings', 'Harvest Kitchen', 4,
         -2, 5, '45 Bonifacio Street, Makati', 'Refrigerated', 'Good', 'available', 0),
        ('FL-009', 'Pancit Canton Noodles', 'Prepared Meals', 50.0, 'servings', 'Harvest Kitchen', 4,
         -3, 3, '45 Bonifacio Street, Makati', 'Refrigerated', 'Fair', 'available', 0),
        ('FL-010', 'Fresh Carabao Milk', 'Dairy', 20.0, 'liters', 'Green Basket Grocery', 2,
         -4, 18, '123 Rizal Avenue, Quezon City', 'Refrigerated', 'Good', 'available', 0),
        ('FL-011', 'Kesong Puti', 'Dairy', 10.0, 'kg', 'Fresh Fields Market', 5,
         -6, 72, '290 Commonwealth Avenue, Quezon City', 'Refrigerated', 'Good', 'available', 0),
        ('FL-012', 'White Rice (Sinandomeng)', 'Dry Goods', 100.0, 'kg', 'Green Basket Grocery', 2,
         -12, 720, '123 Rizal Avenue, Quezon City', 'Cool dry place', 'Good', 'available', 0),
        ('FL-013', 'Canned Sardines', 'Dry Goods', 60.0, 'cans', 'Fresh Fields Market', 5,
         -24, 2160, '290 Commonwealth Avenue, Quezon City', 'Room temperature', 'Good', 'available', 0),
        ('FL-014', 'Instant Noodles (Lucky Me)', 'Dry Goods', 48.0, 'packs', 'Green Basket Grocery', 2,
         -10, 1440, '123 Rizal Avenue, Quezon City', 'Room temperature', 'Good', 'available', 0),
        ('FL-015', 'Ube Halaya', 'Other', 15.0, 'kg', 'Sunrise Bakery', 3,
         -5, 24, '78 Maginhawa Street, Quezon City', 'Refrigerated', 'Good', 'available', 0),
        ('FL-016', 'Leftover Lechon', 'Prepared Meals', 10.0, 'kg', 'Harvest Kitchen', 4,
         -26, -2, '45 Bonifacio Street, Makati', 'Refrigerated', 'Fair', 'expired', 0),
        ('FL-017', 'Day-Old Monay Bread', 'Bakery', 40.0, 'pieces', 'Sunrise Bakery', 3,
         -30, -6, '78 Maginhawa Street, Quezon City', 'Room temperature', 'Fair', 'expired', 0),
        ('FL-018', 'Arroz Caldo', 'Prepared Meals', 30.0, 'servings', 'Harvest Kitchen', 4,
         -8, 60, '45 Bonifacio Street, Makati', 'Refrigerated', 'Good', 'fully_allocated', 30),
        ('FL-019', 'Fresh Tomatoes', 'Vegetables', 18.0, 'kg', 'Fresh Fields Market', 5,
         -7, 42, '290 Commonwealth Avenue, Quezon City', 'Room temperature', 'Good', 'available', 0),
        ('FL-020', 'Calamansi Fruits', 'Fruits', 12.0, 'kg', 'Green Basket Grocery', 2,
         -3, 96, '123 Rizal Avenue, Quezon City', 'Room temperature', 'Good', 'available', 0),
    ]

    for item in listings:
        (lid, name, cat, qty, unit, donor, donor_idx,
         posted_h, expiry_h, loc, storage, cond, status, alloc_qty) = item
        posted_at = (now + timedelta(hours=posted_h)).strftime('%Y-%m-%dT%H:%M:%S')
        expiry_at = (now + timedelta(hours=expiry_h)).strftime('%Y-%m-%dT%H:%M:%S')
        db.execute(
            """INSERT OR IGNORE INTO food_listings
               (listing_id, food_name, category, quantity, unit, donor_name, donor_id,
                posted_at, expiry_at, pickup_location, storage_requirements,
                food_condition, status, allocated_quantity)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (lid, name, cat, qty, unit, donor, donor_idx,
             posted_at, expiry_at, loc, storage, cond, status, alloc_qty),
        )

    # ── Recipient Requests ────────────────────────────────────────────
    requests_data = [
        ('RR-001', 'Community Pantry A', 'Bakery', 30.0, 'pieces', 0, -1, 'pending', 0, 6),
        ('RR-002', 'Hope Feeding Program', 'Prepared Meals', 50.0, 'servings', 2, -3, 'pending', 0, 7),
        ('RR-003', 'Barangay Food Center', 'Vegetables', 25.0, 'kg', 0, -2, 'pending', 0, 8),
        ('RR-004', 'Helping Hands Shelter', 'Fruits', 20.0, 'kg', 0, -4, 'pending', 0, 9),
        ('RR-005', 'Community Pantry A', 'Dry Goods', 50.0, 'kg', 0, -6, 'pending', 0, 6),
        ('RR-006', 'Hope Feeding Program', 'Dairy', 10.0, 'liters', 4, -5, 'pending', 0, 7),
        ('RR-007', 'Barangay Food Center', 'Prepared Meals', 30.0, 'servings', 0, -8, 'partially_fulfilled', 15, 8),
        ('RR-008', 'Helping Hands Shelter', 'Bakery', 40.0, 'pieces', 0, -10, 'pending', 0, 9),
        ('RR-009', 'Community Pantry A', 'Prepared Meals', 30.0, 'servings', 0, -12, 'fulfilled', 30, 6),
        ('RR-010', 'Hope Feeding Program', 'Vegetables', 15.0, 'kg', 0, -7, 'pending', 0, 7),
    ]

    for req in requests_data:
        (rid, org, cat, qty, unit, shelf, req_h, status, fulfilled, recip_id) = req
        requested_at = (now + timedelta(hours=req_h)).strftime('%Y-%m-%dT%H:%M:%S')
        db.execute(
            """INSERT OR IGNORE INTO recipient_requests
               (request_id, organization_name, food_category, requested_quantity,
                quantity_unit, min_shelf_life_hours, requested_at, status,
                fulfilled_quantity, recipient_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (rid, org, cat, qty, unit, shelf, requested_at, status, fulfilled, recip_id),
        )

    # ── Allocations ───────────────────────────────────────────────────
    allocations = [
        ('AL-001', 18, 7, 15.0, -1, 'pending'),   # listing pk=18 (Arroz Caldo) -> request pk=7 (Brgy Food Center partial)
        ('AL-002', 18, 9, 30.0, -12, 'confirmed'), # listing pk=18 -> request pk=9 (Community Pantry fulfilled)
    ]

    for alloc in allocations:
        (aid, l_pk, r_pk, qty, alloc_h, status) = alloc
        allocated_at = (now + timedelta(hours=alloc_h)).strftime('%Y-%m-%dT%H:%M:%S')
        db.execute(
            """INSERT OR IGNORE INTO allocations
               (allocation_id, listing_id, request_id, allocated_quantity,
                allocated_at, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (aid, l_pk, r_pk, qty, allocated_at, status),
        )

    # ── Pickup Schedule ───────────────────────────────────────────────
    schedule_date = (now + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%S')
    db.execute(
        """INSERT OR IGNORE INTO pickup_schedules
           (schedule_id, volunteer_name, schedule_date, status)
           VALUES (?, ?, ?, ?)""",
        ('PS-001', 'Juan Volunteer', schedule_date, 'planned'),
    )

    # get the schedule pk
    sched_row = db.execute("SELECT id FROM pickup_schedules WHERE schedule_id = ?", ('PS-001',)).fetchone()
    sched_pk = sched_row['id'] if sched_row else 1

    stops = [
        ('ST-001', sched_pk, 'Sunrise Bakery', '78 Maginhawa Street, Quezon City', 1,
         (now + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%S'), 1, 'pending', 'Pick up pandesal and ensaymada'),
        ('ST-002', sched_pk, 'Green Basket Grocery', '123 Rizal Avenue, Quezon City', 3,
         (now + timedelta(hours=2, minutes=30)).strftime('%Y-%m-%dT%H:%M:%S'), 2, 'pending', 'Pick up kangkong and pechay'),
        ('ST-003', sched_pk, 'Harvest Kitchen', '45 Bonifacio Street, Makati', 7,
         (now + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%S'), 3, 'pending', 'Pick up chicken adobo'),
        ('ST-004', sched_pk, 'Fresh Fields Market', '290 Commonwealth Avenue, Quezon City', 5,
         (now + timedelta(hours=3, minutes=30)).strftime('%Y-%m-%dT%H:%M:%S'), 4, 'pending', 'Pick up bananas and mangoes'),
    ]

    for stop in stops:
        (sid, sch_pk, donor, loc, l_pk, stime, order, status, notes) = stop
        db.execute(
            """INSERT OR IGNORE INTO pickup_stops
               (stop_id, schedule_id, donor_name, pickup_location, listing_id,
                scheduled_time, stop_order, status, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (sid, sch_pk, donor, loc, l_pk, stime, order, status, notes),
        )

    # ── Philippine Partners ───────────────────────────────────────────
    # Confirmed Collaborating Partners
    confirmed_partners = [
        ('Sunrise Bakery', 'Bakery', '78 Maginhawa St., Quezon City',
         'Artisanal community bakery providing day-fresh surplus pandesal, loaves, and ensaymada to local pantries.',
         'confirmed', 'https://sunrisebakery.ph', 'hello@sunrisebakery.ph', '+63 (2) 8921-4455'),
        ('Green Basket Grocery', 'Supermarket & Grocery', '123 Rizal Ave., Quezon City',
         'Neighborhood organic and staple grocer redistributing surplus leafy greens, root vegetables, and dry pantry items.',
         'confirmed', 'https://greenbasket.ph', 'partners@greenbasket.ph', '+63 (2) 8734-1122'),
        ('Harvest Kitchen', 'Catering', '45 Bonifacio St., Makati City',
         'Events and institutional caterer packaging prepared chef-cooked meals into safe, chilled family servings.',
         'confirmed', 'https://harvestkitchen.ph', 'outreach@harvestkitchen.ph', '+63 (2) 8812-9900'),
        ('Fresh Fields Market', 'Supermarket & Grocery', '290 Commonwealth Ave., Quezon City',
         'Wholesale and retail produce market supplying fresh seasonal fruits, citrus, and staple goods.',
         'confirmed', 'https://freshfields.ph', 'sustainability@freshfields.ph', '+63 (2) 8931-5566'),
        ('Maginhawa Community Pantry Hub', 'NGO / Community', 'Maginhawa St., Quezon City',
         'Grassroots community redistribution center organizing free food distribution for underprivileged families.',
         'confirmed', 'https://maginhawapantry.ph', 'pantry@maginhawa.ph', '+63 917 555 0192'),
        ('Hope Feeding Program', 'NGO / Community', 'Tondo, Manila',
         'Non-profit daily kitchen providing warm, nutritious meals to over 300 children and seniors.',
         'confirmed', 'https://hopefeeding.org.ph', 'contact@hopefeeding.ph', '+63 (2) 8245-7788'),
        ('Kusina ng Kalinga QC', 'Local Food Establishment', 'Cubao, Quezon City',
         'Community kitchen offering affordable healthy meals and redistributing unserved batch dishes.',
         'confirmed', '', 'kusina@kalinga.ph', '+63 920 441 2309'),
    ]

    for p in confirmed_partners:
        db.execute(
            """INSERT OR IGNORE INTO partners
               (name, category, location, description, status, website_url, contact_email, contact_phone)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            p,
        )

    # Prospective Partners (Distinctly Identified — In Outreach/Discussion Stage)
    # Important: Clearly separated to avoid false claims regarding major Philippine food chains
    prospective_partners = [
        ('Jollibee Group Foundation (Outreach Stage)', 'Fast-Food', 'Pasig City, Metro Manila',
         'Prospective collaboration in exploratory talks for surplus bread and safe unserved food redirection.',
         'prospective', 'https://jollibeegroupfoundation.org', 'outreach@jollibee.com.ph', '+63 (2) 8634-1111'),
        ('Max''s Group Community Outreach (Exploratory)', 'Restaurant', 'Makati City, Metro Manila',
         'In active dialogue for bakery and banquet surplus food recovery protocols.',
         'prospective', 'https://maxsgroupinc.com', 'csr@maxsgroupinc.com', '+63 (2) 8784-9000'),
        ('Robinsons Supermarket CSR (In Discussion)', 'Supermarket & Grocery', 'Quezon City, Metro Manila',
         'Prospective retail partner discussing produce and dairy reallocation safety guidelines.',
         'prospective', 'https://robinsonsretailholdings.com.ph', 'csr@robinsons.com.ph', '+63 (2) 8635-0751'),
        ('Mang Inasal Philippines (Prospective)', 'Restaurant', 'Mandaluyong City, Metro Manila',
         'Prospective outreach regarding side dish and rice redirection for community pantries.',
         'prospective', '', 'partnerships@manginasal.ph', ''),
        ('San Miguel Food Group Outreach (Prospective)', 'Local Food Establishment', 'Mandaluyong City, Metro Manila',
         'Exploratory discussions on packaged dry goods and dairy logistics support.',
         'prospective', 'https://sanmiguel.com.ph', 'community@sanmiguel.com.ph', '+63 (2) 8632-3000'),
    ]

    for p in prospective_partners:
        db.execute(
            """INSERT OR IGNORE INTO partners
               (name, category, location, description, status, website_url, contact_email, contact_phone)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            p,
        )

    # ── News and Announcements ────────────────────────────────────────
    articles = [
        ('SurplusShare Rescues 420 kg of Fresh Food Across Metro Manila',
         'surplusshare-rescues-420kg-fresh-food',
         'Activity',
         'Over the past month, SurplusShare successfully redistributed 420 kilograms of bakery items, fresh vegetables, and chef-prepared meals. Through the coordinated effort of community pantries in Quezon City and Manila, over 1,200 meal equivalents were provided to families in need, completely diverting wholesome food from local landfills.',
         'Over 420 kilograms of fresh bakery products and vegetables were successfully matched and delivered to community pantries.',
         'SurplusShare Team', 1, (now - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%S')),
        ('How Merge Sort and FIFO Queues Power Fair Food Reallocation',
         'how-merge-sort-and-fifo-queues-power-food-reallocation',
         'Awareness',
         'Food reallocation is not just about moving boxes; it is a time-sensitive algorithmic optimization problem. By employing Merge Sort (O(n log n)), SurplusShare prioritizes food with the earliest expiry timestamps. Requests are managed via strict FIFO queues (O(1)), ensuring that community pantries receive equitable access without donor favoritism or starvation.',
         'An in-depth look at how classic computer science algorithms solve real-world hunger and logistical waste.',
         'DSA Research Team', 1, (now - timedelta(days=5)).strftime('%Y-%m-%dT%H:%M:%S')),
        ('Sunrise Bakery Celebrates 500 Batches of Shared Bread',
         'sunrise-bakery-celebrates-500-batches-shared',
         'Story',
         'Maginhawa landmark Sunrise Bakery has now contributed its 500th batch of freshly baked pandesal and bread rolls to the SurplusShare network. Owner Maria Santos shared: "Before SurplusShare, managing unsold evening bread was painful. Now, every single roll nourishes a breakfast table in our neighboring barangay."',
         'Local artisanal bakery Sunrise Bakery marks a heartwarming milestone in reducing daily bakery surplus.',
         'Community Relations', 1, (now - timedelta(days=9)).strftime('%Y-%m-%dT%H:%M:%S')),
        ('Volunteer Guide: Navigating Pickup Routes with Doubly Linked Lists',
         'volunteer-guide-navigating-pickup-routes',
         'Update',
         'Our volunteer drivers can now reorder and inspect pickup routes interactively. The Doubly Linked List structure allows dispatchers to dynamically swap stops, perform backward route reviews from delivery destinations, and recalculate ETAs in real-time.',
         'New routing capabilities allow volunteer drivers to view forward routes and reverse route checklists seamlessly.',
         'Logistics Coordinator', 1, (now - timedelta(days=14)).strftime('%Y-%m-%dT%H:%M:%S')),
        ('Advancing UN SDG 2 & SDG 12 in the Philippine Context',
         'advancing-un-sdg-2-and-sdg-12-philippines',
         'Awareness',
         'The United Nations Sustainable Development Goal 2 aims for Zero Hunger, while Goal 12 targets Responsible Consumption and Production. In the Philippines, millions experience food insecurity while metric tons of edible food reach disposal. SurplusShare bridges this gap using ethical tech.',
         'Examining our localized impact on sustainable production, landfill reduction, and community nutrition.',
         'Sustainability Desk', 1, (now - timedelta(days=20)).strftime('%Y-%m-%dT%H:%M:%S')),
    ]

    for a in articles:
        db.execute(
            """INSERT OR IGNORE INTO news_articles
               (title, slug, category, content, excerpt, author_name, is_published, published_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            a,
        )

    # ── Frequently Asked Questions (FAQs) ─────────────────────────────
    faqs = [
        ('How can restaurants, bakeries, and caterers donate surplus food?',
         'Registered food donors can log into the SurplusShare Donor Portal, enter food details (name, category, quantity, safe expiry timestamp, and pickup address), and submit the listing. Our system will immediately evaluate matching recipient requests and schedule volunteer pickup.',
         'Donating Food', 1, 1),
        ('Who can become a verified food donor?',
         'Licensed restaurants, bakeries, supermarkets, hotel kitchens, caterers, and food manufacturers in Metro Manila and neighboring areas can register as donors. All food must be prepared, stored, and packaged according to Philippine food hygiene and safety standards.',
         'Donating Food', 2, 1),
        ('Who is eligible to receive surplus food donations?',
         'Registered community pantries, soup kitchens, charitable shelters, feeding programs, and barangay relief centers are eligible. Each organization specifies its needed food categories, batch capacity, and preparation shelf-life thresholds.',
         'Receiving Food', 3, 1),
        ('How does the automatic food matching engine work?',
         'Our matching engine executes a deterministic two-phase algorithm. First, Merge Sort sorts all available surplus by expiry timestamp ascending (earliest expiry first). Second, category-partitioned FIFO queues match the food with the longest-waiting eligible recipient organization with fair partial fulfillment.',
         'Matching & Algorithms', 4, 1),
        ('How does SurplusShare handle food approaching its expiry date?',
         'Food within 24 hours of expiry triggers visual warning badges, while food with under 6 hours remaining is flagged as Urgent Critical Priority. The system automatically alerts nearby pantries capable of immediate distribution.',
         'Donating Food', 5, 1),
        ('How can volunteers participate in food pickups and delivery?',
         'Volunteers can sign up for the Volunteer Driver Portal. Once registered, volunteers are assigned pickup routes sequenced as Doubly Linked Lists, allowing step-by-step route checklists and bidirectional route adjustments.',
         'Volunteering & Pickups', 6, 1),
        ('How can a business become an official partner?',
         'Businesses can submit an inquiry through our Contact Us page or email partnerships@surplusshare.ph. Our team conducts a brief verification of kitchen facilities and food handling procedures before granting confirmed partner status.',
         'Partnerships', 7, 1),
        ('Is there any financial cost to use SurplusShare?',
         'No. SurplusShare is a non-profit academic platform committed to community welfare and food rescue. Registration, matching, and platform access are 100% free for both donors and community pantries.',
         'General', 8, 1),
    ]

    for f in faqs:
        db.execute(
            """INSERT OR IGNORE INTO faqs
               (question, answer, category, order_index, is_published)
               VALUES (?, ?, ?, ?, ?)""",
            f,
        )

    # ── Initial Security Audit Logs ───────────────────────────────────
    audit_samples = [
        (1, 'admin_user', 'admin', 'SYSTEM_INITIALIZATION', 'system', 'sys-01', 'Database seeded and security RBAC initialized.', '127.0.0.1', (now - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S')),
        (3, 'sunrise_bakery', 'donor', 'CREATE_LISTING', 'food_listings', 'FL-001', 'Posted 50 pieces of Pandesal Bread Rolls.', '127.0.0.1', (now - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%S')),
        (1, 'admin_user', 'admin', 'EXECUTE_MATCHING', 'matching_engine', 'BATCH-001', 'Executed deterministic Merge Sort + FIFO allocation engine.', '127.0.0.1', (now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S')),
    ]

    for aud in audit_samples:
        db.execute(
            """INSERT OR IGNORE INTO audit_logs
               (user_id, username, role, action, resource_type, resource_id, details, ip_address, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            aud,
        )

    db.commit()


@click.command('seed-db')
def seed_db_command():
    """CLI command to seed the database with sample data."""
    init_db()
    seed_database()
    click.echo('Database seeded with sample data.')
