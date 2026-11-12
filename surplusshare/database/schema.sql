-- SurplusShare Database Schema
-- Food Waste Reallocation System

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'donor', 'recipient', 'volunteer')),
    organization TEXT,
    email TEXT,
    password_hash TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Food listings table
CREATE TABLE IF NOT EXISTS food_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id TEXT UNIQUE NOT NULL,
    food_name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('Bakery', 'Vegetables', 'Fruits', 'Prepared Meals', 'Dairy', 'Dry Goods', 'Other')),
    quantity REAL NOT NULL CHECK (quantity > 0),
    unit TEXT NOT NULL,
    donor_name TEXT NOT NULL,
    donor_id INTEGER REFERENCES users(id),
    posted_at TEXT NOT NULL,
    expiry_at TEXT NOT NULL,
    pickup_location TEXT NOT NULL,
    storage_requirements TEXT DEFAULT '',
    food_condition TEXT DEFAULT 'Good',
    status TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'partially_allocated', 'fully_allocated', 'expired', 'cancelled')),
    allocated_quantity REAL NOT NULL DEFAULT 0 CHECK (allocated_quantity >= 0),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Recipient requests table
CREATE TABLE IF NOT EXISTS recipient_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT UNIQUE NOT NULL,
    organization_name TEXT NOT NULL,
    food_category TEXT NOT NULL,
    requested_quantity REAL NOT NULL CHECK (requested_quantity > 0),
    quantity_unit TEXT NOT NULL,
    min_shelf_life_hours REAL DEFAULT 0,
    requested_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'partially_fulfilled', 'fulfilled', 'cancelled', 'expired')),
    fulfilled_quantity REAL NOT NULL DEFAULT 0 CHECK (fulfilled_quantity >= 0),
    recipient_id INTEGER REFERENCES users(id),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Allocations table
CREATE TABLE IF NOT EXISTS allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    allocation_id TEXT UNIQUE NOT NULL,
    listing_id INTEGER NOT NULL REFERENCES food_listings(id),
    request_id INTEGER NOT NULL REFERENCES recipient_requests(id),
    allocated_quantity REAL NOT NULL CHECK (allocated_quantity > 0),
    allocated_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'picked_up', 'delivered', 'confirmed', 'cancelled')),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Pickup schedules table
CREATE TABLE IF NOT EXISTS pickup_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id TEXT UNIQUE NOT NULL,
    volunteer_name TEXT NOT NULL,
    schedule_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'in_progress', 'completed', 'cancelled')),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Pickup stops table
CREATE TABLE IF NOT EXISTS pickup_stops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stop_id TEXT UNIQUE NOT NULL,
    schedule_id INTEGER NOT NULL REFERENCES pickup_schedules(id),
    donor_name TEXT NOT NULL,
    pickup_location TEXT NOT NULL,
    listing_id INTEGER REFERENCES food_listings(id),
    scheduled_time TEXT NOT NULL,
    stop_order INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'skipped', 'cancelled')),
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for food_listings
CREATE INDEX IF NOT EXISTS idx_food_listings_category ON food_listings(category);
CREATE INDEX IF NOT EXISTS idx_food_listings_status ON food_listings(status);
CREATE INDEX IF NOT EXISTS idx_food_listings_expiry_at ON food_listings(expiry_at);
CREATE INDEX IF NOT EXISTS idx_food_listings_donor_name ON food_listings(donor_name);

-- Indexes for recipient_requests
CREATE INDEX IF NOT EXISTS idx_recipient_requests_food_category ON recipient_requests(food_category);
CREATE INDEX IF NOT EXISTS idx_recipient_requests_status ON recipient_requests(status);
CREATE INDEX IF NOT EXISTS idx_recipient_requests_requested_at ON recipient_requests(requested_at);

-- Indexes for allocations
CREATE INDEX IF NOT EXISTS idx_allocations_listing_id ON allocations(listing_id);
CREATE INDEX IF NOT EXISTS idx_allocations_request_id ON allocations(request_id);
CREATE INDEX IF NOT EXISTS idx_allocations_status ON allocations(status);

-- Indexes for pickup_stops
CREATE INDEX IF NOT EXISTS idx_pickup_stops_schedule_id ON pickup_stops(schedule_id);
CREATE INDEX IF NOT EXISTS idx_pickup_stops_stop_order ON pickup_stops(stop_order);

-- Security Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    role TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details TEXT,
    ip_address TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);

-- Philippine Partners Table (Confirmed & Prospective)
CREATE TABLE IF NOT EXISTS partners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('Restaurant', 'Fast-Food', 'Bakery', 'Supermarket & Grocery', 'Catering', 'Local Food Establishment', 'NGO / Community')),
    location TEXT NOT NULL,
    description TEXT NOT NULL,
    logo_url TEXT,
    status TEXT NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'prospective')),
    website_url TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_partners_status ON partners(status);
CREATE INDEX IF NOT EXISTS idx_partners_category ON partners(category);

-- News and Announcements Table
CREATE TABLE IF NOT EXISTS news_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('Activity', 'Announcement', 'Awareness', 'Story', 'Update')),
    content TEXT NOT NULL,
    excerpt TEXT,
    author_name TEXT DEFAULT 'SurplusShare Team',
    is_published INTEGER NOT NULL DEFAULT 1,
    published_at TEXT DEFAULT CURRENT_TIMESTAMP,
    image_url TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_news_articles_is_published ON news_articles(is_published);
CREATE INDEX IF NOT EXISTS idx_news_articles_slug ON news_articles(slug);

-- Frequently Asked Questions (FAQs) Table
CREATE TABLE IF NOT EXISTS faqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('Donating Food', 'Receiving Food', 'Matching & Algorithms', 'Volunteering & Pickups', 'Partnerships', 'General')),
    order_index INTEGER DEFAULT 0,
    is_published INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_faqs_category ON faqs(category);
CREATE INDEX IF NOT EXISTS idx_faqs_is_published ON faqs(is_published);

-- Contact Inquiries Table
CREATE TABLE IF NOT EXISTS contact_inquiries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    organization TEXT,
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'read', 'responded', 'archived')),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_contact_inquiries_status ON contact_inquiries(status);

