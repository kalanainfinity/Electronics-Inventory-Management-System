"""Small shared helpers: timestamps, money maths, stock-status rules."""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

import config

TS_FORMAT = "%Y-%m-%d %H:%M:%S"
_CENT = Decimal("0.01")


def now_str() -> str:
    return datetime.now().strftime(TS_FORMAT)


def fmt_money(value) -> str:
    amount = Decimal(str(value or 0)).quantize(_CENT, rounding=ROUND_HALF_UP)
    return f"{config.CURRENCY}{amount:,.2f}"


def line_total(unit_price, quantity) -> float:
    total = (Decimal(str(unit_price)) * Decimal(int(quantity))).quantize(
        _CENT, rounding=ROUND_HALF_UP
    )
    return float(total)


def compute_totals(line_totals, rate_percent):
    """Return (subtotal, tax_amount, total) using exact decimal arithmetic."""
    subtotal = sum(
        (Decimal(str(x)) for x in line_totals), Decimal("0")
    ).quantize(_CENT, rounding=ROUND_HALF_UP)
    tax = (subtotal * Decimal(str(rate_percent)) / Decimal("100")).quantize(
        _CENT, rounding=ROUND_HALF_UP
    )
    total = (subtotal + tax).quantize(_CENT, rounding=ROUND_HALF_UP)
    return float(subtotal), float(tax), float(total)


def derive_stock_status(quantity: int, reorder_level: int) -> str:
    qty = int(quantity)
    reorder = int(reorder_level)
    if qty <= 0:
        return "Out of Stock"
    if qty <= reorder:
        return "Low Stock"
    return "In Stock"