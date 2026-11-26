"""SQLite schema, connection helpers and first-run initialisation."""
import os
import sqlite3
from contextlib import contextmanager

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('Admin', 'Cashier')),
    full_name TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    contact_person TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE COLLATE NOCASE,
    barcode TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    brand TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
    serial_number TEXT NOT NULL DEFAULT '',
    warranty_months INTEGER NOT NULL DEFAULT 0 CHECK (warranty_months >= 0),
    cost_price REAL NOT NULL CHECK (cost_price >= 0),
    selling_price REAL NOT NULL CHECK (selling_price >= 0),
    stock_qty INTEGER NOT NULL DEFAULT 0 CHECK (stock_qty >= 0),
    reorder_level INTEGER NOT NULL DEFAULT 5 CHECK (reorder_level >= 0),
    stock_status TEXT NOT NULL DEFAULT 'In Stock'
        CHECK (stock_status IN ('In Stock', 'Low Stock', 'Out of Stock')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tax_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rate_percent REAL NOT NULL CHECK (rate_percent >= 0 AND rate_percent <= 100),
    is_active INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT NOT NULL UNIQUE,
    customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
    customer_name TEXT NOT NULL DEFAULT 'Walk-in Customer',
    cashier_id INTEGER NOT NULL REFERENCES users(id),
    cashier_name TEXT NOT NULL,
    subtotal REAL NOT NULL,
    tax_rate REAL NOT NULL,
    tax_amount REAL NOT NULL,
    total REAL NOT NULL,
    payment_method TEXT NOT NULL,
    amount_tendered REAL NOT NULL,
    change_due REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    sku TEXT NOT NULL,
    product_name TEXT NOT NULL,
    category_name TEXT NOT NULL,
    warranty_months INTEGER NOT NULL DEFAULT 0,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL,
    line_total REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    username TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_sales_created ON sales(created_at);
CREATE INDEX IF NOT EXISTS idx_sale_items_sale ON sale_items(sale_id);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
"""


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(config.DB_PATH)), exist_ok=True)
    # isolation_level=None -> autocommit; transactions are managed explicitly below.
    conn = sqlite3.connect(config.DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction():
    """Write transaction (BEGIN IMMEDIATE): commits on success, rolls back on any error."""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        conn.close()


def query_all(sql, params=()):
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def query_one(sql, params=()):
    conn = get_connection()
    try:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def fetch_one(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def init_db(seed: bool = True) -> None:
    """Create tables, and load sample data the first time (when there are no users)."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        empty = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    finally:
        conn.close()
    if seed and empty:
        import seed_data  # ගොනුවේ නම seed_data.py විය යුතුය

        seed_data.seed()