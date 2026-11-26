"""Password hashing (PBKDF2-HMAC-SHA256, per-user random salt, constant-time compare)."""
import hashlib
import hmac
import os

import config

_ALGO = "pbkdf2_sha256"


def hash_password(password: str, iterations: int = None) -> str:
    iterations = iterations or config.PBKDF2_ITERATIONS
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{_ALGO}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, hash_hex = stored.split("$")
        if algo != _ALGO:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False