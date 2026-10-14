"""Campus Customs API (FastAPI).

  Products  - /api/categories, /api/products, /api/products/{id}, /media/products/*  (Problem 3)
  Accounts  - /api/auth/register, /api/auth/login, /api/auth/me                     (Problem 4)
  Chat      - /api/chat (PydanticAI agent), /api/chat/history                       (Problem 5)
  Memory    - logged-in chats saved to chat_messages and reloaded; page context      (Problem 8)
  Shop      - cart quote, checkout (guest or logged in), click history,
              recommendations, staff restock purchase list                          (Problem 9)
  Safety    - payment method required, guest phone/email/name, trackable order
              numbers, hourly inventory audit, agent audit trail                    (Problem 12)

Run from the backend/ folder:
    uvicorn main:app --reload --port 8000
"""

import asyncio
import logging
import os
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import Depends, FastAPI, Header, HTTPException  # noqa: E402
from pydantic import Field  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import agent  # noqa: E402
import auth  # noqa: E402
import db  # noqa: E402
import shop  # noqa: E402
from models import ChatHistoryMessage, ChatRequest, ChatResponse, ProductCard, Size  # noqa: E402

log = logging.getLogger("campus_customs")

INVENTORY_CHECK_SECONDS = int(os.getenv("INVENTORY_CHECK_SECONDS", "3600"))  # hourly by default


async def hourly_inventory_check():
    """Safety rule: re-audit inventory every hour so low / sold-out sizes are caught before
    shoppers try to buy them (checkout also re-checks stock inside its own transaction)."""
    while True:
        await asyncio.sleep(INVENTORY_CHECK_SECONDS)
        try:
            summary = await asyncio.to_thread(shop.inventory_check, "scheduled (hourly)")
            log.info("Inventory check: %s", summary)
        except Exception:
            log.exception("Scheduled inventory check failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Problem 9/12: make sure the shop tables exist, run one inventory audit now, then every hour.
    shop.ensure_tables()
    await asyncio.to_thread(shop.inventory_check, "startup")
    task = asyncio.create_task(hourly_inventory_check())
    yield
    task.cancel()


app = FastAPI(title="Campus Customs API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Product photos: /media/products/<file>.jpg -> data/products/<file>.jpg
app.mount("/media/products", StaticFiles(directory=db.DATA_DIR / "products"), name="products")




@app.get("/api/health")
def health():
    return {"ok": True, "model": agent.SMART_MODEL_NAME, "fallback_model": agent.MODEL_NAME}


# ---------------------------------------------------------------- products

@app.get("/api/categories")
def categories():
    return db.list_categories()


@app.get("/api/products")
def products(category: str | None = None, q: str | None = None, ids: str | None = None):
    items = db.list_products()
    if ids:  # comma-separated product_ids, e.g. the chat's picks; keeps the given order
        wanted = [i for i in ids.split(",") if i]
        by_id = {p["product_id"]: p for p in items}
        items = [by_id[i] for i in wanted if i in by_id]
    if category:
        items = [p for p in items if p["category"].lower() == category.lower()]
    if q:
        words = [w for w in re.findall(r"[a-z0-9]+", q.lower()) if len(w) > 1]
        items = [p for p in items if all(w in _haystack(p) for w in words)]
    return items


@app.get("/api/products/{product_id}")
def product(product_id: str):
    p = db.get_product(product_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return p


def _haystack(p: dict) -> str:
    return " ".join([p["name"], p["garment_type"], p["category"], p["description"],
                     *p["colors"], *p["search_tags"]]).lower()


# ---------------------------------------------------------------- accounts

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def _session(user: dict) -> dict:
    return {"token": auth.create_token(user["id"]), "user": user}


def optional_user(authorization: str | None = Header(default=None)) -> dict | None:
    """Reads "Authorization: Bearer <token>"; returns the user, or None for guests / bad tokens."""
    token = (authorization or "").removeprefix("Bearer ").strip()
    user_id = auth.user_id_from_token(token) if token else None
    return auth.get_user(user_id) if user_id else None


def current_user(user: dict | None = Depends(optional_user)) -> dict:
    if user is None:
        raise HTTPException(status_code=401, detail="Please log in.")
    return user


@app.post("/api/auth/register", status_code=201)
def register(req: RegisterRequest):
    try:
        user = auth.register(req.first_name, req.last_name, req.email, req.password, req.confirm_password)
    except auth.AuthError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return _session(user)


@app.post("/api/auth/login")
def login(req: LoginRequest):
    try:
        user = auth.login(req.email, req.password)
    except auth.AuthError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return _session(user)


@app.get("/api/auth/me")
def me(user: dict = Depends(current_user)):
    return user


# ---------------------------------------------------------------- chat (agent)

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user: dict | None = Depends(optional_user)):
    """Website message -> Handsome Dan's reply.

    Guests: history comes from the request and nothing is stored.
    Logged in: history is loaded from chat_messages, and this exchange is saved there afterwards.
    req.page tells the agent which page/product the shopper is looking at.
    """
    try:
        response = await agent.chat(req.message, req.history, user, req.page, req.visitor_id)
    except Exception:
        log.exception("Chat agent failed")
        raise HTTPException(
            status_code=503,
            detail="Handsome Dan is having trouble answering right now. Please try again in a moment.",
        )
    if user:
        db.save_chat_turn(user["id"], req.message, response.reply, [c.product_id for c in response.products])
    return response


@app.get("/api/chat/history", response_model=list[ChatHistoryMessage])
def chat_history(user: dict = Depends(current_user), limit: int = 40):
    """The logged-in shopper's saved conversation (oldest first), so it reloads when they return.
    Product cards are rebuilt from the database, so prices and stock are current, not as saved."""
    return [
        ChatHistoryMessage(role=m["role"], content=m["content"], products=agent.product_cards(m["product_ids"]),
                           created_at=m["created_at"])
        for m in db.load_chat_history(user["id"], limit=min(limit, 100))
    ]



# ---------------------------------------------------------------- shop: cart + checkout (Problem 9)

class CartItem(BaseModel):
    product_id: str = Field(max_length=120)
    size: Size
    quantity: int = Field(ge=1, le=shop.MAX_LINE_QTY)


class QuoteRequest(BaseModel):
    items: list[CartItem] = Field(max_length=30)


class OrderRequest(QuoteRequest):
    customer_name: str = Field(max_length=120)
    email: str = Field(max_length=200)
    phone: str | None = Field(None, max_length=30)            # required for guests (checked in shop.py)
    fulfillment: str = "pickup"
    shipping_address: str | None = Field(None, max_length=400)
    payment_method: str | None = Field(None, max_length=30)   # required: no payment method -> no order


@app.post("/api/cart/quote")
def cart_quote(req: QuoteRequest):
    """Re-price the cart from the database (live prices and stock; problems listed per line)."""
    return shop.quote([i.model_dump() for i in req.items])


@app.post("/api/orders", status_code=201)
def place_order(req: OrderRequest, user: dict | None = Depends(optional_user)):
    """Checkout. Works for guests (no token) and logged-in shoppers. No payment details are taken:
    orders are paid at pickup / on delivery in this class project."""
    try:
        return shop.place_order([i.model_dump() for i in req.items], req.customer_name, req.email,
                                req.fulfillment, req.shipping_address, user, req.phone, req.payment_method)
    except shop.ShopError as e:
        raise HTTPException(status_code=e.status, detail=e.message)


@app.get("/api/orders/track")
def track_order(order_number: str, contact: str):
    """Track an order with its transaction number + the email or phone used at checkout."""
    try:
        return shop.track_order(order_number, contact)
    except shop.ShopError as e:
        raise HTTPException(status_code=e.status, detail=e.message)


@app.get("/api/payment-methods")
def payment_methods():
    return [{"id": k, "label": label, "fulfillment": f} for k, (label, f) in shop.PAYMENT_METHODS.items()]


# ---------------------------------------------------------------- shop: click history + recommendations

class ViewEvent(BaseModel):
    product_id: str = Field(max_length=120)
    visitor_id: str | None = Field(None, max_length=64)
    source: str = Field("product_page", max_length=30)


@app.post("/api/events/view", status_code=204)
def record_view(ev: ViewEvent, user: dict | None = Depends(optional_user)):
    """Called when a shopper opens a product page: the click history behind recommendations."""
    shop.record_view(ev.product_id, user, ev.visitor_id, ev.source)


@app.get("/api/recommendations")
def recommendations(visitor_id: str | None = None, exclude: str = "", limit: int = 4,
                    user: dict | None = Depends(optional_user)):
    rec = shop.recommend(user["id"] if user else None, visitor_id, [e for e in exclude.split(",") if e],
                         limit=max(1, min(limit, 8)))
    cards: list[ProductCard] = agent.product_cards(rec["product_ids"], limit=8)
    return {"reason": rec["reason"], "products": cards}


# ---------------------------------------------------------------- staff: restock purchase list

def staff_only(x_staff_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("STAFF_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="Set STAFF_KEY in .env to enable staff endpoints.")
    if not x_staff_key or not secrets.compare_digest(x_staff_key, expected):
        raise HTTPException(status_code=403, detail="Staff key required.")


@app.get("/api/staff/inventory-checks", dependencies=[Depends(staff_only)])
def staff_inventory_checks(limit: int = 20):
    """History of the hourly inventory audits (newest first)."""
    return {"interval_seconds": INVENTORY_CHECK_SECONDS, "checks": shop.inventory_checks(min(limit, 100))}


@app.get("/api/staff/purchase-list", dependencies=[Depends(staff_only)])
def staff_purchase_list(status: str = "open"):
    """The business's restock list: every low/sold-out size with the quantity to reorder."""
    return shop.purchase_list(status)
