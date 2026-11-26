"""Application-wide constants and the single source of truth for role permissions."""
import os
import sys

APP_NAME = "Electronics Inventory Management System"


def _get_app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = _get_app_dir()
DATA_DIR = os.path.join(BASE_DIR, "data")
# DB path is read at call time (config.DB_PATH) so tests can point at a temp file.
DB_PATH = os.environ.get("EIMS_DB", os.path.join(DATA_DIR, "inventory.db"))
EXPORT_DIR = os.path.join(BASE_DIR, "exports")

CURRENCY = "$"  # change to "Rs." etc. if needed; used for display/receipts only

ADMIN = "Admin"
CASHIER = "Cashier"
ROLES = (ADMIN, CASHIER)

STOCK_STATUSES = ("In Stock", "Low Stock", "Out of Stock")
PAYMENT_METHODS = ("Cash", "Card", "Mobile Payment")

PBKDF2_ITERATIONS = 200_000
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 60

_BOTH = frozenset({ADMIN, CASHIER})
_ADMIN = frozenset({ADMIN})

PERMISSIONS = {
    "overview": {
        "view": _BOTH,
        "view_financials": _ADMIN,
        "view_activity_log": _ADMIN,
    },
    "customers": {"view": _BOTH, "add": _BOTH, "edit": _ADMIN, "delete": _ADMIN},
    "suppliers": {"view": _BOTH, "add": _ADMIN, "edit": _ADMIN, "delete": _ADMIN},
    "categories": {"view": _BOTH, "add": _BOTH, "edit": _ADMIN, "delete": _ADMIN},
    "products": {
        "view": _BOTH,
        "view_cost": _ADMIN,
        "add": _ADMIN,
        "edit": _ADMIN,
        "delete": _ADMIN,
        "update_status": _BOTH,
    },
    "tax_rate": {"view_active": _BOTH, "view_all": _ADMIN, "manage": _ADMIN},
    "sales": {
        "create": _BOTH,
        "view_own": _BOTH,
        "view_all": _ADMIN,
        "analytics": _ADMIN,
        "qr": _ADMIN,
        "export": _ADMIN,
        "report": _ADMIN,
        "reset": _ADMIN,
    },
}

NAV_ITEMS = (
    "Overview", "Customers", "Suppliers", "Categories",
    "Products", "Tax Rate", "Sales", "Exit",
)
NAV_SECTIONS = {
    "Overview": "overview", "Customers": "customers", "Suppliers": "suppliers",
    "Categories": "categories", "Products": "products", "Tax Rate": "tax_rate",
    "Sales": "sales",
}