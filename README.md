# Campus Customs: Store and Handsome Dan Shopping Agent (HW4)

A customer website for **Campus Customs** (officially licensed Yale apparel). Shoppers can:
- browse products and open a product page for each item;
- create an account and log in;
- chat with **Handsome Dan**, a PydanticAI agent that answers price and stock questions from the store's SQLite database and puts matching items on the page;
- add items to a cart and check out as a guest or member, then track the order.

| | |
|---|---|
| **Frontend** | React + Vite + TypeScript (`frontend/`) |
| **Backend** | Python FastAPI (`backend/main.py`), run with `uvicorn main:app --reload` |
| **Agent** | 4 files in `backend/`: `prompts/prompt.md` (system prompt), `agent.py` (wiring), `tools.py` (database tools), `models.py` (Pydantic types) |
| **AI** | OpenAI models through Portkey: `gpt-5.6-terra`, falling back to `gpt-5.6-luna` |

**Docs:**
- [`output/harness.md`](output/harness.md): how the whole system works (model fields, tools, safety rules, specs).
- [`AI_prompts.md`](AI_prompts.md): log of every prompt used to build this.
- [`output/usability.md`](output/usability.md), [`output/design.md`](output/design.md), [`output/app_check.html`](output/app_check.html) (open by double-click).
- [`output/audit_trail.json`](output/audit_trail.json): append-only agent activity log.

---

## Repository layout

```
hw4/
├── AI_prompts.md
├── requirements.txt          # Python dependencies (backend)
├── .env.example              # placeholders only: copy to .env
├── .gitignore
├── README.md
├── frontend/                 # Vite React TypeScript app
├── backend/
│   ├── main.py               # FastAPI app: run with  uvicorn main:app --reload
│   ├── agent.py              # ┐
│   ├── models.py             # │ the agent
│   ├── tools.py              # │
│   ├── prompts/prompt.md     # ┘
│   ├── auth.py db.py shop.py audit.py   # supporting modules (accounts, data access, shop, audit trail)
├── scripts/                  # data profile + automated checks
└── output/
    ├── harness.md  design.md  usability.md
    ├── app_check.html
    ├── app_check_images/     # screenshots linked from app_check.html
    └── audit_trail.json
```

## 1. Place the data pack (not in git)

The database and product photos are **not** in this repository: they're excluded by `.gitignore`. Copy the course data pack into a `data/` folder at the repo root, so that it looks like this:

```
hw4/
└── data/
    ├── campus_customs.db     # catalogue, inventory, users (+ chat_messages)
    └── products/             # product images referenced by catalogue.image_file_path
```

On first start the backend adds its own tables to this database (`orders`, `order_items`, `product_views`, `purchase_list`, `inventory_checks`). The original tables aren't changed.

## 2. One-time setup

You'll need **Python 3.11+** and **Node.js 18+** (developed with Python 3.14 and Node 24).

```powershell
# from the hw4 folder
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

cd frontend
npm install
cd ..

copy .env.example .env
```

Then edit **`.env`**:
- `PORTKEY_API_KEY`: your Portkey key. It can also come from your system environment.
- `SESSION_SECRET` and `STAFF_KEY`: any long random strings. To generate one, run `python -c "import secrets;print(secrets.token_hex(32))"`.

On macOS or Linux, use `source .venv/bin/activate`, `pip install -r requirements.txt` and `cp .env.example .env` instead.

> **OneDrive or Dropbox users:** pause syncing while creating `.venv` and running `npm install`.
>
> **Windows:** clone into a short path (e.g. `C:\code\hw4`). Very deep folders can hit the 260-character path limit during `pip install`.

## 3. Run the backend (terminal 1)

```powershell
cd backend
..\.venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

When it starts, it:
- creates any missing shop tables;
- runs an inventory audit;
- schedules the audit to run again every hour;
- serves the API at http://localhost:8000.

To check it's running, open http://localhost:8000/api/health.

## 4. Run the frontend (terminal 2)

```powershell
cd frontend
npm run dev
```

Open **http://localhost:5173**. Vite forwards `/api` and `/media` requests to the backend on port 8000, so both must be running.

**Try these:**
- Click a product, pick a size, then **Add to cart** (watch the bubble).
- Open the 🛒 cart, check out **as a guest** (name, email, phone and a payment method), then use **Track order**.
- Open the chat (bottom right) and ask "how many Basic Hoodie Big Yale are left in XS?" or "what hoodies are available?".
- Click the Handsome Dan logo to hear him bark. 🔊 mutes the sounds.

**To stop:** press Ctrl+C in both terminals. If port 8000 stays busy (Windows):
1. Run `netstat -ano | findstr :8000` to find the process id.
2. Run `taskkill /PID <pid> /T /F`.

## 5. Checks (optional)

With the backend running, and `SEED_TEST_EMAIL` / `SEED_TEST_PASSWORD` set in `.env`:

```powershell
.venv\Scripts\python scripts\check_auth.py      # 16 account/password checks
.venv\Scripts\python scripts\check_shop.py      # 24 cart/checkout/safety/tracking/restock/audit checks (cleans up after itself)
.venv\Scripts\python scripts\check_agent.py     # 22 agent scenarios with real AI calls -> output/p5_agent_checks.json
.venv\Scripts\python scripts\export_purchase_list.py   # restock list -> output/purchase_list.csv
cd backend; ..\.venv\Scripts\python agent.py --trace "do you have a navy hoodie in M?"   # watch one turn's tool calls
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Server status and the models the agent uses |
| GET | `/api/categories` | Categories with counts, price ranges and a sample image |
| GET | `/api/products?category=&q=&ids=` | List products (category filter, keyword search, or specific ids) |
| GET | `/api/products/{product_id}` | One product, with stock for each size |
| GET | `/media/products/{file}` | Product images (served from `data/products/`) |
| POST | `/api/auth/register` · `/api/auth/login` | Create an account or log in (PBKDF2-SHA256 passwords) and return a session token |
| GET | `/api/auth/me` | The current user, from `Authorization: Bearer <token>` |
| POST | `/api/chat` | Message Handsome Dan. Returns a reply, product cards, suggestions and `page_results` (cards for the page). Members' chats are saved |
| GET | `/api/chat/history` | A logged-in shopper's saved conversation |
| POST | `/api/cart/quote` | Re-price a cart from the database |
| POST | `/api/orders` | Checkout (guest or member). A payment method is **required**; guests give name, email and phone. Returns a unique transaction number |
| GET | `/api/orders/track?order_number=&contact=` | Track an order with its number plus the email or phone used |
| GET | `/api/payment-methods` | Card/cash at pickup, or card/cash on delivery |
| POST | `/api/events/view` · GET `/api/recommendations` | Click history and "Picked for you" |
| GET | `/api/staff/purchase-list` · `/api/staff/inventory-checks` | Restock list and hourly inventory audits (`X-Staff-Key` header) |

## Security notes

- **Not committed:** `.env` (secrets) and `data/` (database and images). Both are in `.gitignore`. `.env.example` holds placeholders only.
- **Passwords:** stored only as salted PBKDF2-SHA256 hashes.
- **Payments:** the site never collects card numbers. Payment happens at pickup or on delivery.
- **Audit trail privacy:** the agent's audit trail logs shoppers as `guest` or `user#id`, never by email.
