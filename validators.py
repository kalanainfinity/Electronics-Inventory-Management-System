"""Input validation. Every function raises ValidationError with a user-readable message."""
import re
from decimal import Decimal, InvalidOperation

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^[0-9+\-()\s]+$")
_SKU_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]{2,39}$")
_INT_RE = re.compile(r"^[+-]?\d+$")


class ValidationError(ValueError):
    """Raised when user input is not acceptable."""


def clean_text(value, label, *, required=False, max_len=120) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValidationError(f"{label} is required.")
    if len(text) > max_len:
        raise ValidationError(f"{label} must be at most {max_len} characters.")
    return text


def parse_int(value, label, *, minimum=0, maximum=1_000_000) -> int:
    text = clean_text(value, label, required=True, max_len=12)
    if not _INT_RE.match(text):
        raise ValidationError(f"{label} must be a whole number.")
    number = int(text)
    if number < minimum or number > maximum:
        raise ValidationError(f"{label} must be between {minimum} and {maximum}.")
    return number


def _parse_decimal(value, label, max_places=2) -> Decimal:
    text = clean_text(value, label, required=True, max_len=20).replace(",", "")
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise ValidationError(f"{label} must be a number.") from None
    if not number.is_finite():
        raise ValidationError(f"{label} must be a number.")
    if number.as_tuple().exponent < -max_places:
        raise ValidationError(f"{label} may have at most {max_places} decimal places.")
    return number


def parse_money(value, label, *, maximum=10_000_000) -> float:
    number = _parse_decimal(value, label)
    if number < 0:
        raise ValidationError(f"{label} cannot be negative.")
    if number > maximum:
        raise ValidationError(f"{label} is too large.")
    return float(number)


def parse_rate(value, label="Tax rate") -> float:
    number = _parse_decimal(value, label)
    if number < 0 or number > 100:
        raise ValidationError(f"{label} must be between 0 and 100 percent.")
    return float(number)


def validate_email(value, label="Email") -> str:
    text = clean_text(value, label, max_len=120)
    if text and not _EMAIL_RE.match(text):
        raise ValidationError(f"{label} is not a valid email address.")
    return text


def validate_phone(value, label="Phone") -> str:
    text = clean_text(value, label, max_len=25)
    if not text:
        return ""
    digits = re.sub(r"\D", "", text)
    if not _PHONE_RE.match(text) or not 7 <= len(digits) <= 15:
        raise ValidationError(f"{label} must contain 7-15 digits (spaces, +, -, ( ) allowed).")
    return text


def validate_sku(value) -> str:
    text = clean_text(value, "SKU", required=True, max_len=40)
    if not _SKU_RE.match(text):
        raise ValidationError(
            "SKU must be 3-40 characters: letters, digits, '.', '_' or '-' (no spaces)."
        )
    return text.upper()


def validate_date(value, label="Date") -> str:
    """Accept blank or YYYY-MM-DD."""
    from datetime import datetime

    text = clean_text(value, label, max_len=10)
    if not text:
        return ""
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        raise ValidationError(f"{label} must be in YYYY-MM-DD format.") from None
    return text