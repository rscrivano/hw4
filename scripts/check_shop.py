"""Problems 9 + 12 - end-to-end checks for cart pricing, guest/logged-in checkout, click history,
recommendations, the restock purchase list, and the Problem 12 safety rules (payment method required,
guest phone/email/name, unique trackable order numbers, hourly inventory audit, audit trail).
Needs the backend running on :8000.

Run from the Homework 4 folder:
    .venv\\Scripts\\python scripts\\check_shop.py

The test orders really decrement inventory (that's what is being tested), so at the end the script
puts the stock back and removes only the rows it created (its orders, order lines, view events and
purchase-list lines). Results are saved to output/p9_shop_checks.txt.
"""

import json
import os
import re
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

API = "http://127.0.0.1:8000"
DB = ROOT / "data" / "campus_customs.db"
lines_out: list[str] = []
results: list[bool] = []


def log(msg: str):
    print(msg)
    lines_out.append(msg)


def check(ok: bool, label: str):
    results.append(ok)
    log(("PASS " if ok else "FAIL ") + label)


def call(method, path, body=None, token=None, headers=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else None


def qty(con, pid, size):
    return con.execute("SELECT quantity FROM inventory WHERE product_id=? AND size=?", (pid, size)).fetchone()[0]


def main():
    con = sqlite3.connect(DB)
    # A size with 8 in stock and no open restock line: buying 3 leaves 5 = "low stock".
    pid, size = con.execute(
        "SELECT i.product_id, i.size FROM inventory i WHERE i.quantity = 8 AND NOT EXISTS ("
        "SELECT 1 FROM purchase_list p WHERE p.product_id=i.product_id AND p.size=i.size AND p.status='open') LIMIT 1"
    ).fetchone()
    other_pid, other_size = con.execute(
        "SELECT product_id, size FROM inventory WHERE quantity >= 20 AND product_id != ? LIMIT 1", (pid,)).fetchone()
    start = {(pid, size): qty(con, pid, size), (other_pid, other_size): qty(con, other_pid, other_size)}
    max_order = con.execute("SELECT COALESCE(MAX(id),0) FROM orders").fetchone()[0]
    max_pl = con.execute("SELECT COALESCE(MAX(id),0) FROM purchase_list").fetchone()[0]
    visitor = "check-" + secrets.token_hex(4)
    log(f"Test item: {pid} size {size} (stock {start[(pid, size)]}); second item: {other_pid} {other_size}")

    try:
        # ---- 1. cart quote: prices come from the DB, stock problems are reported
        s, q = call("POST", "/api/cart/quote", {"items": [{"product_id": pid, "size": size, "quantity": 9}]})
        check(s == 200 and not q["ok"] and "Only 8 left" in q["problems"][0], "quote flags quantity above stock")
        s, q = call("POST", "/api/cart/quote", {"items": [{"product_id": pid, "size": size, "quantity": 3}]})
        price = con.execute("SELECT price FROM catalogue WHERE product_id=?", (pid,)).fetchone()[0]
        check(q["ok"] and q["subtotal"] == round(price * 3, 2), f"quote prices from the catalogue (${q['subtotal']:.2f})")

        # ---- 2. Problem 12 safety rules: refused orders change NOTHING
        guest = {"items": [{"product_id": pid, "size": size, "quantity": 3}], "customer_name": "Guest Tester",
                 "email": "guest.tester@example.com", "phone": "(203) 555-0142", "fulfillment": "pickup",
                 "payment_method": "cash_at_pickup"}
        orders_before = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        s, r = call("POST", "/api/orders", {**guest, "payment_method": None})
        check(s == 402 and "payment method" in r["detail"].lower(), f"no payment method -> order refused ({s})")
        s, r = call("POST", "/api/orders", {**guest, "payment_method": "card_on_delivery"})
        check(s == 402, f"payment method that doesn't fit pickup -> refused ({s})")
        s, r = call("POST", "/api/orders", {**guest, "phone": ""})
        check(s == 400 and "phone" in r["detail"].lower(), f"guest without phone number -> refused ({s})")
        s, r = call("POST", "/api/orders", {**guest, "email": "nope"})
        check(s == 400, "guest checkout rejects an invalid email")
        check(qty(con, pid, size) == start[(pid, size)] and
              con.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == orders_before,
              "refused orders saved nothing and took no stock")

        # ---- 3. guest checkout with name + email + phone + payment method
        s, r = call("POST", "/api/orders", guest)
        number = r and r.get("order_number")
        check(s == 201 and r["guest"] and bool(re.fullmatch(r"CC-\d{6}-[A-Z2-9]{6}", number or "")),
              f"guest order placed with transaction number {number}")
        row = con.execute("SELECT user_id, email, phone, payment_method FROM orders WHERE order_number=?", (number,)).fetchone()
        check(row[0] is None and row[1] == "guest.tester@example.com" and row[2] == "2035550142"
              and row[3] == "cash_at_pickup", f"guest order saved with name, email, phone and payment method: {tuple(row)}")
        # tracking: number + email or phone; wrong contact is refused
        s, t = call("GET", f"/api/orders/track?order_number={number}&contact=GUEST.TESTER@example.com")
        check(s == 200 and t["order_number"] == number and t["payment_status"] == "due at pickup",
              f"order trackable by number + email ({t and t.get('status')}, {t and t.get('payment_method')})")
        s, t = call("GET", f"/api/orders/track?order_number={number.lower()}&contact=203.555.0142")
        check(s == 200, "order trackable by number + phone (any format)")
        s, _ = call("GET", f"/api/orders/track?order_number={number}&contact=someone.else@example.com")
        check(s == 404, "tracking refuses the wrong email (no browsing other orders)")
        check(qty(con, pid, size) == start[(pid, size)] - 3, f"inventory decremented 8 -> {qty(con, pid, size)}")

        # ---- 3. low stock -> purchase list
        pl = con.execute("SELECT stock_when_flagged, reorder_qty, reason FROM purchase_list "
                         "WHERE product_id=? AND size=? AND status='open'", (pid, size)).fetchone()
        check(pl is not None and pl[0] == 5, f"low stock flagged on purchase list: {pl}")
        check(pl is not None and pl[1] == 25 - 5 + 3, "reorder qty = par 25 - stock 5 + 3 sold in last 30 days = 23")

        # ---- 4. can't oversell
        s, r = call("POST", "/api/orders", {**guest, "items": [{"product_id": pid, "size": size, "quantity": 6}]})
        check(s == 409 and "only 5 left" in r["detail"], "checkout refuses to oversell (409)")

        # ---- 5. logged-in checkout links the order to the account
        s, login = call("POST", "/api/auth/login", {"email": os.environ["SEED_TEST_EMAIL"],
                                                    "password": os.environ["SEED_TEST_PASSWORD"]})
        token = login["token"]
        s, r = call("POST", "/api/orders", {"items": [{"product_id": other_pid, "size": other_size, "quantity": 1}],
                                             "customer_name": "Test User", "email": "test@campuscustoms.yale.edu",
                                             "fulfillment": "ship", "shipping_address": "1 Prospect St, New Haven",
                                             "payment_method": "card_on_delivery"},
                    token=token)
        uid = con.execute("SELECT user_id FROM orders WHERE order_number=?", (r["order_number"],)).fetchone()[0]
        check(s == 201 and not r["guest"] and uid == login["user"]["id"], "logged-in order linked to the account")

        # ---- 6. click history -> recommendations
        hoodies = [x[0] for x in con.execute("SELECT product_id FROM catalogue WHERE garment_type LIKE '%hood%' "
                                             "AND garment_type NOT LIKE '%zip%' LIMIT 3")]
        for h in hoodies:
            call("POST", "/api/events/view", {"product_id": h, "visitor_id": visitor})
        n = con.execute("SELECT COUNT(*) FROM product_views WHERE visitor_id=?", (visitor,)).fetchone()[0]
        check(n == 3, "3 product views recorded for the visitor")
        s, rec = call("GET", f"/api/recommendations?visitor_id={visitor}&limit=4")
        cats = [c["category"] for c in rec["products"]]
        check(rec["reason"].startswith("Because you") and "hoodie" in rec["reason"].lower() and cats.count("Hoodies") >= 3,
              f"recommendations follow the clicks: {rec['reason']} -> {cats}")
        s, rec2 = call("GET", "/api/recommendations?visitor_id=brand-new-visitor&limit=4")
        check(rec2["reason"] == "Popular right now", "no history -> popular items")

        # ---- 7. hourly inventory audit + append-only audit trail
        key = {"X-Staff-Key": os.environ["STAFF_KEY"]}
        s, ic = call("GET", "/api/staff/inventory-checks", headers=key)
        latest = ic["checks"][0] if s == 200 and ic["checks"] else {}
        check(s == 200 and ic["interval_seconds"] == 3600 and latest.get("sizes_checked") == 612,
              f"inventory audit runs at startup and every {ic and ic.get('interval_seconds')}s "
              f"(latest: {latest.get('trigger')}, {latest.get('sizes_checked')} sizes, {latest.get('flagged_for_restock')} flagged)")
        trail = json.loads((ROOT / "output" / "audit_trail.json").read_text(encoding="utf-8"))
        check(any(e.get("event") == "inventory_check" for e in trail) and any(e.get("event") == "tool_call" for e in trail),
              f"audit trail holds agent tool calls and inventory checks ({len(trail)} entries, never wiped)")

        # ---- 8. staff purchase list is protected
        s, _ = call("GET", "/api/staff/purchase-list")
        check(s == 403, "purchase list needs the staff key")
        s, plist = call("GET", "/api/staff/purchase-list", headers={"X-Staff-Key": os.environ["STAFF_KEY"]})
        check(s == 200 and any(i["product_id"] == pid and i["size"] == size for i in plist["items"]),
              f"staff sees the purchase list ({plist['lines']} lines, {plist['total_units']} units to reorder)")
    finally:
        # ---- clean up only what this script created
        for (p, sz), q0 in start.items():
            con.execute("UPDATE inventory SET quantity=? WHERE product_id=? AND size=?", (q0, p, sz))
        con.execute("DELETE FROM order_items WHERE order_id > ?", (max_order,))
        con.execute("DELETE FROM orders WHERE id > ?", (max_order,))
        con.execute("DELETE FROM product_views WHERE visitor_id = ?", (visitor,))
        con.execute("DELETE FROM purchase_list WHERE id > ?", (max_pl,))
        con.commit()
        con.close()
        log("Cleanup: stock restored, test orders/views/purchase-list lines removed.")

    log(f"\n{sum(results)}/{len(results)} checks passed")
    (ROOT / "output" / "p9_shop_checks.txt").write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
