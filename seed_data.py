"""Realistic sample data so the app can be tested immediately after first launch.

Default logins (CHANGE THESE before any real use):
    admin    / admin123     (Admin)
    cashier  / cashier123   (Cashier)
    cashier2 / cashier123   (Cashier)
"""
import random
from datetime import datetime, timedelta


import config
from database import transaction
from security import hash_password
from utils import TS_FORMAT, compute_totals, derive_stock_status, line_total

USERS = [
    ("admin", "admin123", "Admin", "System Administrator"),
    ("cashier", "cashier123", "Cashier", "Front Desk Cashier"),
    ("cashier2", "cashier123", "Cashier", "Evening Cashier"),
]

CATEGORIES = [
    ("Smartphones", "Mobile phones and foldables"),
    ("Laptops & Computers", "Laptops, desktops and monitors"),
    ("Audio", "Headphones, earbuds and speakers"),
    ("TVs & Displays", "Televisions and streaming devices"),
    ("Cameras", "Cameras, lenses and action cams"),
    ("Gaming", "Consoles, controllers and gaming peripherals"),
    ("Accessories", "Chargers, cables, power banks and storage"),
    ("Smart Home", "Smart speakers, plugs, cameras and lighting"),
]

SUPPLIERS = [
    ("TechSource Distribution", "Alicia Mendes", "+1 555 010 1001", "sales@techsource.example", "12 Harbor Rd, Port City"),
    ("GlobalGadgets Wholesale", "Rahul Verma", "+1 555 010 1002", "orders@globalgadgets.example", "88 Market St, Eastfield"),
    ("Pacific Components Ltd", "Mei Tanaka", "+1 555 010 1003", "supply@pacificcomp.example", "5 Dockside Ave, Bayview"),
    ("NovaTrade Electronics", "Daniel Okoye", "+1 555 010 1004", "hello@novatrade.example", "301 Industrial Pkwy, Northgate"),
    ("BrightWave Imports", "Sofia Rossi", "+1 555 010 1005", "trade@brightwave.example", "47 Canal St, Riverton"),
]

CUSTOMERS = [
    ("Amelia Fernando", "+1 555 020 2001", "amelia.f@example.com", "21 Lake View, Eastfield"),
    ("Kasun Perera", "+1 555 020 2002", "kasun.p@example.com", "9 Station Rd, Bayview"),
    ("Priya Natarajan", "+1 555 020 2003", "priya.n@example.com", "150 Hill St, Northgate"),
    ("Tom Whitfield", "+1 555 020 2004", "tom.w@example.com", "3 Orchard Ln, Riverton"),
    ("Nadia Hussein", "+1 555 020 2005", "nadia.h@example.com", "77 Park Ave, Port City"),
    ("Lucas Almeida", "+1 555 020 2006", "lucas.a@example.com", "18 Cedar Ct, Eastfield"),
]

# sku, name, brand, model, category, supplier#, serial, warranty, cost, price, qty, reorder
PRODUCTS = [
    ("PH-SAM-S24", "Galaxy S24 128GB", "Samsung", "SM-S921B", "Smartphones", 0, "SN-S24-2025-0001", 24, 610.00, 799.00, 14, 5),
    ("PH-APL-I15", "iPhone 15 128GB", "Apple", "A3090", "Smartphones", 1, "SN-I15-2025-0001", 12, 640.00, 829.00, 9, 5),
    ("PH-GOO-P8", "Pixel 8 128GB", "Google", "GKV4X", "Smartphones", 1, "", 24, 480.00, 649.00, 4, 5),
    ("LT-DEL-XPS13", "XPS 13 Laptop i7/16GB/512GB", "Dell", "9340", "Laptops & Computers", 0, "SN-XPS-2025-0007", 24, 980.00, 1299.00, 6, 3),
    ("LT-LEN-TP14", "ThinkPad E14 i5/16GB/512GB", "Lenovo", "E14 G5", "Laptops & Computers", 3, "", 36, 640.00, 849.00, 8, 3),
    ("LT-HP-PAV15", "Pavilion 15 Ryzen 5/8GB/512GB", "HP", "15-eg3", "Laptops & Computers", 3, "", 12, 450.00, 619.00, 2, 3),
    ("MN-LG-27UP", "27\" 4K UHD Monitor", "LG", "27UP850", "Laptops & Computers", 2, "", 24, 260.00, 369.00, 11, 4),
    ("AU-SON-XM5", "WH-1000XM5 Wireless Headphones", "Sony", "WH-1000XM5", "Audio", 1, "", 12, 280.00, 379.00, 12, 5),
    ("AU-JBL-FLIP6", "Flip 6 Bluetooth Speaker", "JBL", "FLIP6", "Audio", 4, "", 12, 85.00, 129.00, 20, 8),
    ("AU-APL-APP2", "AirPods Pro (2nd gen)", "Apple", "MTJV3", "Audio", 1, "", 12, 190.00, 249.00, 0, 6),
    ("AU-BOS-QC45", "QuietComfort 45 Headphones", "Bose", "QC45", "Audio", 4, "", 12, 220.00, 329.00, 7, 4),
    ("TV-SAM-55Q", "55\" QLED 4K Smart TV", "Samsung", "QN55Q60D", "TVs & Displays", 0, "", 24, 450.00, 649.00, 5, 3),
    ("TV-LG-C3-65", "65\" OLED evo 4K TV", "LG", "OLED65C3", "TVs & Displays", 2, "", 24, 1150.00, 1599.00, 3, 2),
    ("TV-ROK-STK4K", "Streaming Stick 4K", "Roku", "3820R", "TVs & Displays", 4, "", 12, 28.00, 49.99, 30, 10),
    ("CM-CAN-R50", "EOS R50 Mirrorless Camera Kit", "Canon", "R50 + 18-45", "Cameras", 3, "SN-R50-2025-0003", 12, 560.00, 779.00, 5, 2),
    ("CM-GOP-H12", "HERO12 Black Action Camera", "GoPro", "CHDHX-121", "Cameras", 4, "", 12, 260.00, 349.00, 8, 3),
    ("GM-SON-PS5", "PlayStation 5 Console", "Sony", "CFI-2000", "Gaming", 1, "SN-PS5-2025-0012", 12, 410.00, 499.00, 6, 4),
    ("GM-NIN-SWOLED", "Switch OLED Model", "Nintendo", "HEG-001", "Gaming", 1, "", 12, 280.00, 349.00, 10, 4),
    ("GM-LOG-G502", "G502 HERO Gaming Mouse", "Logitech", "G502", "Gaming", 2, "", 24, 32.00, 54.99, 25, 8),
    ("AC-ANK-PB20", "PowerCore 20000mAh Power Bank", "Anker", "A1289", "Accessories", 4, "", 18, 24.00, 45.99, 3, 10),
    ("AC-ANK-USBC65", "65W USB-C GaN Charger", "Anker", "A2668", "Accessories", 4, "", 18, 20.00, 39.99, 40, 10),
    ("AC-SAN-SSD1T", "Portable SSD 1TB", "SanDisk", "SDSSDE61", "Accessories", 2, "", 36, 72.00, 109.00, 15, 5),
    ("SH-AMZ-ECHO", "Echo Dot (5th gen)", "Amazon", "B09B8V1LZ3", "Smart Home", 3, "", 12, 28.00, 49.99, 18, 8),
    ("SH-TPL-KP125", "Kasa Smart Plug Mini (2-pack)", "TP-Link", "KP125", "Smart Home", 2, "", 12, 14.00, 24.99, 1, 6),
]

TAX_RATES = [
    ("Standard Sales Tax", 8.00, 1),
    ("Reduced Rate", 5.00, 0),
    ("Luxury Rate", 12.00, 0),
]


def seed() -> None:
    rng = random.Random(2026)
    now = datetime.now()
    ts = now.strftime(TS_FORMAT)

    with transaction() as conn:
        for username, password, role, full_name in USERS:
            conn.execute(
                "INSERT INTO users (username, password_hash, role, full_name) VALUES (?,?,?,?)",
                (username, hash_password(password), role, full_name),
            )
        for name, desc in CATEGORIES:
            conn.execute("INSERT INTO categories (name, description) VALUES (?,?)", (name, desc))
        for row in SUPPLIERS:
            conn.execute(
                "INSERT INTO suppliers (name, contact_person, phone, email, address) VALUES (?,?,?,?,?)", row
            )
        for name, phone, email, address in CUSTOMERS:
            conn.execute(
                "INSERT INTO customers (name, phone, email, address, created_at) VALUES (?,?,?,?,?)",
                (name, phone, email, address, ts),
            )
        for name, rate, active in TAX_RATES:
            conn.execute(
                "INSERT INTO tax_rates (name, rate_percent, is_active, created_at, created_by) VALUES (?,?,?,?,?)",
                (name, rate, active, ts, "admin"),
            )

        cat_ids = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM categories")}
        sup_ids = [r["id"] for r in conn.execute("SELECT id FROM suppliers ORDER BY id")]
        for i, (sku, name, brand, model, cat, sup, serial, warranty, cost, price, qty, reorder) in enumerate(PRODUCTS):
            conn.execute(
                """INSERT INTO products (sku, barcode, name, brand, model, category_id, supplier_id,
                   serial_number, warranty_months, cost_price, selling_price, stock_qty, reorder_level,
                   stock_status, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (sku, f"89{i + 1:011d}", name, brand, model, cat_ids[cat], sup_ids[sup], serial,
                 warranty, cost, price, qty, reorder, derive_stock_status(qty, reorder), ts, ts),
            )

        # ---- sample sales over the last 30 days (stock figures above are already "after" these) ----
        products = [dict(r) for r in conn.execute(
            "SELECT p.*, c.name AS category_name FROM products p JOIN categories c ON c.id = p.category_id")]
        sellable = [p for p in products if p["selling_price"] > 0]
        cashiers = [dict(r) for r in conn.execute("SELECT id, full_name FROM users WHERE role = 'Cashier'")]
        customers = [dict(r) for r in conn.execute("SELECT id, name FROM customers")]
        rate = next(r for r in TAX_RATES if r[2])[1]

        stamps = []
        for n in range(34):
            if n < 4:  # a few sales "today" so the daily KPI is populated
                stamps.append(now - timedelta(minutes=rng.randint(10, 300)))
            else:
                day = now - timedelta(days=rng.randint(1, 29))
                stamps.append(day.replace(hour=rng.randint(9, 20), minute=rng.randint(0, 59), second=rng.randint(0, 59)))
        stamps.sort()

        for when in stamps:
            cashier = rng.choice(cashiers)
            customer = rng.choice(customers + [None, None])
            picks = rng.sample(sellable, rng.randint(1, 3))
            lines = []
            for p in picks:
                qty = rng.choice([1, 1, 1, 2, 3]) if p["selling_price"] < 200 else rng.choice([1, 1, 2])
                lines.append((p, qty, line_total(p["selling_price"], qty)))
            subtotal, tax, total = compute_totals([l[2] for l in lines], rate)
            method = rng.choice(["Cash", "Card", "Card", "Mobile Payment"])
            cur = conn.execute(
                """INSERT INTO sales (invoice_no, customer_id, customer_name, cashier_id, cashier_name,
                   subtotal, tax_rate, tax_amount, total, payment_method, amount_tendered, change_due, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f"TMP-{when.timestamp()}", customer["id"] if customer else None,
                 customer["name"] if customer else "Walk-in Customer", cashier["id"], cashier["full_name"],
                 subtotal, rate, tax, total, method, total, 0.0, when.strftime(TS_FORMAT)),
            )
            sale_id = cur.lastrowid
            conn.execute("UPDATE sales SET invoice_no = ? WHERE id = ?",
                         (f"INV-{when:%Y%m%d}-{sale_id:05d}", sale_id))
            for p, qty, lt in lines:
                conn.execute(
                    """INSERT INTO sale_items (sale_id, product_id, sku, product_name, category_name,
                       warranty_months, quantity, unit_price, line_total) VALUES (?,?,?,?,?,?,?,?,?)""",
                    (sale_id, p["id"], p["sku"], p["name"], p["category_name"], p["warranty_months"],
                     qty, p["selling_price"], lt),
                )

        conn.execute(
            "INSERT INTO audit_log (ts, username, role, action, details) VALUES (?,?,?,?,?)",
            (ts, "system", "System", "SEED_DATA", "Sample data loaded on first run"),
        )