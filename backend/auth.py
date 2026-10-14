"""Password hashing, account storage and session tokens for Campus Customs.

Password format (matches the seed users in campus_customs.db):
    pbkdf2_sha256$<salt>$<hex digest>
    digest = PBKDF2-HMAC-SHA256(password, salt as UTF-8 text, 120_000 iterations), 32 bytes

Signup and login share ONE function (_pbkdf2) so the settings can never drift apart.
Login never "un-hashes" anything: it reads the salt from the stored string,
re-hashes what the user typed with that same salt, and compares in constant time.
"""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time

import db

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000
SALT_BYTES = 8                      # 8 random bytes -> 16 hex chars, like the seed users
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8

# Signs session tokens. Set SESSION_SECRET in .env so logins survive a server restart;
# otherwise a random per-process secret is used (everyone is logged out on restart).
_SESSION_SECRET = (os.getenv("SESSION_SECRET") or secrets.token_hex(32)).encode()


class AuthError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


# ------------------------------------------------------------------ passwords

def _pbkdf2(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS).hex()


def hash_password(password: str) -> str:
    """Signup: fresh random salt, then store algorithm$salt$hash."""
    salt = secrets.token_hex(SALT_BYTES)
    return f"{ALGORITHM}${salt}${_pbkdf2(password, salt)}"


def verify_password(password: str, stored: str) -> bool:
    """Login: reuse the stored salt, re-hash the typed password, constant-time compare."""
    try:
        algorithm, salt, expected = stored.split("$")
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    return hmac.compare_digest(_pbkdf2(password, salt), expected)


# Used when the email doesn't exist so a failed login takes the same time either way
# (stops attackers from discovering which emails have accounts by timing responses).
_DUMMY_HASH = hash_password(secrets.token_hex(16))


# ------------------------------------------------------------------ accounts

def public_user(row: sqlite3.Row) -> dict:
    """Everything the browser may see about a user. Never includes password_hash."""
    return {
        "id": row["id"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "name": row["name"],
        "email": row["email"],
    }


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def register(first_name: str, last_name: str, email: str, password: str, confirm_password: str) -> dict:
    first_name, last_name, email = first_name.strip(), last_name.strip(), _normalize_email(email)
    if not first_name or not last_name:
        raise AuthError("Please enter your first and last name.")
    if not EMAIL_RE.match(email):
        raise AuthError("Please enter a valid email address.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if password != confirm_password:
        raise AuthError("Passwords do not match.")

    with db.connect() as con:
        if con.execute("SELECT 1 FROM users WHERE lower(email) = ?", (email,)).fetchone():
            raise AuthError("An account with that email already exists. Try logging in.", 409)
        cur = con.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
            (f"{first_name} {last_name}", email, hash_password(password), first_name, last_name),
        )
        row = con.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return public_user(row)


def login(email: str, password: str) -> dict:
    with db.connect() as con:
        row = con.execute("SELECT * FROM users WHERE lower(email) = ?", (_normalize_email(email),)).fetchone()
    if row is None:
        verify_password(password, _DUMMY_HASH)
        raise AuthError("Incorrect email or password.", 401)
    if not verify_password(password, row["password_hash"]):
        raise AuthError("Incorrect email or password.", 401)
    return public_user(row)


def get_user(user_id: int) -> dict | None:
    with db.connect() as con:
        row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return public_user(row) if row else None


# ------------------------------------------------------------------ sessions

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def create_token(user_id: int) -> str:
    """Signed token "<payload>.<signature>"; the server can trust it without storing it."""
    payload = _b64(json.dumps({"uid": user_id, "exp": int(time.time()) + SESSION_TTL_SECONDS}).encode())
    sig = _b64(hmac.new(_SESSION_SECRET, payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def user_id_from_token(token: str) -> int | None:
    try:
        payload, sig = token.split(".")
        expected = _b64(hmac.new(_SESSION_SECRET, payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if data["exp"] < time.time():
            return None
        return int(data["uid"])
    except (ValueError, KeyError, json.JSONDecodeError):
        return None
