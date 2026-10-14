"""Campus Customs shop agent - entry point and wiring.

    prompts/prompt.md  -> system prompt (Handsome Dan's voice, rules, safety basics)
    tools.py           -> read-only database tools the agent can call
    models.py          -> structured types (ShopReply output, ProductCard, chat API types)

Model: AI calls go through Portkey's OpenAI-compatible gateway using PORTKEY_API_KEY.
Answering a shopper means chaining tool calls and reasoning about stock, so the agent runs on
the stronger model (OPENAI_SMART_MODEL, default gpt-5.6-terra) and automatically falls back
to the everyday model (OPENAI_MODEL, default gpt-5.6-luna) if that call fails.

Quick test from the backend/ folder:
    python agent.py "do you have a navy hoodie in medium?"
    python agent.py --trace "..."      # also prints every tool call the agent makes
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from pydantic_ai import Agent, RunContext, UsageLimits  # noqa: E402
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart  # noqa: E402
from pydantic_ai.models.fallback import FallbackModel  # noqa: E402
from pydantic_ai.models.openai import OpenAIResponsesModel  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402

import audit  # noqa: E402
import db  # noqa: E402
import shop  # noqa: E402
from models import (  # noqa: E402
    ChatResponse,
    ChatTurn,
    PageContext,
    PageResults,
    PageSearch,
    ProductCard,
    ShopReply,
    SizeStatus,
    stock_status,
)
from tools import SHOP_TOOLS, TOOL_BADGES, Customer, PageView, ShopDeps, ViewedProduct, _main_color  # noqa: E402

PROMPT_PATH = HERE / "prompts" / "prompt.md"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
SMART_MODEL_NAME = os.getenv("OPENAI_SMART_MODEL", "gpt-5.6-terra")
MAX_CARDS = 6            # product cards inside the chat bubble
MAX_PAGE_CARDS = 12      # product cards the chat puts on the page
CHAT_CARDS_WITH_PAGE = 3  # when results go to the page, the chat bubble shows just the top picks
MAX_HISTORY_TURNS = 12   # earlier turns are dropped to keep requests small
MAX_AGENT_REQUESTS = 8   # a normal turn needs 2-4 model requests (tool calls + final answer)


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_model() -> FallbackModel:
    key = os.getenv("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Add it to your environment or the project .env file.")
    provider = OpenAIProvider(base_url=PORTKEY_BASE_URL, api_key=key)
    # The Portkey deployment only supports tool calls (used for structured output) on the
    # Responses endpoint, hence OpenAIResponsesModel. Note: Portkey routes unknown model names
    # to gpt-5.6-luna silently, so check the spelling of OPENAI_SMART_MODEL.
    return FallbackModel(
        OpenAIResponsesModel(SMART_MODEL_NAME, provider=provider),
        OpenAIResponsesModel(MODEL_NAME, provider=provider),
    )


agent = Agent(
    build_model(),
    instructions=load_system_prompt(),
    deps_type=ShopDeps,
    output_type=ShopReply,
    tools=SHOP_TOOLS,
    model_settings={"openai_reasoning_effort": "low"},
    retries=2,
)


# ------------------------------------------------------------------ context: who + where (Problem 8)

@agent.instructions
def shopper_context(ctx: RunContext[ShopDeps]) -> str:
    """Adds who is chatting to the instructions on every turn (from deps, never from the message)."""
    c = ctx.deps.customer
    viewed = [p["name"] for pid in shop.recent_views(c.user_id if c else None, ctx.deps.visitor_id, 5)
              if (p := db.get_product(pid))]
    seen = (f"\nRecently viewed products (newest first): {'; '.join(viewed)}. Use these to suggest related "
            "items when it fits (get_recommendations), without being pushy.") if viewed else ""
    if c:
        return seen + (
            "\n## Shopper (logged in)\n"
            f"- Name: {c.first_name} {c.last_name}\n"
            f"- Email: {c.email}\n"
            f"- Member since: {c.member_since}\n"
            "Earlier messages in this conversation are this shopper's saved chat history, possibly from "
            "previous visits, so you can refer back to them (\"last time you were looking at...\"). "
            "Greet them by first name now and then. Only mention their email if they ask about their account."
        )
    return seen + (
        "\n## Shopper (guest)\n"
        "The shopper is not logged in. Help them fully. Their chat is not saved; if they want to pick up "
        "the conversation later, you may mention that logging in saves their chat. Never ask for an email "
        "or other personal details."
    )


@agent.instructions
def page_context(ctx: RunContext[ShopDeps]) -> str:
    """Adds what page the shopper is on, so "this", "it" and "this one" can be resolved."""
    page = ctx.deps.page
    if page is None:
        return ""
    lines = ["## Current page", f"- Path: {page.path} ({page.page_type} page)"]
    if page.product:
        v = page.product
        lines += [
            f"- The shopper is VIEWING this product right now: **{v.name}** (product_id `{v.product_id}`), "
            f"{v.category}, ${v.price:.2f}, garment color: {v.main_color or 'see description'}, "
            f"all colors listed: {', '.join(v.colors) or 'n/a'}.",
            "- If they say \"this\", \"it\", \"this one\" or ask about a color or size without naming a "
            "product, they mean this product. Use its product_id with the tools; don't ask which item they mean.",
        ]
    if page.category:
        lines.append(f"- They are browsing the Products page filtered to: {page.category}.")
    if page.search:
        lines.append(f"- Their Products page search box says: \"{page.search}\".")
    if page.results_title:
        lines.append(f"- Your earlier search results \"{page.results_title}\" are shown on their page.")
    return "\n".join(lines)


PAGE_TYPES = {"/": "home", "/products": "products", "/about": "about", "/login": "login", "/register": "register"}


def build_deps(user: dict | None, page: PageContext | None, visitor_id: str | None = None) -> ShopDeps:
    """Turn the request's login + page info into agent deps. Everything is re-read from the database:
    the browser only says *which* product is open, never its name, price or colors."""
    customer = None
    if user:
        row = db.get_customer(user["id"])
        if row:
            customer = Customer(user_id=row["id"], first_name=row["first_name"] or row["name"],
                                last_name=row["last_name"] or "", email=row["email"],
                                member_since=(row["created_at"] or "")[:10])
    view = None
    if page:
        product = None
        if page.product_id and (p := db.get_product(page.product_id)):
            product = ViewedProduct(product_id=p["product_id"], name=p["name"], category=p["category"],
                                    price=p["price"], main_color=_main_color(p), colors=p["colors"])
        page_type = "product" if product else PAGE_TYPES.get(page.path, "other")
        view = PageView(path=page.path, page_type=page_type, product=product, category=page.category,
                        search=page.search, results_title=page.results_title)
    return ShopDeps(customer=customer, page=view, visitor_id=visitor_id)


def to_message_history(history: list[ChatTurn]) -> list[ModelMessage]:
    """Guest chat turns sent by the website -> PydanticAI message history (text only)."""
    messages: list[ModelMessage] = []
    for turn in history[-MAX_HISTORY_TURNS:]:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


def saved_history(user_id: int) -> list[ModelMessage]:
    """Logged-in shopper's memory: their saved chat_messages -> PydanticAI message history.
    Assistant turns get a note of which products were shown, so "the first one" still resolves later."""
    messages: list[ModelMessage] = []
    for m in db.load_chat_history(user_id, limit=MAX_HISTORY_TURNS):
        if m["role"] == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=m["content"])]))
        else:
            text = m["content"]
            if m["product_ids"]:
                text += "\n[Products shown with this reply, in order: " + ", ".join(m["product_ids"]) + "]"
            messages.append(ModelResponse(parts=[TextPart(content=text)]))
    while messages and isinstance(messages[0], ModelResponse):  # history must start with a user turn
        messages.pop(0)
    return messages


def short_info(description: str, limit: int = 110) -> str:
    """First sentence of the catalogue description, trimmed to fit a card."""
    first = description.split(". ")[0].rstrip(".") + "."
    return first if len(first) <= limit else first[: limit - 1].rsplit(" ", 1)[0] + "…"


def product_cards(product_ids: list[str], limit: int = MAX_CARDS) -> list[ProductCard]:
    """Build cards from the database; ids the model invented are silently dropped."""
    cards: list[ProductCard] = []
    for pid in dict.fromkeys(product_ids):  # de-duplicate, keep order
        p = db.get_product(pid)
        if p is None:
            continue
        cards.append(ProductCard(
            product_id=p["product_id"], name=p["name"], category=p["category"], price=p["price"],
            image_url=p["image_url"], short_description=short_info(p["description"]), colors=p["colors"],
            sizes_in_stock=[s["size"] for s in p["inventory"] if s["quantity"] > 0],
            total_stock=p["total_stock"],
            stock=[SizeStatus(size=s["size"], quantity=s["quantity"], status=stock_status(s["quantity"]))
                   for s in p["inventory"]],
        ))
        if len(cards) == limit:
            break
    return cards


def page_results(search: PageSearch | None) -> PageResults | None:
    """Agent's PageSearch -> the PageResults the website renders. Cards come from the database."""
    if search is None:
        return None
    cards = product_cards(search.product_ids, limit=MAX_PAGE_CARDS)
    if not cards:
        return None
    return PageResults(title=search.title, total_matches=max(search.total_matches, len(cards)),
                       category=search.category, products=cards)


async def run_agent(message: str, memory: list[ModelMessage], deps: ShopDeps, source: str = "website"):
    """Run the agent loop step by step and append every step to output/audit_trail.json.

    Records: the user message, each tool call (name, short args, short result) as it happens, and
    how the loop ended (stop reason, model, requests, tokens, duration). Failures are recorded too.
    """
    run_id = uuid.uuid4().hex[:12]
    started = time.perf_counter()
    who = f"user#{deps.customer.user_id}" if deps.customer else "guest"
    where = deps.page.path if deps.page else None
    entries = [{"time": audit.now(), "run_id": run_id, "source": source, "event": "user_message",
                "customer": who, "page": where, "message": audit.short(message, 160)}]
    pending: dict[str, dict] = {}
    try:
        async with agent.iter(message, message_history=memory, deps=deps,
                              usage_limits=UsageLimits(request_limit=MAX_AGENT_REQUESTS)) as run:
            async for node in run:
                if Agent.is_call_tools_node(node):
                    for part in node.model_response.parts:
                        if part.part_kind == "tool-call" and part.tool_name != "final_result":
                            entry = {"time": audit.now(), "run_id": run_id, "event": "tool_call",
                                     "tool": part.tool_name, "args": audit.short(part.args_as_dict()),
                                     "result": None}
                            pending[part.tool_call_id] = entry
                            entries.append(entry)
                elif Agent.is_model_request_node(node):
                    for part in node.request.parts:
                        if part.part_kind == "tool-return" and part.tool_call_id in pending:
                            pending[part.tool_call_id]["result"] = audit.short(str(part.content))
                        elif part.part_kind == "retry-prompt" and part.tool_call_id in pending:
                            pending[part.tool_call_id]["result"] = "RETRY: " + audit.short(str(part.content), 120)
        result = run.result
        out: ShopReply = result.output
        usage = result.usage() if callable(result.usage) else result.usage
        entries.append({
            "time": audit.now(), "run_id": run_id, "event": "end",
            "stop_reason": "final_result: agent returned a validated ShopReply",
            "model": result.response.model_name, "model_requests": usage.requests,
            "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "output": audit.short({"reply": out.reply, "product_ids": out.product_ids,
                                   "page_results": bool(out.page_results), "focus_size": out.focus_size}),
        })
        return result
    except Exception as exc:
        reason = (f"usage limit: more than {MAX_AGENT_REQUESTS} model requests"
                  if type(exc).__name__ == "UsageLimitExceeded" else f"error: {type(exc).__name__}: {exc}")
        entries.append({"time": audit.now(), "run_id": run_id, "event": "error",
                        "stop_reason": audit.short(reason),
                        "duration_ms": round((time.perf_counter() - started) * 1000)})
        raise
    finally:
        audit.append(entries)


async def chat(message: str, history: list[ChatTurn] | None = None, user: dict | None = None,
               page: PageContext | None = None, visitor_id: str | None = None) -> ChatResponse:
    """One chat turn: run the agent and turn its ShopReply into the website's ChatResponse.

    Memory: a logged-in shopper's history comes from the database (chat_messages), so it survives
    reloads, new tabs and other devices; a guest's history is whatever the website sends.
    """
    deps = build_deps(user, page, visitor_id)
    memory = saved_history(deps.customer.user_id) if deps.customer else to_message_history(history or [])
    result = await run_agent(message, memory, deps, source="website")
    out: ShopReply = result.output
    page = page_results(out.page_results)
    chat_ids = out.product_ids or (out.page_results.product_ids if page else [])
    return ChatResponse(
        reply=out.reply,
        products=product_cards(chat_ids, limit=CHAT_CARDS_WITH_PAGE if page else MAX_CARDS),
        page_results=page,
        focus_size=out.focus_size,
        suggestions=out.suggestions[:3],
        checked=tools_used(result.new_messages()),
    )


def tools_used(messages: list[ModelMessage]) -> list[str]:
    """Badges for the database lookups the agent actually ran this turn (shown under the reply)."""
    called = {part.tool_name for m in messages for part in m.parts if part.part_kind == "tool-call"}
    return [badge for tool, badge in TOOL_BADGES.items() if tool in called]


async def _trace(question: str) -> None:
    """CLI helper: print every tool call and result, then the final reply."""
    result = await agent.run(question, deps=ShopDeps(), usage_limits=UsageLimits(request_limit=MAX_AGENT_REQUESTS))
    for msg in result.all_messages():
        for part in msg.parts:
            if part.part_kind == "tool-call":
                print(f"-> {part.tool_name}({part.args_as_dict()})")
            elif part.part_kind == "tool-return":
                print(f"<- {str(part.content)[:300]}")
    print(f"\nmodel: {result.response.model_name}\n")
    print(json.dumps(result.output.model_dump(), indent=2))


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--trace":
        asyncio.run(_trace(" ".join(args[1:]) or "What hoodies do you have?"))
    else:
        response = asyncio.run(chat(" ".join(args) or "What hoodies do you have?"))
        print(json.dumps(response.model_dump(), indent=2))
