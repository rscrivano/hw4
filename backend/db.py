"""Read access to data/campus_customs.db for the Campus Customs API."""

import json
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

# garment_type has ~22 raw spellings; map them onto shopper-facing categories.
# Order matters: the first matching rule wins.
CATEGORY_RULES = [
    ("Jackets & Fleece", ("jacket", "fleece")),
    ("Full-Zip Hoodies", ("full-zip hood",)),
    ("Quarter-Zips", ("quarter-zip",)),
    ("Performance Long Sleeves", ("performance",)),
    ("Hoodies", ("hood",)),
    ("Crewnecks", ("crewneck", "mockneck")),
    ("T-Shirts", ("t-shirt",)),
]
CATEGORY_ORDER = [name for name, _ in CATEGORY_RULES]


def category_for(garment_type: str) -> str:
    g = garment_type.lower()
    for name, keys in CATEGORY_RULES:
        if any(k in g for k in keys):
            return name
    return "Other"


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _inventory(con: sqlite3.Connection) -> dict[str, list[dict]]:
    stock: dict[str, list[dict]] = {}
    for r in con.execute("SELECT product_id, size, quantity FROM inventory"):
        stock.setdefault(r["product_id"], []).append({"size": r["size"], "quantity": r["quantity"]})
    for sizes in stock.values():
        sizes.sort(key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else 99)
    return stock


def _product(row: sqlite3.Row, sizes: list[dict]) -> dict:
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "category": category_for(row["garment_type"]),
        "description": row["description"],
        "colors": json.loads(row["colors"]),
        "search_tags": json.loads(row["search_tags"]),
        "image_url": f"/media/{row['image_file_path']}",
        "price": row["price"],
        "inventory": sizes,
        "total_stock": sum(s["quantity"] for s in sizes),
    }


def list_products() -> list[dict]:
    with connect() as con:
        stock = _inventory(con)
        rows = con.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
    return [_product(r, stock.get(r["product_id"], [])) for r in rows]


def get_product(product_id: str) -> dict | None:
    with connect() as con:
        row = con.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            return None
        sizes = [dict(r) for r in con.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,))]
    sizes.sort(key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else 99)
    return _product(row, sizes)


def list_categories() -> list[dict]:
    """One entry per category with count, price range and a sample image."""
    groups: dict[str, list[dict]] = {}
    for p in list_products():
        groups.setdefault(p["category"], []).append(p)
    out = []
    for name in CATEGORY_ORDER + ["Other"]:
        items = groups.get(name)
        if not items:
            continue
        prices = [p["price"] for p in items]
        out.append({
            "name": name,
            "count": len(items),
            "min_price": min(prices),
            "max_price": max(prices),
            "image_url": items[0]["image_url"],
        })
    return out


# ------------------------------------------------------------------ customer memory (Problem 8)
# Chat history for logged-in shoppers lives in the existing chat_messages table:
#   id, user_id -> users.id, role ('user' | 'assistant'), content, products_json, created_at


def get_customer(user_id: int) -> dict | None:
    """The customer fields the agent may see. Never the password hash."""
    with connect() as con:
        row = con.execute(
            "SELECT id, first_name, last_name, name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def save_chat_turn(user_id: int, message: str, reply: str, product_ids: list[str]) -> None:
    """Store one exchange (shopper message + assistant reply) for a logged-in shopper."""
    products_json = json.dumps([{"product_id": pid} for pid in product_ids]) if product_ids else None
    with connect() as con:
        con.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)", (user_id, message))
        con.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply, products_json),
        )


def load_chat_history(user_id: int, limit: int = 40) -> list[dict]:
    """The shopper's most recent saved messages, oldest first, with the product_ids shown with each reply."""
    with connect() as con:
        rows = con.execute(
            "SELECT role, content, products_json, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit),
        ).fetchall()
    history = []
    for r in reversed(rows):
        saved = json.loads(r["products_json"]) if r["products_json"] else []
        # Older rows (from the provided database) stored full product dicts; only the id is needed.
        ids = [p["product_id"] for p in saved if isinstance(p, dict) and "product_id" in p]
        history.append({"role": r["role"], "content": r["content"], "product_ids": ids,
                         "created_at": r["created_at"]})
    return history


def chat_stats(user_id: int) -> tuple[int, str | None]:
    """(number of saved messages, timestamp of the latest one) for a shopper."""
    with connect() as con:
        row = con.execute(
            "SELECT COUNT(*), MAX(created_at) FROM chat_messages WHERE user_id = ?", (user_id,)
        ).fetchone()
    return row[0], row[1]
