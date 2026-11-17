"""Password hashing with the standard library's scrypt (no extra dependency).

We store only "scrypt$n$r$p$salt$hash", never the password. Each customer gets a random salt,
so two customers with the same password still have different hashes.
"""

import base64
import hashlib
import hmac
import os

_N, _R, _P = 2**14, 8, 1  # scrypt cost settings (memory/CPU work per guess)


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, digest_b64 = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    salt, expected = base64.b64decode(salt_b64), base64.b64decode(digest_b64)
    actual = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p))
    return hmac.compare_digest(actual, expected)  # constant-time comparison
