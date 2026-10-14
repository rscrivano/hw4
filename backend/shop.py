"""Shop operations (Problem 9): cart pricing, checkout/orders, click history,
recommendations, and the low-stock restock purchase list.

New tables are created on startup with CREATE TABLE IF NOT EXISTS (see ensure_tables), so the
provided campus_customs.db keeps its original tables untouched and simply gains these:

  orders          one row per placed order (user_id is NULL for guest checkout)
  order_items     the lines of each order, with the price charged at the time
  product_views   every product a shopper opened (user_id and/or anonymous visitor_id)
  purchase_list   the business's restock list: what to reorder, how many, and why
  inventory_checks one row per scheduled stock audit (Problem 12)

Problem 12 safety rules enforced here (server-side, so the website can't skip them):
  * no payment method chosen -> the order is refused before anything is saved or deducted
  * guests must give name, email AND phone number
  * every order gets a unique, trackable transaction number (CC-YYMMDD-XXXXXX)
  * inventory_check() re-audits stock (run hourly by main.py) so low/sold-out sizes are caught early
"""

from __future__ import annotations

import re
import secrets
import sqlite3
from collections import Counter
from datetime import datetime

import audit
import db
from models import LOW_STOCK_MAX

PAR_LEVEL = 25          # target units per size after a restock (the highest stock level in the catalogue)
DEMAND_WINDOW_DAYS = 30  # recent sales added on top of the par level, so popular sizes reorder more
MAX_LINE_QTY = 10
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Payment is collected in person (the site never takes card numbers), but the shopper MUST choose
# how they will pay before an order can be placed. Allowed methods depend on pickup vs shipping.
PAYMENT_METHODS = {
    "card_at_pickup": ("Card at pickup", "pickup"),
    "cash_at_pickup": ("Cash at pickup", "pickup"),
    "card_on_delivery": ("Card on delivery", "ship"),
    "cash_on_delivery": ("Cash on delivery", "ship"),
}
ORDER_NUMBER_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I, easy to read out


def _phone_digits(phone: str | None) -> str:
    return re.sub(r"\D", "", phone or "")

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT NOT NULL UNIQUE,
    user_id INTEGER REFERENCES users(id),
    customer_name TEXT NOT NULL,
    email TEXT NOT NULL,
    fulfillment TEXT NOT NULL CHECK (fulfillment IN ('pickup', 'ship')),
    shipping_address TEXT,
    subtotal REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'placed',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id TEXT NOT NULL REFERENCES catalogue(product_id),
    size TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL,
    line_total REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS product_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    visitor_id TEXT,
    product_id TEXT NOT NULL REFERENCES catalogue(product_id),
    source TEXT NOT NULL DEFAULT 'product_page',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_views_user ON product_views(user_id, id);
CREATE INDEX IF NOT EXISTS idx_views_visitor ON product_views(visitor_id, id);
CREATE TABLE IF NOT EXISTS purchase_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL REFERENCES catalogue(product_id),
    size TEXT NOT NULL,
    stock_when_flagged INTEGER NOT NULL,
    reorder_qty INTEGER NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'ordered', 'received')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
-- at most one OPEN restock line per product + size
CREATE UNIQUE INDEX IF NOT EXISTS idx_purchase_open ON purchase_list(product_id, size) WHERE status = 'open';
CREATE TABLE IF NOT EXISTS inventory_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checked_at TEXT NOT NULL DEFAULT (datetime('now')),
    trigger TEXT NOT NULL,
    sizes_checked INTEGER NOT NULL,
    sold_out INTEGER NOT NULL,
    low_stock INTEGER NOT NULL,
    flagged_for_restock INTEGER NOT NULL,
    restock_lines_closed INTEGER NOT NULL,
    problems_fixed TEXT
);
"""

# Columns added to orders in Problem 12 (added with ALTER TABLE if an older orders table exists).
ORDER_COLUMNS = {"phone": "TEXT", "payment_method": "TEXT", "payment_status": "TEXT"}


class ShopError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def ensure_tables() -> None:
    with db.connect() as con:
        con.executescript(SCHEMA)
        have = {r["name"] for r in con.execute("PRAGMA table_info(orders)")}
        for col, kind in ORDER_COLUMNS.items():
            if col not in have:
                con.execute(f"ALTER TABLE orders ADD COLUMN {col} {kind}")


# ------------------------------------------------------------------ cart pricing

def _stock(con: sqlite3.Connection, product_id: str, size: str) -> int | None:
    row = con.execute("SELECT quantity FROM inventory WHERE product_id = ? AND size = ?", (product_id, size)).fetchone()
    return row["quantity"] if row else None


def quote(items: list[dict]) -> dict:
    """Price a cart from the database. The browser's prices are never trusted.

    items: [{product_id, size, quantity}] -> lines with the live price, stock and any problem."""
    lines, problems, subtotal = [], [], 0.0
    with db.connect() as con:
        for it in items:
            p = db.get_product(it["product_id"])
            if p is None:
                problems.append(f"An item in your cart ({it['product_id']}) is no longer sold.")
                continue
            available = _stock(con, p["product_id"], it["size"])
            qty = int(it["quantity"])
            issue = None
            if available is None:
                issue = f"Size {it['size']} doesn't exist for this item."
            elif available == 0:
                issue = f"Size {it['size']} is now sold out."
            elif qty > available:
                issue = f"Only {available} left in size {it['size']}."
            if issue:
                problems.append(f"{p['name']}: {issue}")
            line_total = round(p["price"] * qty, 2)
            subtotal += line_total if not issue else 0
            lines.append({
                "product_id": p["product_id"], "name": p["name"], "size": it["size"], "quantity": qty,
                "unit_price": p["price"], "line_total": line_total, "image_url": p["image_url"],
                "available": available or 0, "issue": issue,
            })
    return {"lines": lines, "subtotal": round(subtotal, 2), "item_count": sum(l["quantity"] for l in lines),
            "ok": not problems and bool(lines), "problems": problems}


# ------------------------------------------------------------------ checkout

def place_order(items: list[dict], customer_name: str, email: str, fulfillment: str,
                shipping_address: str | None, user: dict | None, phone: str | None = None,
                payment_method: str | None = None) -> dict:
    """Validate and place an order in ONE transaction: re-check stock, decrement inventory, save the
    order and its lines, then flag any size that is now low on the restock purchase list.
    Every rule is checked BEFORE the transaction starts, so a refused order changes nothing."""
    customer_name, email = customer_name.strip(), email.strip().lower()
    digits = _phone_digits(phone)
    if not items:
        raise ShopError("Your cart is empty.")
    if not customer_name:
        raise ShopError("Please enter your name.")
    if not EMAIL_RE.match(email):
        raise ShopError("Please enter a valid email so we can send your order confirmation.")
    # Safety rule: guests must leave a phone number (members may add one).
    if user is None and not digits:
        raise ShopError("Please enter a phone number so we can reach you about your order.")
    if digits and not 10 <= len(digits) <= 15:
        raise ShopError("Please enter a valid phone number (10-15 digits).")
    if fulfillment not in ("pickup", "ship"):
        raise ShopError("Choose in-store pickup or shipping.")
    if fulfillment == "ship" and not (shipping_address or "").strip():
        raise ShopError("Please enter a shipping address.")
    # Safety rule: no payment method applied -> the transaction cannot complete.
    if not payment_method:
        raise ShopError("Choose a payment method to complete your order.", 402)
    if payment_method not in PAYMENT_METHODS or PAYMENT_METHODS[payment_method][1] != fulfillment:
        raise ShopError("That payment method isn't available for this delivery option.", 402)

    merged: Counter = Counter()  # the same product+size added twice counts once
    for it in items:
        if not 1 <= int(it["quantity"]) <= MAX_LINE_QTY:
            raise ShopError(f"Quantities must be between 1 and {MAX_LINE_QTY}.")
        merged[(it["product_id"], it["size"])] += int(it["quantity"])

    con = db.connect()
    try:
        con.execute("BEGIN IMMEDIATE")  # lock so two shoppers can't buy the last unit at once
        lines, subtotal = [], 0.0
        for (pid, size), qty in merged.items():
            p = con.execute("SELECT name, price FROM catalogue WHERE product_id = ?", (pid,)).fetchone()
            available = _stock(con, pid, size)
            if p is None or available is None:
                raise ShopError("An item in your cart is no longer available.", 409)
            if qty > available:
                left = "sold out" if available == 0 else f"only {available} left"
                raise ShopError(f"{p['name']} in size {size} is {left}. Please update your cart.", 409)
            lines.append((pid, size, qty, p["price"], round(p["price"] * qty, 2), p["name"]))
            subtotal += p["price"] * qty
        order_number = new_order_number(con)
        payment_status = "due at pickup" if fulfillment == "pickup" else "due on delivery"
        cur = con.execute(
            "INSERT INTO orders (order_number, user_id, customer_name, email, phone, fulfillment, shipping_address, "
            "subtotal, payment_method, payment_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (order_number, user["id"] if user else None, customer_name, email, digits or None, fulfillment,
             shipping_address.strip() if fulfillment == "ship" and shipping_address else None, round(subtotal, 2),
             payment_method, payment_status),
        )
        order_id = cur.lastrowid
        for pid, size, qty, price, total, _name in lines:
            con.execute("INSERT INTO order_items (order_id, product_id, size, quantity, unit_price, line_total) "
                        "VALUES (?, ?, ?, ?, ?, ?)", (order_id, pid, size, qty, price, total))
            con.execute("UPDATE inventory SET quantity = quantity - ? WHERE product_id = ? AND size = ?",
                        (qty, pid, size))
        flagged = [check_restock(con, pid, size) for pid, size, *_ in lines]
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    return {"order_number": order_number, "subtotal": round(subtotal, 2), "guest": user is None,
            "payment_method": PAYMENT_METHODS[payment_method][0], "payment_status": payment_status,
            "items": [{"product_id": pid, "name": n, "size": s, "quantity": q, "unit_price": pr, "line_total": t}
                      for pid, s, q, pr, t, n in lines],
            "restock_flagged": [f for f in flagged if f]}


def new_order_number(con: sqlite3.Connection) -> str:
    """Unique, readable, trackable transaction number, e.g. CC-261014-K7Q2MX (date + 6 random chars)."""
    while True:
        code = "".join(secrets.choice(ORDER_NUMBER_CHARS) for _ in range(6))
        number = f"CC-{datetime.now():%y%m%d}-{code}"
        if not con.execute("SELECT 1 FROM orders WHERE order_number = ?", (number,)).fetchone():
            return number  # the UNIQUE constraint on orders.order_number is the final guarantee


def track_order(order_number: str, contact: str) -> dict:
    """Look up an order by its transaction number + the email OR phone used at checkout
    (both are required, so nobody can browse other people's orders by guessing numbers)."""
    number = order_number.strip().upper()
    contact = contact.strip().lower()
    with db.connect() as con:
        o = con.execute("SELECT * FROM orders WHERE order_number = ?", (number,)).fetchone()
        if o is None or not (contact == (o["email"] or "").lower()
                             or (_phone_digits(contact) and _phone_digits(contact) == (o["phone"] or ""))):
            raise ShopError("We couldn't find an order with that number and email/phone.", 404)
        lines = con.execute(
            "SELECT oi.product_id, c.name, oi.size, oi.quantity, oi.unit_price, oi.line_total "
            "FROM order_items oi JOIN catalogue c USING (product_id) WHERE oi.order_id = ?", (o["id"],),
        ).fetchall()
    method = PAYMENT_METHODS.get(o["payment_method"] or "", (o["payment_method"] or "not recorded",))[0]
    ready = "Ready for pickup at 57 Broadway" if o["fulfillment"] == "pickup" else "Preparing for shipment"
    return {
        "order_number": o["order_number"], "placed_at": o["created_at"], "status": o["status"],
        "customer_name": o["customer_name"], "fulfillment": o["fulfillment"], "payment_method": method,
        "payment_status": o["payment_status"] or ("due at pickup" if o["fulfillment"] == "pickup" else "due on delivery"),
        "subtotal": o["subtotal"], "items": [dict(r) for r in lines],
        "timeline": [{"step": "Order placed", "done": True, "at": o["created_at"]},
                     {"step": "Items reserved (stock deducted)", "done": True, "at": o["created_at"]},
                     {"step": ready, "done": False, "at": None}],
    }


# ------------------------------------------------------------------ hourly inventory audit

def inventory_check(trigger: str = "scheduled") -> dict:
    """Re-audit every size's stock (run on startup and then hourly by main.py):
      1. repair impossible values (negative stock -> 0) so checkout never trusts a bad number
      2. flag every size at <= LOW_STOCK_MAX for restock (adds/updates purchase_list lines)
      3. close restock lines whose size has since been restocked above the low-stock line
    The result is saved in inventory_checks and appended to the audit trail."""
    problems = []
    with db.connect() as con:
        for r in con.execute("SELECT product_id, size, quantity FROM inventory WHERE quantity < 0").fetchall():
            con.execute("UPDATE inventory SET quantity = 0 WHERE product_id = ? AND size = ?", (r["product_id"], r["size"]))
            problems.append(f"{r['product_id']} {r['size']}: negative stock {r['quantity']} reset to 0")
        sizes = con.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        sold_out = con.execute("SELECT COUNT(*) FROM inventory WHERE quantity = 0").fetchone()[0]
        low = con.execute("SELECT COUNT(*) FROM inventory WHERE quantity BETWEEN 1 AND ?", (LOW_STOCK_MAX,)).fetchone()[0]
        flagged = 0
        for r in con.execute("SELECT product_id, size FROM inventory WHERE quantity <= ?", (LOW_STOCK_MAX,)).fetchall():
            flagged += check_restock(con, r["product_id"], r["size"]) is not None
        closed = con.execute(
            "UPDATE purchase_list SET status = 'received', updated_at = datetime('now') WHERE status = 'open' AND "
            "(SELECT quantity FROM inventory i WHERE i.product_id = purchase_list.product_id AND i.size = purchase_list.size) > ?",
            (LOW_STOCK_MAX,),
        ).rowcount
        con.execute(
            "INSERT INTO inventory_checks (trigger, sizes_checked, sold_out, low_stock, flagged_for_restock, "
            "restock_lines_closed, problems_fixed) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trigger, sizes, sold_out, low, flagged, closed, "; ".join(problems) or None),
        )
    summary = {"trigger": trigger, "sizes_checked": sizes, "sold_out": sold_out, "low_stock": low,
               "flagged_for_restock": flagged, "restock_lines_closed": closed, "problems_fixed": problems}
    audit.append([{"time": audit.now(), "event": "inventory_check", **summary,
                   "stop_reason": "completed"}])
    return summary


def inventory_checks(limit: int = 20) -> list[dict]:
    with db.connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM inventory_checks ORDER BY id DESC LIMIT ?", (limit,))]


# ------------------------------------------------------------------ restock purchase list

def reorder_quantity(con: sqlite3.Connection, product_id: str, size: str, current: int) -> int:
    """Bring the size back up to the par level, plus whatever sold in the last 30 days (demand buffer)."""
    sold = con.execute(
        "SELECT COALESCE(SUM(oi.quantity), 0) FROM order_items oi JOIN orders o ON o.id = oi.order_id "
        "WHERE oi.product_id = ? AND oi.size = ? AND o.created_at >= datetime('now', ?)",
        (product_id, size, f"-{DEMAND_WINDOW_DAYS} days"),
    ).fetchone()[0]
    return max(PAR_LEVEL - current, 0) + sold


def check_restock(con: sqlite3.Connection, product_id: str, size: str) -> dict | None:
    """If this size is at or below the low-stock line, add/update its OPEN purchase-list row."""
    qty = _stock(con, product_id, size)
    if qty is None or qty > LOW_STOCK_MAX:
        return None
    reorder = reorder_quantity(con, product_id, size, qty)
    reason = "sold out" if qty == 0 else f"low stock ({qty} left)"
    con.execute(
        "INSERT INTO purchase_list (product_id, size, stock_when_flagged, reorder_qty, reason) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(product_id, size) WHERE status = 'open' DO UPDATE SET "
        "stock_when_flagged = excluded.stock_when_flagged, reorder_qty = excluded.reorder_qty, "
        "reason = excluded.reason, updated_at = datetime('now')",
        (product_id, size, qty, reorder, reason),
    )
    return {"product_id": product_id, "size": size, "stock": qty, "reorder_qty": reorder, "reason": reason}


def scan_inventory() -> int:
    """Startup sweep: flag every size that is already low (catches stock changed outside the app)."""
    with db.connect() as con:
        rows = con.execute("SELECT product_id, size FROM inventory WHERE quantity <= ?", (LOW_STOCK_MAX,)).fetchall()
        for r in rows:
            check_restock(con, r["product_id"], r["size"])
    return len(rows)


def purchase_list(status: str = "open") -> dict:
    with db.connect() as con:
        rows = con.execute(
            "SELECT pl.*, c.name, c.price FROM purchase_list pl JOIN catalogue c USING (product_id) "
            "WHERE pl.status = ? ORDER BY pl.stock_when_flagged, c.name, pl.size", (status,),
        ).fetchall()
    items = [dict(r) for r in rows]
    return {"status": status, "lines": len(items), "total_units": sum(i["reorder_qty"] for i in items),
            "items": items}


# ------------------------------------------------------------------ click history + recommendations

def record_view(product_id: str, user: dict | None, visitor_id: str | None, source: str) -> bool:
    if db.get_product(product_id) is None:
        return False
    with db.connect() as con:
        con.execute("INSERT INTO product_views (user_id, visitor_id, product_id, source) VALUES (?, ?, ?, ?)",
                    (user["id"] if user else None, visitor_id, product_id, source))
    return True


def recent_views(user_id: int | None, visitor_id: str | None, limit: int = 30) -> list[str]:
    """Most recent first, de-duplicated. Logged-in shoppers' history follows them across devices;
    a visitor id covers guests (and the views they made before logging in on this browser)."""
    if not user_id and not visitor_id:
        return []
    with db.connect() as con:
        rows = con.execute(
            "SELECT product_id FROM product_views WHERE (user_id = ? AND ? IS NOT NULL) OR (visitor_id = ? AND ? IS NOT NULL) "
            "ORDER BY id DESC LIMIT ?", (user_id, user_id, visitor_id, visitor_id, limit * 3),
        ).fetchall()
    return list(dict.fromkeys(r["product_id"] for r in rows))[:limit]


def recommend(user_id: int | None, visitor_id: str | None, exclude: list[str] | None = None,
              limit: int = 4) -> dict:
    """Score in-stock products by how well they match the shopper's recent clicks:
    same category (+3 each recent view, newer counts more), same garment color (+2), shared tags (+0.5).
    Products already viewed recently rank lower; no history -> most-viewed products overall."""
    viewed = recent_views(user_id, visitor_id)
    exclude = set(exclude or [])
    products = [p for p in db.list_products() if p["total_stock"] > 0 and p["product_id"] not in exclude]
    by_id = {p["product_id"]: p for p in db.list_products()}

    if not viewed:
        with db.connect() as con:
            popular = [r[0] for r in con.execute(
                "SELECT product_id FROM product_views GROUP BY product_id ORDER BY COUNT(*) DESC LIMIT 20")]
        ranked = [by_id[i] for i in popular if i in by_id and i not in exclude and by_id[i]["total_stock"] > 0]
        ranked += [p for p in products if p not in ranked]
        return {"reason": "Popular right now", "based_on": [], "product_ids": [p["product_id"] for p in ranked[:limit]]}

    cat_w, color_w, tag_w = Counter(), Counter(), Counter()
    for rank, pid in enumerate(viewed):
        p = by_id.get(pid)
        if not p:
            continue
        weight = 1 / (1 + rank * 0.25)  # newer clicks count more
        cat_w[p["category"]] += weight
        if p["colors"]:
            color_w[p["colors"][0]] += weight
        for t in p["search_tags"]:
            tag_w[t.lower()] += weight

    def score(p: dict) -> float:
        s = 3 * cat_w[p["category"]] + 2 * color_w[p["colors"][0] if p["colors"] else ""]
        s += 0.5 * sum(tag_w[t.lower()] for t in p["search_tags"])
        if p["product_id"] in viewed[:10]:
            s *= 0.3  # they've seen it; show something new first
        return s

    ranked = sorted(products, key=lambda p: (-score(p), -p["total_stock"]))
    # Explain the picks with the shopper's strongest interest, so the label matches the cards.
    top_cat = cat_w.most_common(1)[0][0] if cat_w else None
    anchor = next((by_id[v] for v in viewed if v in by_id and by_id[v]["category"] == top_cat), None)
    if anchor and len(viewed) == 1:
        reason = f"Because you viewed {anchor['name']}"
    elif top_cat:
        reason = f"Because you've been looking at {top_cat.lower()}" + (f", like the {anchor['name']}" if anchor else "")
    else:
        reason = "Picked for you"
    return {"reason": reason, "based_on": viewed[:5], "product_ids": [p["product_id"] for p in ranked[:limit]]}
