"""Problem 4 - end-to-end check of hashing, signup and login.

Needs the backend running on :8000. Run from the Homework 4 folder:
    .venv\\Scripts\\python scripts\\check_auth.py

Reads SEED_TEST_EMAIL / SEED_TEST_PASSWORD from .env. Creates a throwaway account with a
random password, checks it, then deletes that one row so the users table stays clean.
"""

import json
import os
import secrets
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

import auth  # noqa: E402

API = "http://127.0.0.1:8000"
DB = ROOT / "data" / "campus_customs.db"
results: list[tuple[bool, str]] = []


def check(ok: bool, label: str):
    results.append((ok, label))
    print(("PASS " if ok else "FAIL ") + label)


def call(method: str, path: str, body: dict | None = None, token: str | None = None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main():
    seed_email, seed_pw = os.environ["SEED_TEST_EMAIL"], os.environ["SEED_TEST_PASSWORD"]

    # 1. Hash function unit checks
    h = auth.hash_password("correct horse battery")
    algo, salt, digest = h.split("$")
    check(algo == "pbkdf2_sha256" and len(digest) == 64, "new hash has format pbkdf2_sha256$salt$64-hex")
    check(auth.verify_password("correct horse battery", h), "re-hashing with stored salt verifies")
    check(not auth.verify_password("correct horse batterY", h), "one wrong character fails")
    check(auth.hash_password("same") != auth.hash_password("same"), "same password -> different salt/hash")

    # 2. Seeded test user (hash created outside this app -> proves settings match)
    s, r = call("POST", "/api/auth/login", {"email": seed_email, "password": seed_pw})
    check(s == 200 and r["user"]["email"] == seed_email, f"seed user logs in ({s})")
    check("password_hash" not in json.dumps(r), "login response never contains password_hash")
    s, me = call("GET", "/api/auth/me", token=r.get("token"))
    check(s == 200 and me["first_name"] == "Test", "token from login resolves /api/auth/me")
    s, _ = call("POST", "/api/auth/login", {"email": seed_email, "password": seed_pw + "x"})
    check(s == 401, f"seed user wrong password rejected ({s})")
    s, _ = call("POST", "/api/auth/login", {"email": "nobody@example.com", "password": seed_pw})
    check(s == 401, f"unknown email rejected with same error ({s})")
    s, _ = call("GET", "/api/auth/me", token=r["token"][:-2] + "xx")
    check(s == 401, f"tampered token rejected ({s})")

    # 3. Brand-new account through the API
    email = f"autocheck.{secrets.token_hex(4)}@example.com"
    pw = secrets.token_urlsafe(12)
    base = {"first_name": "Auto", "last_name": "Check", "email": email}
    s, _ = call("POST", "/api/auth/register", {**base, "password": pw, "confirm_password": pw + "!"})
    check(s == 400, f"mismatched confirmation rejected ({s})")
    s, _ = call("POST", "/api/auth/register", {**base, "password": "short", "confirm_password": "short"})
    check(s == 400, f"password under 8 chars rejected ({s})")
    s, r = call("POST", "/api/auth/register", {**base, "password": pw, "confirm_password": pw})
    check(s == 201 and r["user"]["first_name"] == "Auto", f"new account created ({s})")
    s, _ = call("POST", "/api/auth/register", {**base, "email": email.upper(), "password": pw, "confirm_password": pw})
    check(s == 409, f"duplicate email (any case) rejected ({s})")
    s, r = call("POST", "/api/auth/login", {"email": email, "password": pw})
    check(s == 200, f"new account logs in ({s})")

    con = sqlite3.connect(DB)
    stored = con.execute("SELECT password_hash FROM users WHERE email = ?", (email,)).fetchone()[0]
    check(pw not in stored and stored.startswith("pbkdf2_sha256$"), "DB row stores only the hash, not the password")
    con.execute("DELETE FROM users WHERE email = ?", (email,))
    con.commit()
    con.close()

    failed = [label for ok, label in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
