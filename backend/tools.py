"""Tools the Campus Customs shop agent can call.

Every tool reads data/campus_customs.db (through db.py) at call time, so prices and stock
in the agent's answers are always the live values - the model is told never to guess them.
All tools are read-only.

  search_products   - find products (keywords, category, garment color, size, max price)
  get_product_info  - one product's description, price, colors and sizes in stock
  get_prices        - prices for one or more products in a single call
  check_stock       - live stock for every size, or one size with a clear sold-out message
  list_categories   - categories with counts and price ranges
  get_customer_profile - the logged-in shopper's own name, email and chat activity (from deps)
  get_recommendations  - in-stock picks based on the shopper's click history (product_views)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import db
import shop
from pydantic_ai import RunContext

from models import (
    LOW_STOCK_MAX,
    CategoryInfo,
    CustomerProfile,
    PriceLookup,
    PriceQuote,
    Recommendation,
    ProductInfo,
    ProductSummary,
    SearchResult,
    Size,
    SizeStatus,
    StockReport,
    stock_status,
)

MAX_RESULTS = 12  # enough to fill the on-page results grid

# Shopper words -> words used in the catalogue.
SYNONYMS = {
    "grey": "gray",
    "tee": "t-shirt",
    "tees": "t-shirt",
    "tshirt": "t-shirt",
    "tshirts": "t-shirt",
    "shirt": "t-shirt",
    "sweater": "sweatshirt",
    "hoody": "hoodie",
    "hoodies": "hoodie",
    "crew": "crewneck",
    "quarterzip": "quarter-zip",
    "jackets": "jacket",
    "dog": "bulldog",
    "mascot": "bulldog",
}
STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "in", "of", "to", "me", "my", "i", "you", "do",
    "have", "any", "some", "show", "want", "need", "looking", "like", "would", "please", "your",
    "yale", "campus", "customs", "is", "are", "it", "that", "this", "what", "which", "something",
}


@dataclass
class Customer:
    """The logged-in shopper, as the agent sees them (loaded from the users table; no password hash)."""
    user_id: int
    first_name: str
    last_name: str
    email: str
    member_since: str


@dataclass
class ViewedProduct:
    """The product on the page the shopper is looking at (looked up in the catalogue, not trusted from the browser)."""
    product_id: str
    name: str
    category: str
    price: float
    main_color: str
    colors: list[str]


@dataclass
class PageView:
    """Where the shopper is on the site when they send a message."""
    path: str
    page_type: str  # home | products | product | about | login | register | other
    product: ViewedProduct | None = None
    category: str | None = None
    search: str | None = None
    results_title: str | None = None


@dataclass
class ShopDeps:
    """Per-request context passed to the agent: who is chatting and what page they're on."""
    customer: Customer | None = None
    page: PageView | None = None
    visitor_id: str | None = None  # anonymous browser id: lets guests' clicks count too


def _words(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z0-9\-]+", text.lower()):
        w = SYNONYMS.get(w, w)
        if w not in STOPWORDS and len(w) > 1:
            out.append(w)
    return out


def _haystack(p: dict) -> str:
    return " ".join([p["name"], p["garment_type"], p["category"], p["description"],
                     *p["colors"], *p["search_tags"]]).lower()


def _main_color(p: dict) -> str:
    """Garment color. `colors` lists the garment color first, then print/lettering colors."""
    return p["colors"][0] if p["colors"] else ""


def _summary(p: dict) -> ProductSummary:
    desc = p["description"]
    return ProductSummary(
        product_id=p["product_id"],
        name=p["name"],
        category=p["category"],
        price=p["price"],
        main_color=_main_color(p),
        colors=p["colors"],
        sizes_in_stock=[s["size"] for s in p["inventory"] if s["quantity"] > 0],
        sold_out_sizes=[s["size"] for s in p["inventory"] if s["quantity"] == 0],
        short_description=desc if len(desc) <= 160 else desc[:157].rsplit(" ", 1)[0] + "...",
    )


def _find(product_id: str) -> dict | None:
    p = db.get_product(product_id.strip())
    if p is None:  # tolerate the model passing a product name instead of the id
        wanted = product_id.strip().lower()
        p = next((x for x in db.list_products() if x["name"].lower() == wanted), None)
    return p


# ------------------------------------------------------------------ tools

def list_categories() -> list[CategoryInfo]:
    """List the store's product categories with how many styles each has and their price range.

    Use this for broad questions like "what do you sell?" or "what's your cheapest item?".
    """
    return [CategoryInfo(name=c["name"], product_count=c["count"], min_price=c["min_price"],
                         max_price=c["max_price"]) for c in db.list_categories()]


def search_products(
    query: str = "",
    category: str | None = None,
    color: str | None = None,
    size: Size | None = None,
    max_price: float | None = None,
    limit: int = 6,
) -> SearchResult:
    """Search the catalogue. Every argument is optional; combine them to narrow results.

    Args:
        query: Free-text keywords, e.g. "hockey", "bulldog", "residential college", "Harvard game".
        category: One of the store categories (T-Shirts, Crewnecks, Hoodies, Quarter-Zips,
            Full-Zip Hoodies, Jackets & Fleece, Performance Long Sleeves). Loose spellings are OK.
        color: A color such as "navy", "gray", "white", "red".
        size: Only return products that currently have this size in stock. Matching products
            that are sold out in this size are listed in `note` instead.
        max_price: Only return products at or below this price in USD.
        limit: Max products to return (1-12). Use 12 when the shopper is browsing a type of item.
    """
    products = db.list_products()
    note = []

    if category:
        cat = category.lower().strip().rstrip("s")
        cat = {"tee": "t-shirt", "tshirt": "t-shirt", "sweatshirt": "crewneck"}.get(cat, cat)
        # An exact store category ("Hoodies") matches only that category, so counts agree with the
        # website's category filter; anything looser ("zip", "fleece") matches the garment type too.
        exact = [p for p in products if p["category"].lower().rstrip("s") == cat]
        matched = exact or [p for p in products if cat in p["category"].lower() or cat in p["garment_type"].lower()]
        if matched:
            products = matched
        else:
            note.append(f"No category matched '{category}', so all categories were searched.")
    if color:
        # Match the garment color first; products that only use the color in their
        # print/lettering are a fallback (a gray sweatshirt with navy letters isn't "navy").
        c = SYNONYMS.get(color.lower(), color.lower())
        garment = [p for p in products if c in _main_color(p).lower() or
                   (not p["colors"] and c in p["description"].lower()[:40])]
        accent = [p for p in products if p not in garment and any(c in col.lower() for col in p["colors"])]
        if garment:
            products = garment
        else:
            products = accent
            if accent:
                note.append(f"No garments are {color}; these only use {color} in the print or lettering.")
    if max_price is not None:
        products = [p for p in products if p["price"] <= max_price]

    words = _words(query)
    if words:
        scored = []
        for p in products:
            hay, name = _haystack(p), p["name"].lower()
            score = sum(1 for w in words if w in hay or w.rstrip("s") in hay)
            # Words found in the product's name rank it higher, so "ice hockey hoodie"
            # puts "Ice Hockey Left Chest Hoodie" first.
            name_hits = sum(1 for w in words if w in name or w.rstrip("s") in name)
            if score:
                scored.append((score, name_hits, p["total_stock"], p))
        scored.sort(key=lambda t: (-t[0], -t[1], -t[2]))
        best = scored[0][0] if scored else 0
        # Prefer products matching every keyword; fall back to partial matches.
        products = [p for s, _, _, p in scored if s == best] if best == len(words) else [p for *_, p in scored]
        if scored and best < len(words):
            note.append("No product matched every keyword; these are the closest partial matches.")
        if not scored:
            note.append("No products matched these keywords. We may not carry this item.")

    # Size goes last and never hides a match silently: if a product the shopper may mean is
    # sold out in their size, the agent is told, so it can say so instead of skipping it.
    if size:
        in_size = [p for p in products if any(s["size"] == size and s["quantity"] > 0 for s in p["inventory"])]
        sold_out = [p for p in products if p not in in_size]
        if sold_out:
            names = ", ".join(f"{p['name']} ({p['product_id']})" for p in sold_out[:5])
            note.append(f"Sold out in size {size}: {names}.")
        products = in_size

    limit = max(1, min(limit, MAX_RESULTS))
    prices = [p["price"] for p in products]
    return SearchResult(total_matches=len(products), min_price=min(prices, default=None),
                        max_price=max(prices, default=None), products=[_summary(p) for p in products[:limit]],
                        note=" ".join(note))


def get_product_info(product_id: str) -> ProductInfo | str:
    """Look up one product's full description, price, colors and which sizes are in stock.

    Use for "tell me about…", "what does it look like?", "what colors?" and "how much is it?"
    about a specific item. For exact stock numbers or one size, use check_stock.

    Args:
        product_id: The product_id from a search result (e.g. "basic-hoodie-big-yale").
    """
    p = _find(product_id)
    if p is None:
        return _not_found(product_id)
    return ProductInfo(
        product_id=p["product_id"], name=p["name"], category=p["category"], garment_type=p["garment_type"],
        price=p["price"], description=p["description"], main_color=_main_color(p), colors=p["colors"],
        tags=p["search_tags"],
        sizes_in_stock=[s["size"] for s in p["inventory"] if s["quantity"] > 0],
        sold_out_sizes=[s["size"] for s in p["inventory"] if s["quantity"] == 0],
        total_stock=p["total_stock"],
    )


def get_prices(product_ids: list[str]) -> PriceLookup:
    """Look up the current catalogue price of one or more products in a single call.

    Use for "how much is…?", comparing prices, or adding up a few items.

    Args:
        product_ids: One or more product_id values from search results (max 10).
    """
    quotes, missing = [], []
    for pid in list(dict.fromkeys(product_ids))[:10]:
        p = _find(pid)
        if p is None:
            missing.append(pid)
        else:
            quotes.append(PriceQuote(product_id=p["product_id"], name=p["name"], category=p["category"],
                                     price=p["price"]))
    return PriceLookup(prices=quotes, not_found=missing)


def check_stock(product_id: str, size: Size | None = None) -> StockReport | str:
    """Check live stock for one product: every size, or focused on the shopper's size.

    Use for "is it in stock?", "do you have it in M?", "how many are left?" and
    "what sizes are available?". Always call this before saying anything about stock.

    Args:
        product_id: The product_id from a search result.
        size: Optional. XS, S, M, L, XL or XXL when the shopper asks about one size.
    """
    p = _find(product_id)
    if p is None:
        return _not_found(product_id)
    sizes = [SizeStatus(size=s["size"], quantity=s["quantity"], status=stock_status(s["quantity"]))
             for s in p["inventory"]]
    in_stock = [s.size for s in sizes if s.quantity > 0]
    sold_out = [s.size for s in sizes if s.quantity == 0]
    report = StockReport(
        product_id=p["product_id"], name=p["name"], price=p["price"], sizes=sizes,
        sizes_in_stock=in_stock, sold_out_sizes=sold_out, total_stock=p["total_stock"], summary="",
    )
    if size:
        chosen = next((s for s in sizes if s.size == size), None)
        qty = chosen.quantity if chosen else 0
        report.requested_size = size
        report.requested_size_quantity = qty
        report.requested_size_status = stock_status(qty)
        if qty == 0:
            others = ", ".join(in_stock) or "no other sizes"
            report.summary = f"{p['name']} is SOLD OUT in size {size}. Sizes in stock: {others}."
        elif qty <= LOW_STOCK_MAX:
            report.summary = f"{p['name']} is in stock in size {size}, but only {qty} left (low stock)."
        else:
            report.summary = f"{p['name']} is in stock in size {size} ({qty} available)."
    elif not in_stock:
        report.summary = f"{p['name']} is sold out in every size."
    else:
        report.summary = (f"{p['name']} is in stock in {', '.join(in_stock)}"
                          + (f"; sold out in {', '.join(sold_out)}." if sold_out else " (every size)."))
    return report


def get_customer_profile(ctx: RunContext[ShopDeps]) -> CustomerProfile | str:
    """Look up the logged-in shopper's own account: name, email, member-since date and chat activity.

    Use when the shopper asks about their account ("what email is my account under?", "when did I
    join?", "have we chatted before?"). Only ever returns the shopper's OWN details.
    """
    c = ctx.deps.customer
    if c is None:
        return "The shopper is a guest (not logged in), so there is no account to look up."
    count, last = db.chat_stats(c.user_id)
    return CustomerProfile(first_name=c.first_name, last_name=c.last_name, email=c.email,
                           member_since=c.member_since, saved_messages=count, last_chat_at=last)


def get_recommendations(ctx: RunContext[ShopDeps], limit: int = 4) -> Recommendation:
    """Suggest in-stock products based on what THIS shopper has clicked on before (their product views).

    Use for "what would you recommend?", "anything else I'd like?", "surprise me", or to suggest
    something relevant after answering a question. Falls back to popular items if there's no history.

    Args:
        limit: How many picks to return (1-6).
    """
    c, page = ctx.deps.customer, ctx.deps.page
    exclude = [page.product.product_id] if page and page.product else []
    rec = shop.recommend(c.user_id if c else None, ctx.deps.visitor_id, exclude, limit=max(1, min(limit, 6)))
    viewed = [db.get_product(pid) for pid in shop.recent_views(c.user_id if c else None, ctx.deps.visitor_id, 5)]
    picks = [_summary(p) for pid in rec["product_ids"] if (p := db.get_product(pid))]
    return Recommendation(reason=rec["reason"], recently_viewed=[p["name"] for p in viewed if p], picks=picks)


def _not_found(product_id: str) -> str:
    return f"No product with id '{product_id}'. Use search_products to find the right product_id first."


SHOP_TOOLS = [search_products, get_product_info, get_prices, check_stock, list_categories, get_customer_profile,
              get_recommendations]

# Which "checked" badge each tool earns in the chat widget.
TOOL_BADGES = {
    "check_stock": "live stock",
    "get_prices": "catalogue prices",
    "get_product_info": "product details",
    "search_products": "catalogue search",
    "get_customer_profile": "your account",
    "get_recommendations": "your browsing history",
}
