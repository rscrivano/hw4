"""Structured types for the Campus Customs shop agent and its chat API.

Three groups:
  * Tool results - what tools.py hands the agent (always read live from the database).
  * Agent output - ShopReply, the structured answer the model must return.
  * API types    - what main.py sends to / receives from the website's chat widget.

Design rule: prices and stock numbers only ever come from these tool results. The agent
never writes them into product cards itself - it returns product_ids, and the backend builds
each ProductCard from the database.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Size = Literal["XS", "S", "M", "L", "XL", "XXL"]
StockStatus = Literal["in stock", "low stock", "sold out"]
LOW_STOCK_MAX = 5  # 1-5 units left counts as "low stock"


def stock_status(quantity: int) -> StockStatus:
    if quantity <= 0:
        return "sold out"
    return "low stock" if quantity <= LOW_STOCK_MAX else "in stock"


# ------------------------------------------------------------------ tool results

class SizeStatus(BaseModel):
    """Stock for one size, with a ready-made status label so every answer uses the same words."""
    size: str
    quantity: int = Field(description="Units on hand right now.")
    status: StockStatus = Field(description="'sold out' = 0, 'low stock' = 1-5, 'in stock' = 6+.")


class ProductSummary(BaseModel):
    """One search hit: enough for the agent to choose and describe a product."""
    product_id: str
    name: str
    category: str
    price: float
    main_color: str = Field(description="The garment's own color.")
    colors: list[str] = Field(description="Garment color first, then print/lettering colors.")
    sizes_in_stock: list[str] = Field(description="Sizes with quantity > 0.")
    sold_out_sizes: list[str]
    short_description: str


class SearchResult(BaseModel):
    total_matches: int = Field(description="How many products matched before the limit was applied.")
    min_price: float | None = Field(None, description="Lowest price across ALL matches, not just those shown.")
    max_price: float | None = Field(None, description="Highest price across ALL matches, not just those shown.")
    products: list[ProductSummary]
    note: str = ""


class ProductInfo(BaseModel):
    """get_product_info: everything a shopper might ask about one product."""
    product_id: str
    name: str
    category: str
    garment_type: str
    price: float = Field(description="Price in USD from the catalogue. Quote exactly as $0.00.")
    description: str = Field(description="Full catalogue description - use it for 'what does it look like?'.")
    main_color: str
    colors: list[str]
    tags: list[str]
    sizes_in_stock: list[str]
    sold_out_sizes: list[str]
    total_stock: int


class PriceQuote(BaseModel):
    product_id: str
    name: str
    category: str
    price: float = Field(description="Price in USD from the catalogue.")


class PriceLookup(BaseModel):
    """get_prices: prices for one or more products in a single call."""
    prices: list[PriceQuote]
    not_found: list[str] = Field(default_factory=list, description="Ids that don't exist - search for them first.")


class StockReport(BaseModel):
    """check_stock: live stock for one product, optionally focused on the shopper's size."""
    product_id: str
    name: str
    price: float
    requested_size: str | None = Field(None, description="The size the shopper asked about, if any.")
    requested_size_quantity: int | None = None
    requested_size_status: StockStatus | None = None
    sizes: list[SizeStatus] = Field(description="Every size, XS to XXL, with quantity and status.")
    sizes_in_stock: list[str]
    sold_out_sizes: list[str]
    total_stock: int
    summary: str = Field(description="One plain-English sentence stating the facts; safe to paraphrase to the shopper.")


class CustomerProfile(BaseModel):
    """get_customer_profile: who is chatting (logged-in shoppers only). Never includes the password hash."""
    first_name: str
    last_name: str
    email: str
    member_since: str = Field(description="Date the account was created (YYYY-MM-DD).")
    saved_messages: int = Field(description="How many chat messages are saved for this shopper.")
    last_chat_at: str | None = Field(None, description="When they last chatted, if ever.")


class Recommendation(BaseModel):
    """get_recommendations: products picked from the shopper's click history (product_views)."""
    reason: str = Field(description="Why these were picked, e.g. 'Because you viewed Basic Hoodie Big Yale'.")
    recently_viewed: list[str] = Field(description="Names of products the shopper opened recently, newest first.")
    picks: list[ProductSummary] = Field(description="In-stock products that match their interests.")


class CategoryInfo(BaseModel):
    name: str
    product_count: int
    min_price: float
    max_price: float


# ------------------------------------------------------------------ agent output

class PageSearch(BaseModel):
    """The agent's structured search matches for the website to show as product cards on the page."""
    title: str = Field(description="Short heading for the results, e.g. 'Hoodies' or 'Navy crewnecks in size M'.")
    product_ids: list[str] = Field(
        description="ALL matching product_id values from search_products, best match first (max 12)."
    )
    total_matches: int = Field(0, description="total_matches from search_products (may be more than shown).")
    category: str | None = Field(
        None, description="The store category searched, if exactly one (enables a 'see all' link). Else null."
    )


class ShopReply(BaseModel):
    """What the agent returns for every chat turn."""
    reply: str = Field(
        description="The message shown to the shopper, in Handsome Dan's friendly voice. "
        "Plain text or light markdown (bold, short bullet lists). Keep it under ~120 words."
    )
    product_ids: list[str] = Field(
        default_factory=list,
        description="product_id values (from tool results only) to show as cards INSIDE the chat, best match "
        "first. Max 3 when page_results is set, else max 6. Empty when no product is relevant.",
    )
    page_results: PageSearch | None = Field(
        None,
        description="Set when the shopper is browsing a type of item ('what hoodies do you have?'): the website "
        "shows these matches as product cards on the page. Null for single-item price/stock questions and "
        "for off-topic or no-match replies.",
    )
    focus_size: Size | None = Field(
        None, description="The size the shopper asked about (e.g. 'M'), so the cards can highlight it. Else null."
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Up to 3 short follow-up questions the shopper might tap next, e.g. 'Is the M in stock?'.",
    )


# ------------------------------------------------------------------ API types

class ProductCard(BaseModel):
    """A product card for the chat widget, built from the database (never by the model)."""
    product_id: str
    name: str
    category: str
    price: float
    image_url: str
    short_description: str = Field("", description="First sentence or so of the catalogue description.")
    colors: list[str]
    sizes_in_stock: list[str]
    total_stock: int
    stock: list[SizeStatus] = Field(default_factory=list, description="Per-size stock for the size chips.")


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class PageContext(BaseModel):
    """What the shopper is looking at when they send a message (sent by the website)."""
    path: str = Field("/", max_length=300, description="Current URL path, e.g. /products/crew-left-chest-hoodie.")
    product_id: str | None = Field(None, max_length=120, description="Set on a product detail page.")
    category: str | None = Field(None, max_length=60, description="Category filter on the Products page.")
    search: str | None = Field(None, max_length=100, description="Text in the Products page search box.")
    results_title: str | None = Field(None, max_length=100, description="Title of chat results shown on the page.")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    # Guests: the website sends the conversation so far. Logged-in shoppers: ignored, the server
    # loads their saved history from the chat_messages table instead.
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)
    page: PageContext | None = None
    visitor_id: str | None = Field(None, max_length=64, description="Anonymous browser id (guest click history).")


Checked = Literal["live stock", "catalogue prices", "product details", "catalogue search", "your account",
                  "your browsing history"]


class PageResults(BaseModel):
    """API contract for chat search -> page: what the website renders as product cards on the page."""
    title: str
    total_matches: int
    category: str | None = None
    products: list[ProductCard]


class ChatResponse(BaseModel):
    reply: str
    products: list[ProductCard] = Field(default_factory=list)
    page_results: PageResults | None = Field(
        None, description="Search matches to render as product cards on the page (null = leave the page alone)."
    )
    focus_size: Size | None = None
    suggestions: list[str] = Field(default_factory=list)
    checked: list[Checked] = Field(
        default_factory=list, description="Which database lookups the agent ran this turn (shown as badges)."
    )


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    created_at: str
