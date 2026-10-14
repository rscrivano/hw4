# AI Prompts Log — Homework 4: Campus Customs

This is a running log of the prompts I typed into the vibe coder (Claude Code) for this assignment. Each prompt is copied word for word, in the order I sent it, with a short note on what the AI did in response. Evidence (the running site, database writes and screenshots) is listed in each section.

**Tool:** Claude Code (desktop app, Code tab)
**Project folder:** `Homework/Homework 4`

---

## Problem 1: Vibe coder prompts (project setup and logging)

### Prompt 1.1: Project kickoff (my words)

> This is now focused on the homework 4 folder for this file path. Here is the file path: C:\Users\ryans\OneDrive - Yale University\Courses\Mgmt 409 AI\Homework\Homework 4
>
> The data folder is in that folder location too. I need all this content created here focused on this folder and keep a trail of our conversation here in the folder path so the professor can understand our approach on this project. This should be created under AI_prompts.md at the start of the assignment and updated as I go so it keeps a log of what i type in on the vibe coder.
>
> The concept here is the following: Campus Customs needs a real customer website iwth a helpful effective chatbot. I need to build a React + Vite TypeScript front end and a Python FastAPI backend whose brain is a PydanticAI agent. Shoppers need to be able to browse products, create an account, chat about the merchandise, see matching items appear on the page and get honest answers about the price and stock from a local databasse.
>
> I am provided with the campus_customs.db with tables for the product catalogue, inventory by size, and users (with hashed passwords). Product image file paths are located in the catalogue table. The website yalebulldogblue.com is meant to help you understand the style of campus customs page and information for you to understand. I have already reveiwed the layout of the site so I am aware how we best create this final output. Use my PORT_API_KEY that is already integrated into this account for my agent's AI calls. I will be using the OpenAI through Portkey so for the harder agent steps, I need to use a smarter model. At the end of this product, I will be pushing the project to a public GitHub repo and submit the repo URL on Canvas (the last problem shows the file tree here). Make sure you don't commit the database or product images.
>
> In the zip folder, make sure you have data/campus_customs.db - SQLite database with the tables catalogue, inventory, and users (one test user is already there); also the data/products/ - product images; paths match the catalogue table
>
> Problem 1: Vibe coder prompts:
>
> Each section shoudl be separated out for each problem and each section should include: the problem number and title, at least one prompt I type in my own words which I will do as much as I can, and a follow-up prompt if needed.
>
> My running site, database writes, screenshots are evidence

**What the AI did:**
- Created this file (`AI_prompts.md`) as the prompt log, with one section per problem.
- Checked the `data/` folder: `campus_customs.db` and `data/products/` (102 `.jpg` images) are both present.
- Added `.gitignore` so `data/`, `*.db`, `.env`, `.venv/` and `node_modules/` are never committed to the public repo.
- Noted the build plan: React + Vite + TypeScript frontend, FastAPI + PydanticAI backend, AI calls through Portkey using `PORTKEY_API_KEY` from `.env`, the model set by `OPENAI_MODEL`, and a stronger model for the harder agent steps.

### Follow-up prompts

_(added as I go)_

---

## Problem 2: Analyze the database

### Prompt 2.1: Review the tables (my words)

> Problem 2: analyze the database
>
> Review the data/campus_customs.db and undertand the fields of each table. I need you to understand the catalogue, inventory, and users. I need to visually see it too after you review it. Then i need to start the file output/harness.md. I will need to see this so i can write doewn each table and its fields along with one short line on why each field matters for the shop or that chatbot specficially

**What the AI did:**
- Opened the database **read-only** and profiled every table. Found **4 data tables**: `catalogue` (102 rows), `inventory` (612 rows = 102 products × 6 sizes), `users` (3 rows), and an extra `chat_messages` table (22 rows).
- Wrote `scripts/analyze_db.py`, which generates **`output/database_overview.html`**. This is a black-and-pink visual page with stat tiles, bar charts (garment types, prices, colors, stock by size, sold-out sizes), schema tables and a product image gallery.
- Started **`output/harness.md`**, listing each table and field with one line on why it matters for the shop or chatbot, plus the data facts the agent must respect.
- Main findings:
  - Stock is tracked per size. 24% of size rows are at 0, but no product is completely sold out.
  - `garment_type` has 22 inconsistent spellings.
  - `colors` and `search_tags` are stored as JSON strings.
  - Price is set by category ($32 to $98).
  - Passwords are stored as `pbkdf2_sha256$salt$hash`.

**Evidence:** `output/database_overview.html`, `output/harness.md`

### Follow-up prompts

#### Prompt 2.2

> I still can't visually see it

**What the AI did:** Opened `output/database_overview.html` directly in my default web browser so the full page and the product photos display.

---

## Problem 3: Build the Campus Customs website

### Prompt 3.1: Scaffold the site (my words)

> Problem 3: Build the Campus Customs website
>
> Alright now i need you to scaffold a React + Vite + TypeScript front end for the Campus Customs section and put a Nav Bar at teh top that links it to the main pages:
>
> 1. Home
> 2. Products
> 3. About Us
> 4. Log in
> 5. Create account
>
> Pull the campus customs style wording from yalebulldogblue.com for the Home and About us. The About Us page should say We  are not just a campus store, but rather a store that is vibrant and multi-cultured that gathers designs integrated from cultures globally. With Yale being a multi national institution with students from across the globe, we want to ensure our branding and store merchandise collectviely enables designs from a diverse background of cultures and appeals to our students and families along with alumni. The Home Page should say the key type of merchandise categories that are available to purchase
>
> On the Products page, show the product images from the catalogue (use the image paths in the database) with the basic product info (name, price, and a short description).
>
> Make each product open a signle-item page (large image on one side, full product text on the other - description, price, sizes/stock when I have them). Clicking on a card on the products should automatically take the shopper there to that section. Then add a chat interface on the bottom right of the site. It doesn't need to talk to an agent yet, a stub that will call my backend later is enough for now.
>
> I need a small API soon to read the database. It's fine to start a simple FastAPI app in teh backend/main.py just to serve the products and images and then grow it into the agent backend in problem 5 coming up.

**What the AI did:**
- Read yalebulldogblue.com to pick up the store's tone and layout. That meant the upbeat, school-spirited headings ("Big Spirit, Big Yale", "Bulldog pride"), the "officially licensed" message and the 57 Broadway address. It wrote original copy in that style rather than copying the site's text.
- **Backend:** `backend/main.py` (FastAPI) and `backend/db.py`.
  - Endpoints: `/api/categories`, `/api/products` (category filter and search), `/api/products/{id}` (stock for each size), `/media/products/*` (the images) and a **stub** `/api/chat` that does simple keyword matching until the agent is built in Problem 5.
  - The 22 messy `garment_type` values are mapped onto 7 clean categories in one place (`db.category_for`).
- **Frontend:** `frontend/`, built with React + Vite + TypeScript and React Router.
  - **Nav bar:** Home, Products, About Us, Log in, Create account. It collapses into a menu button on phones.
  - **Home:** the hero banner, a "Shop by category" grid (T-Shirts $32, Crewnecks, Hoodies, Quarter-Zips $72, Full-Zip Hoodies $88, Jackets & Fleece $98, Performance Long Sleeves $45) and featured products.
  - **About Us:** my multicultural, global-design statement (lightly copy-edited), plus three short value cards and the store address.
  - **Products:** every catalogue image with its name, price and a short description, plus category filter chips and a search box. Clicking a card goes to that product's page.
  - **Product page:** a large image on the left. On the right are the name, price, full description, colors, a stock grid by size (sold-out sizes crossed out, "Only N left" when stock is low) and the tags.
  - **Chat widget:** a pink button in the bottom-right corner. It opens a panel that posts to `/api/chat` and shows any matching products as clickable cards.
  - **Log in / Create account:** finished forms with validation. Submitting shows a "coming soon" notice until account endpoints are added to the backend.
- Added `README.md` with run steps and `.env.example` (variable names only).
- **Verified:**
  - The TypeScript check and the production build pass.
  - The API returns all 102 products across 7 categories.
  - The Ice Hockey Left Chest Hoodie page shows XS 20, S 8, M/L/XL sold out and XXL 25, which matches the `inventory` table.
  - The chat stub returned crewnecks for "do you have a gray bulldog crewneck?".
  - Fixed a React crash in the scroll-to-top helper that showed up during testing.

**Evidence:** `output/screenshots/p3_home.jpg`, `p3_products_hoodies.jpg`, `p3_product_detail_stock.jpg`, `p3_chat_stub.jpg`, `p3_about.jpg`

### Follow-up prompts

#### Prompt 3.2: Viewing the site

> I want to review the latest site setup, whats the link to correctly view this

**What the AI did:** Restarted both servers, which had stopped overnight, and opened http://localhost:5173 in my browser.

#### Prompt 3.3: Lighter, more vibrant look with Handsome Dan

> is there a way for you to make the background a lighter/white color (not just plain white) and include handsome dan in it and other vibrant colors that will be more appealing to the shopper?

**What the AI did:** 
- **Light, vibrant theme** (`frontend/src/styles.css` rewritten). This replaces the default black-and-pink style at my request.
  - **Background:** warm cream (`#fff8f1`) instead of plain white, with soft pink, blue, yellow and teal glows and a faint dot pattern.
  - **Colors:** Yale blue for headings and the nav, hot pink for buttons and prices, and sunshine yellow, teal, violet and coral accents.
  - **Rainbow stripes** under the nav bar and above the footer, and the footer itself is Yale blue.
  - **Category cards** each get their own accent color, and the color and tag chips are colorful too.
- **Handsome Dan** (`frontend/src/components/HandsomeDan.tsx`): an *original* cartoon bulldog in a Yale-blue "Y" sweater, drawn as code (SVG). No real photos of the mascot were copied from the web. He appears in:
  - the nav logo;
  - the home page banner, where he bobs gently (turned off for people who prefer reduced motion) beside a "Woof! Boola Boola!" speech bubble and colorful confetti;
  - the "Need a hand?" banner;
  - the chat button ("Ask Handsome Dan") and chat header, where the assistant now greets shoppers as Dan;
  - the About Us page, the Log in and Create account cards, and the footer.
- **Product photos:** 73 of the 102 catalogue images have black backgrounds, which looked patchy on a light page. Product images now show as full-bleed photo tiles that zoom slightly on hover, so black-background and white-background photos both look deliberate. The image files themselves were not edited.
- **Verified:**
  - The TypeScript check passes and the browser console shows no errors.
  - Checked the phone layout and the desktop layout, where the hero is two columns with Dan on the right.
  - Checked the chat ("bulldog hoodie" returns bulldog hoodies) and the About page.

**Evidence:** `output/screenshots/p3b_light_home.jpg`, `p3b_handsome_dan_hero.jpg`, `p3b_light_products.jpg`, `p3b_light_product_detail.jpg`, `p3b_dan_chat.jpg`, `p3b_light_about.jpg`

#### Prompt 3.4

> show me the site now

**What the AI did:** Checked that both servers were running, then opened http://localhost:5173 in my browser and in the browser pane.

---

## Problem 4: Create account and login

### Prompt 4.1: Account flow (my words)

> Problem 4: Create account and login
>
> Now build a normal create account /login flow.
>
> Create teh account by setting up the first name, last name, email address, password, and the confirmation of the password. Log in: email and password
>
> New accounts will go into the users table. And make sure to store passwords securely so that hackers (human or AI) can't access them at all.
>
> The seed database has a test user that can be used while building it:
>
> 1. email: test@campuscustoms.yale.edu
> 2. password: password

_(I interrupted the AI here to add the hashing details.)_

### Prompt 4.2: Follow-up with the hashing rules (my words)

> Hang on, I am not done with problem 4 yet.
>
> Hash function: PBKDF2-HMAC-SHA256, 120,000 iterations (stored as pbkdf2_sha256@salt@hash)
>
> How login checks a password:
>
> 1. You never un-hash the stored value so that it is protected. You instead re-hash what the user typed and compared
> 2. Read the salt out of the stored string (middle piece) - don't make a new one at the login
> 3. Hash the typed password with the same salt, then compare to the stored hash. Use a constant-time compare
> 4. Signup and login must use the same has settings (same function, same salt handling, same iteration count). If they differ, even the correct password won't match
> 5. Surest check: log in as the seeded test user and as a brand-new account that I just created in my own app here.
>
> Confirm that I can log in as that user and that a brand-new account I created also works.
>
> Lastly, update the output/harness.md with how the auth works (what I store here for a user and how passwords are protected)

**What the AI did:**
- **Checked the hashing scheme first.** It re-hashed the seed user's password with PBKDF2-SHA256, 120,000 iterations and the stored salt read as text, and got the stored hash exactly.
  - It also found that the database separates the parts with `$` (`pbkdf2_sha256$salt$hash`), not `@` as I wrote, so the app follows the database.
- **Backend (`backend/auth.py`):**
  - `hash_password()` runs at signup and makes a new random salt. `verify_password()` runs at login, reads the salt from the stored string, re-hashes what was typed and compares with `hmac.compare_digest`. Both use one shared `_pbkdf2()` helper, so the settings can't drift apart.
  - Signup checks the name, email format, a password of at least 8 characters, a matching confirmation and that the email isn't already used.
  - New accounts go into `users` with the email lowercased.
  - Failed logins always say "Incorrect email or password." and take the same time whether or not the email exists.
  - API responses never include the password hash.
- **Sessions:** a signed token (HMAC with `SESSION_SECRET` from `.env`) that lasts 7 days. The endpoints are `POST /api/auth/register`, `POST /api/auth/login` and `GET /api/auth/me`.
- **Frontend:**
  - The Create account and Log in pages now talk to the backend and show clear errors.
  - Login state is shared across the app (`frontend/src/auth.tsx`).
  - The nav bar shows "Hi, First name" and a Log out button.
  - Logins survive a page reload.
- **Verified:**
  - `scripts/check_auth.py` passes **16/16** checks (`output/p4_auth_check_results.txt`).
  - In the browser:
    - The seed test user logged in.
    - A mismatched confirmation was caught.
    - A brand-new account (**Handsome Dan**, `users` row 5) was created through the form, logged out, rejected with a wrong password, then logged back in with the right one.
  - The demo account's login is saved in the git-ignored `.env` (`DEMO_EMAIL` / `DEMO_PASSWORD`).
- Updated `output/harness.md` Section 3 with what is stored for each user and how passwords are protected.

**Evidence:** `output/screenshots/p4_seed_user_logged_in.jpg`, `p4_signup_password_mismatch.jpg`, `p4_new_account_created.jpg`, `p4_wrong_password_rejected.jpg`, `p4_new_account_logged_back_in.jpg`, `output/p4_auth_check_results.txt`, and the new row in the `users` table.

### Follow-up prompts

_(added as I go)_

---

## Problem 5: Shop chatbot (PydanticAI agent behind FastAPI)

### Prompt 5.1: Build the agent (my words)

> Now I want you to build the shop chatbot as a PydanticAI agent behind FastAPI, plugged into the front-end chat widget that we began building out already. Put the API app in backend/main.py - which is the file that I already had you run with Uvicorn earlier. Keep the agent as these four file s next to it just like we did conceptually in homework assignment number 3 from earlier.
>
> * backend/prompts/prompt.md - system prompt (we will be expanding upon this file later)
> * backend/agent.py - agent entry / wiring
> * backend/tools.py - tools the agent can call
> * backend/models.py - Pydantic / PydanticAI structured types
>
> In the main.py, expose a chat route for the purpose of a message from the website returning a reply from the agent (and anything else that would be rational for products/authorization). This part of the project here will need my AI model API key for the agent

_(I interrupted the AI here to add more requirements.)_

### Prompt 5.2: Follow-up requirements (my words)

> Hang on, that and this still will be for Problem 5: PydanticAI agent backend
>
> Additionally, put the Campus Customs voice and safety basics into prompts/prompt.md (I will expand the tools and safety later on in this buildout). Update the types in models.py for the chat replies / product cards as necessary.
>
> In the output/harness.md, make sure that it notes how the front end communicates with the FastAPI and how the agent is loaded (prompt file + model).
>
> Ensure the backend runs from the backend/ folder like this: uvicorn main:app --reload --port 8000

**What the AI did:**
- **Followed Homework 3's layout.** It reused the PydanticAI and Portkey pattern (`OpenAIResponsesModel` through `https://api.portkey.ai/v1`) and kept the agent as four files in `backend/`:
  - `prompts/prompt.md`: Handsome Dan's voice, the "always use tools, never guess" rules and the safety basics.
  - `agent.py`: wiring. It loads the prompt, builds the model and exposes `chat()`. It also has a `--trace` command-line option that prints every tool call.
  - `tools.py`: four read-only database tools: `search_products`, `get_product_details`, `check_stock` and `list_categories`.
  - `models.py`: tool-result types, the agent's structured output `ShopReply` (`reply`, `product_ids`, `suggestions`), and the chat API types `ProductCard`, `ChatRequest`, `ChatResponse` and `ChatHistoryMessage`.
- **Picking the smarter model.** It tested which models Portkey actually serves and found that unknown names, even `gpt-5.6`, are silently sent to `gpt-5.6-luna`. Only `gpt-5.6-luna` and `gpt-5.6-terra` are real.
  - The agent runs on **gpt-5.6-terra** for the harder tool-calling steps and falls back automatically to **gpt-5.6-luna**.
  - Both names are set in `.env` (`OPENAI_SMART_MODEL`, `OPENAI_MODEL`).
  - My `PORTKEY_API_KEY` comes from my Windows environment and is never printed or committed.
- **`main.py` routes:**
  - `POST /api/chat` runs the agent. Guests can chat; logged-in shoppers' chats are saved to the `chat_messages` table.
  - `GET /api/chat/history` lets a logged-in shopper's conversation come back after a reload.
  - `GET /api/products?ids=` shows the chat's picks on the page.
  - A failed AI call returns a friendly 503 error.
- **Runs from `backend/`:** switched the imports to sibling modules, so `uvicorn main:app --reload --port 8000` works from `backend/`. Tested that exact command.
- **Chat widget:**
  - sends the login token and the conversation history;
  - shows Dan's replies with bold text and bullet lists;
  - shows product cards with the sizes in stock;
  - adds tappable follow-up suggestions, a "Dan is checking the shelves…" typing indicator and a "New chat" button;
  - adds **"Show these on the page →"**, which filters the Products page to "Handsome Dan's picks".
- **Bugs found by testing and fixed in code, not just the prompt:**
  1. **Size filter.** Searching with `size=M` silently hid the Ice Hockey Left Chest Hoodie (sold out in M), so the agent said "yes" about a different hoodie. The size filter now runs last and lists what it excluded, so the agent says "sold out in M" and offers alternatives.
  2. **Colors.** A "navy crewneck" search returned a light gray crewneck with navy lettering. The garment color (the first entry in `colors`) is now matched first.
  3. **Ranking.** Products whose name matches the search words now rank first.
- **Verified:**
  - `scripts/check_agent.py` passes **7/7** real-AI scenarios (`output/p5_agent_checks.json`): sold-out honesty, cheapest item, a color we don't carry, a filtered search, a multi-turn follow-up, a prompt-injection or fake-discount attempt, and an off-topic request.
  - It automatically checks that every quoted price is real and every card is a real product. Two early "failures" were mistakes in the test itself (a curly apostrophe, and a budget the shopper typed being repeated back), and were fixed in the test.
  - `scripts/check_auth.py` still passes 16/16, and the production build passes.
  - **In the browser** (logged in as the demo account):
    - Asked "I need a navy hoodie for my brother, he wears XL" and got 5 navy hoodies, all with XL in stock.
    - "Show these on the page" worked.
    - The chat was saved to `chat_messages` (rows 23–24) and came back after a reload with "welcome back, Handsome!".
- **Updated `output/harness.md`:**
  - Section 4: how the frontend talks to FastAPI (a diagram, the Vite proxy, tokens, history, errors and the route table).
  - Section 5: how the agent is loaded (the prompt file, the terra and luna fallback through Portkey, tools, output type and limits).
  - Section 6: the system prompt summary and test results.
- Updated `README.md` with the new run command and the check scripts.

**Evidence:** `output/screenshots/p5_chat_welcome_suggestions.jpg`, `p5_chat_thinking.jpg`, `p5_agent_navy_xl_hoodies.jpg`, `p5_dans_picks_on_page.jpg`, `p5_chat_history_restored.jpg`, `output/p5_agent_checks.json`, and the new rows in `chat_messages`.

### Follow-up prompts

_(added as I go)_

---

## Problem 6: Tools for product info and stock

_(My first attempt was sent too early and cut off at "This includes:". I interrupted it and re-sent the full prompt below.)_

### Prompt 6.1: Product info and stock tools (my words)

> Problem 6: Tools: product info and stock
>
> Now I want to make sure the agent has tools for the purpose of looking up real information from teh campus_customs.db
>
> This includes:
>
> * Product description
> * Price
> * How many are in stock (by size when the customer asks)
>
> The agent must use the database - it should not invent prices or quantities. If a size is out of stock, it should say so clearly so the customer knows.
>
> I also need to expand the prompts/prompt.md so that the agent knows to call these tools for price and stock questions. Add or update the return types in models.py
>
> Lastly in the output/harness.md, please list each tool and explain which model fields I chose for the lookup results and why
>
> The tools should be practical, efficient for a customer to use, and easily visable for the customer

**What the AI did:**
- **Three dedicated lookup tools** in `backend/tools.py`, replacing Problem 5's all-in-one `get_product_details`. All of them read `campus_customs.db` live and are read-only:
  - `get_product_info(product_id)`: the **full description**, price, garment color and print colors, and the sizes in stock.
  - `get_prices(product_ids)`: **exact prices** for one or more items in **one call**, for comparisons and totals.
  - `check_stock(product_id, size=None)`: **stock for every size**, or one size with its quantity and a status of in stock, low stock (1–5) or sold out. It includes a code-built `summary` sentence such as "… is SOLD OUT in size M. Sizes in stock: XS, S, XXL."
  - `search_products` and `list_categories` are kept.
- **`models.py` return types:**
  - New: `ProductInfo`, `PriceQuote`, `PriceLookup`, `StockReport` and `SizeStatus`. The stock status comes from one shared rule (`stock_status()`, `LOW_STOCK_MAX = 5`).
  - `ShopReply.focus_size`: the size the shopper asked about.
  - `ProductCard.stock`: per-size stock for the cards.
  - `ChatResponse.checked`: which database lookups actually ran this turn.
- **Expanded `prompts/prompt.md`:**
  - a **"Which tool to call"** table that maps each kind of question to a tool;
  - **price rules**: quote exactly, never round or invent discounts, show the math for totals, and note that totals exclude tax;
  - **stock rules by size**: say "sold out" clearly and early and offer sizes that are in stock; say "only N left" for 1–5; give exact counts when asked; set `focus_size`.
- **Made it visible to the customer.** Every chat product card now shows:
  - **size chips**: green for in stock, amber with a count for low stock, gray and struck through for sold out;
  - **the asked-about size ringed**, with a colored status line such as "Size L: sold out" or "Size XL: only 2 left";
  - **✓ badges** under the reply (e.g. "Checked live stock", "Prices from our catalogue"), taken from the tool calls that actually ran.
- **Tests:**
  - Extended `scripts/check_agent.py` to **12 scenarios** (5 new for Problem 6), with expected values read from the database.
  - Added an automatic check that every "N left" in a reply matches a quantity a stock tool really returned.
  - Result: **12/12 pass**. The one early "failure" was the test rejecting a correct subtotal ($136.00), so the test was fixed, not the agent.
  - `check_auth.py` still passes 16/16, and the production build passes.
- **In the browser:**
  - "Ice Hockey Left Chest Hoodie in L? How much?" → "Sorry… **sold out in L**. It's **$68.00**", with a red "Size L: sold out" line on the card.
  - "How many Basic Hoodie Big Yale left in XL?" → "only **2 left in XL**", with an amber chip.
  - Both match the database (L=0, XL=2).
- **Updated `output/harness.md`.** The new Section 7 lists each tool and explains **which model fields were chosen for the lookup results and why**. Sections 5 and 6 were updated to match.

**Evidence:** `output/screenshots/p6_sold_out_reply_badges.jpg`, `p6_sold_out_size_chips.jpg`, `p6_low_stock_exact_count.jpg`, and `output/p5_agent_checks.json` (12 scenarios with tool calls and replies).

### Follow-up prompts

_(added as I go)_

---

## Problem 7: Chat search that updates the page

### Prompt 7.1: Dynamic product cards from chat (my words)

> Problem 7: Chat search that updates the page
>
> Now I need to add a cool feature to the site which is when a customer asks about a type of item, like "what hoodies are available", I need the agent to search the catalogue and the website needs to dynamically show the matching items as product cards (including the: image, name, price, short info). This is an API contract: the agent returns structured product matches and then the front end renders them on the website so it looks appealing to the end user.
>
> After the dynamic product cards are loaded by the new feature, ensure the same single-item page behavior that I build in problem 3 earlier is still working properly: each product card, including the ones the chat just put into the page should still open that detail view (large image + the full information) when its clicked int.
>
> Update the prompts/prompt.md and output/harness.md so it is clear how the search results reach the page

**What the AI did:**
- **Defined the API contract** (`backend/models.py`):
  - The agent's structured output now has **`page_results: PageSearch`**: a title, all matching `product_ids`, `total_matches` and the category.
  - The backend turns that into **`ChatResponse.page_results: PageResults`**, with full `ProductCard`s (image, name, price and a new `short_description`) built **from the database**. Made-up ids are dropped.
  - `null` means "leave the page alone".
- **Updated the agent** (`agent.py`, `tools.py`): `page_results()` builds up to 12 cards; the chat bubble keeps just the top 3 picks; `search_products` now returns up to 12 results.
- **Frontend:**
  - `pageResults.tsx`: shared React context, saved to sessionStorage.
  - `ChatResults.tsx`: renders "**Handsome Dan found — Hoodies** · Showing 12 of 25" at the top of **any** page, with **See all** and **Clear** buttons and pop-in card animations.
  - The chat bubble gets a **"12 hoodies are on the page · View"** button that closes the chat and scrolls to the results.
- **Kept the Problem 3 detail page working.**
  - Made the one `ProductCard` component accept both catalogue products and chat cards, so the chat's cards are the same cards as the Products page and link to `/products/:id`.
  - On a detail page the results shrink to a slim **"Dan's results: Hoodies (12) · Show"** bar, so the large image stays in view.
- **Bugs found by testing and fixed:**
  1. **Wrong price range.** The first reply said "pullover styles start at $68.00" because the agent saw only 12 of the 25 hoodies (two cost $45). `search_products` now returns `min_price` and `max_price` across **all** matches, and the prompt says to use them, so it now says "25 hoodies, from $45.00–$68.00".
  2. **Mismatched count.** The category "Hoodies" also matched full-zip hoodies (27 vs the site's 25). Exact category names now match exactly.
  3. **Header price range.** It only reflected the shown cards, so it was removed.
- **Updated `prompts/prompt.md`.** The new "**Showing products: in the chat, and on the page**" section explains when to fill `page_results` (browsing a type of item), when to leave it null (single-item questions, no matches, off-topic), and to use `total_matches`, `min_price` and `max_price`.
- **Updated `output/harness.md`.** The new **Section 8** has a step-by-step flow diagram of how search results reach the page, both JSON contracts with real examples, a design-decisions table, and the verification. The Section 4 diagram was updated too.
- **Verified:**
  - `scripts/check_agent.py` passes **15/15**. New checks: a browse question fills `page_results` with all 25 real hoodies; navy crewnecks match the garment color; a single-item question leaves the page alone.
  - Auth passes 16/16, and the production build passes.
  - **In the browser:** chat → 12 hoodie cards on the page → clicked a chat card → the Crew Left Chest Hoodie detail page (M sold out, XXL "Only 5 left", matching the database) → Show strip → a second product's detail page ($45.00 UA Gameday hood).

**Evidence:** `output/screenshots/p7_chat_reply_on_page_button.jpg`, `p7_results_on_page.jpg`, `p7_detail_from_chat_card_strip.jpg`, `p7_detail_page_slim_bar.jpg`, `p7_second_detail_from_strip.jpg`, `p7_desktop_results_grid.jpg`, and `output/p5_agent_checks.json`.

### Follow-up prompts

_(added as I go)_

---

## Problem 8: Customer memory

### Prompt 8.1: Remember the shopper and the page they're on (my words)

> Problem 8: Customer memory
>
> When the shopper is logged in, make sure to save their chat history in the database in an appropriate table and reload it when they return to the site. I need the agent to know who is chatting (their name and email) which should be put in the agent deps (or an equivalent clear pattern) and/or tools the agent can call.
>
> Make sure to also pass enough page context that if someone is on a product page and asks if they have an item in a certain color, the agent is able to interpret which item the user is referring to. Code can be put into the agent context for this purpose if that is helpful.
>
> Gusts are still able to chat, but the history only needs to persist for logged-in users. Be sure to document in the output/harness.md: how the user chat history gets stored, what customer fields the agent sees, and how the page context is passed

**What the AI did:**
- **Who is chatting goes in the agent deps.**
  - `ShopDeps` in `tools.py` now holds `customer: Customer(user_id, first_name, last_name, email, member_since)` and `page: PageView`.
  - `agent.build_deps()` loads the customer from the `users` table (never the password hash).
  - A dynamic instruction, `shopper_context`, tells Dan the shopper's name, email and member-since date, or that they're a guest.
  - A new tool, **`get_customer_profile`**, returns the shopper's *own* account details and chat activity. It takes no arguments, because it reads from the deps.
- **Chat memory in the database.**
  - Logged-in chats are saved in the existing **`chat_messages`** table with `db.save_chat_turn()`: the shopper's row, then Dan's row with the ids of the products shown.
  - On every message, the **server** loads the shopper's last 12 messages from the database (`db.load_chat_history()` → `agent.saved_history()`) instead of trusting the browser's copy. Dan therefore remembers across reloads, visits and devices, and can still resolve "the tennis one you showed me".
  - When the shopper returns, the chat widget reloads the conversation with "welcome back".
  - Guests can still chat normally, and nothing is saved for them.
- **Page context.**
  - With each message, the chat widget sends `page: {path, product_id, category, results_title}`, and shows a **"👀 Viewing: Crew Left Chest Hoodie"** chip.
  - The server re-reads the viewed product from the catalogue (ignoring any unknown id).
  - A dynamic instruction, `page_context`, tells Dan which product "this" or "it" means, with its id, price and garment color.
  - New prompt rules cover "do you have this in [color]?": the item comes in one garment color, so say so, then offer real alternatives in the same category in that color.
- **Updated `prompts/prompt.md`** with the new section **"Who you're talking to, and what they're looking at"**, and added a `get_customer_profile` row to the tool table.
- **Verified:**
  - `scripts/check_agent.py` passes **20/20**. The 5 new scenarios cover: "this in gray?" on a product page; "is this in medium?" on a product page; "what email is my account under?" (logged in); "what was I shopping for last time?" (recalled from saved history); and the same email question as a guest (no details given).
  - Auth passes 16/16, and the production build passes.
- **In the browser:**
  - Logged in on the Crew Left Chest Hoodie page, "do you have this in gray?" → "This Crew Left Chest Hoodie only comes in navy blue. I found 9 gray hoodie alternatives…", saved as rows 31–32.
  - After a reload and pressing **New chat** (an empty window), "is the tennis one you showed me available in XXL?" → "only **2 left in XXL**", taken from the database memory. Saved as rows 33–34.
  - As a guest: a fresh chat, "how much is this one?" → "$68.00", and **no** new database rows.
- **Documented in `output/harness.md` Section 9:**
  - how chat history is stored and reloaded (the table, its columns and the flow);
  - which customer fields the agent sees, where, and why;
  - how page context is passed (browser → server → deps → instructions → prompt rules);
  - the verification results.

**Evidence:** `output/screenshots/p8_history_reloaded_viewing_chip.jpg`, `p8_this_in_gray_alternatives.jpg`, `p8_memory_after_reload_tennis_xxl.jpg`, `chat_messages` rows 31–34, and `output/p5_agent_checks.json`.

### Follow-up prompts

_(added as I go)_

#### Prompt 8.2

> show me the updated site product now

**What the AI did:** Checked that both servers were running, then opened http://localhost:5173 in my browser and in the browser pane.

---

## Problem 9: Usability improvements

### Prompt 9.1: Cart, guest checkout, click history and restocking (my words)

> Problem 9: Usability Improvements
>
> Now that the core shop works, I need to improve it. I want the front end to have an option to checkout as a guest and there should also be an ability to add any of the items to a cart that the user can see and click on the cart to check what they are ordering.
>
> The backend should be optimized so it ensures a data history of each of the items the user has clicked on and holds that memory so it can better advertise items in the future to that user. Additionally, the back-end should be able to track when an item is running low on stock and therefore add the proper re-stock quantity to the businesses inventory purchase list.
>
> Write output/usability.md before or as you build this out. For each improvement note what you added and why it is a helpful addition, which I just explained in my description.

**What the AI did:**
- **Wrote `output/usability.md` first** as a plan (4 improvements, each with "what" and "why"), then filled it in as each one was built and tested.
- **Shopping cart:**
  - **Add to cart** on product pages (size and quantity, limited to the stock available).
  - A **🛒 Cart icon with a live count badge**, always visible, including on phones.
  - A **Cart page** with quantity, remove and subtotal.
  - The server re-prices every cart from the database (`/api/cart/quote`) and marks sold-out or over-quantity lines with ⚠.
- **Checkout with a guest option:**
  - `/checkout` works **without an account** (name and email only), or pre-filled for logged-in shoppers.
  - Pickup or shipping. Payment is at pickup or on delivery, and no card details are ever collected.
  - `POST /api/orders` re-checks stock in **one transaction** (it can't oversell), charges catalogue prices, saves `orders` and `order_items`, and reduces inventory.
  - An order confirmation page.
- **Click history → recommendations:**
  - Every product page opened is saved in a new **`product_views`** table, by account or by an anonymous visitor id for guests.
  - A scoring engine (category, garment color, tags, recency) powers "**Picked for you · Because you viewed …**" on the home page and "You might also like" on product pages.
  - Handsome Dan got the same memory: recently viewed items in his context, and a new `get_recommendations` tool.
- **Low stock → restock purchase list:**
  - A new **`purchase_list`** table. Any size at 5 or fewer units is flagged automatically after each order and in a startup sweep.
  - Reorder quantity = (par 25 − stock) + units sold in the last 30 days.
  - A staff-key-protected API route, and `scripts/export_purchase_list.py` → `output/purchase_list.csv` (261 sizes, 6,122 units).
- **Fixed while testing:**
  - The cart badge was hidden on phones.
  - The brand name wrapped on small screens.
  - The chat's search results covered the Cart page.
  - Handsome Dan repeated a stale stock number from an old chat. The agent test caught this, and a prompt rule fixed it.
- **Verified:**
  - New `scripts/check_shop.py` passes **15/15** (it cleans up its own test data).
  - `check_agent.py` passes **22/22**, including 2 new scenarios.
  - Auth passes 16/16, and the build passes.
  - **In the browser as a guest:** Add to cart (3 × L) → badge 3 → Cart $204.00 → guest checkout → order **CC-33FB9E** → database shows the guest order, L stock 8 → 5, a purchase-list line with reorder 23, and the product view → home page shows "Picked for you · Because you viewed Basic Hoodie Big Yale".

**Evidence:** `output/usability.md`, `output/screenshots/p9_add_to_cart.jpg`, `p9_cart_badge.png`, `p9_cart_page.jpg`, `p9_guest_checkout.jpg`, `p9_order_confirmation.jpg`, `p9_picked_for_you.jpg`, `output/p9_shop_checks.txt`, `output/purchase_list.csv`, and the `orders`, `product_views` and `purchase_list` tables.

### Follow-up prompts

_(added as I go)_

---

## Problem 10: Interactive design (bark, fly-to-cart, growl)

### Prompt 10.1: Fun interactions (my words)

> Problem 10: make the handsome dan bark when the icon is clicked to get back to the home page. When a user clicks on an item to add to their cart, forma  bubble of the image inside the bubble showing it moving to the users cart. If the user removes an item from the cart, make a dog growl sound.
>
> Write the output/design.md: of what I changed and explain these are interactive features to keep the customer engaged in the site and want to purchase more items or view more items so they don't leave the webpage.

**What the AI did:**
- **New `frontend/src/fx.ts`.** Every sound is **generated in the browser with the Web Audio API**, so there are no audio files to license or download:
  - **Bark:** two quick "woofs".
  - **Growl:** a low, ~1 second rumble.
  - **Fly-to-cart:** the bubble animation.
- **Bark on the logo.** Clicking the Handsome Dan logo goes home, plays the bark, and makes Dan's face wiggle.
- **Fly-to-cart bubble.** Clicking **Add to cart** creates a round bubble with the product photo that arcs into the 🛒 cart icon. The icon then hops and the count goes up. The bubble starts at the photo, or at the button if the photo is off-screen.
- **Growl on Remove.** Clicking **Remove** in the Cart plays the growl as the item is removed.
- **Guard-rails:**
  - a **🔊/🔇 sound toggle** in the nav, remembered per browser;
  - sounds only play right after a click;
  - animations are skipped for "reduced motion" users;
  - the bubble is hidden from screen readers.
- **Fixed while testing.** The new sound button made the phone nav too wide and pushed the ☰ menu off-screen, so the spacing was tightened for small phones.
- **Verified in the browser:**
  - The bark and growl were rendered offline and measured: the bark is 2 bursts at ~360 Hz, the growl 1 sustained low rumble at ~100 Hz.
  - Logo click → home, 2 bark voices played, wiggle animation.
  - The bubble was tracked over 52 frames, from the button to exactly the cart icon centre, and the badge went 0 → 1 → 2.
  - A mid-flight freeze-frame screenshot was captured.
  - Remove → growl played and the cart was empty.
  - Muted → 0 sounds.
  - The build passes, and there were no console errors on fresh loads.
- **Wrote `output/design.md`.** It covers each change, why it keeps shoppers engaged (staying on the site, browsing more, adding more and keeping items in the cart), the guard-rails, and the verification.

**Evidence:** `output/design.md`, `output/screenshots/p10_fly_to_cart_bubble.jpg`, `p10_cart_before_remove.jpg`, `p10_after_remove_growl.jpg`, `p10_nav_sound_toggle.png`

### Follow-up prompts

_(added as I go)_

#### Prompt 10.2

> can i see what the product is now?

**What the AI did:** Checked that both servers were running, then opened http://localhost:5173 in my browser and in the browser pane.

---

## Problem 11: Site testing (app check)

### Prompt 11.1: Document the live-site checks (my words)

> Problem 11: Site testing (app check)
>
> I have tested the live site which shoudl be documented in output/app_check.html (a page you can double click and open). I need you to document the interaction I have had with the chat bot on the site where i asked specific questions including the inventory count of an item. I also need you to analyze teh dynamic search-results cards appearing after a category question (e.g. hoodies) and lastly, document the usability of the features I added in problem 9, which has been accomplished properly. The sound effects are there, the bubble occurs when an item is added to the selection and the growl happens if an item is removed from the cart.
>
> Ensure the HTML is easy to grade by: heading for each check, screenshot, one or two sentences on what the screenshot proves which i just explained above. Place the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example app_check_images/inventory.png).

**What the AI did:**
- **Checked the database for my own test session first.** I had tested as a guest: 9 product views were recorded, but guest chats aren't saved. So the AI **re-ran each check in the browser** and captured fresh screenshots, and the page says so plainly.
- **Took 14 screenshots** into `output/app_check_images/`, and checked every number against `campus_customs.db`:
  - **Chatbot:**
    1. "How many Basic Hoodie Big Yale … left in XS?" → "**15 left in XS**" (database: 15).
    2. "Ice Hockey Left Chest Hoodie in medium? How much?" → "**sold out in M** … **$68.00**" (database: M = 0).
  - **Dynamic search results:**
    3. "what hoodies are available?" → "25 hoodies, $45.00–$68.00", with a "12 on the page" button.
    4. The results section on the page.
    5. One card (image, name, price, short info).
    6. A chat card opens the Problem 3 detail page.
  - **Usability and effects:**
    7. The fly-to-cart bubble, frozen mid-flight.
    8. The cart page (2 items, $100.00).
    9. Guest checkout.
    10. Guest order confirmation CC-33FB9E.
    11. **Bark** on the logo click.
    12. **Growl** on Remove.
    13. "Picked for you".
    14. The restock purchase list.
- **Made the sounds visible.** A screenshot can't capture sound, so a test-only "Sound check" overlay drew the bark and growl waveforms and logged each sound as it played: "BARK (2 woofs)" after the logo click and "GROWL" after Remove.
- **Fixed while testing:**
  - The "Picked for you" label said "Because you viewed 2025 Yale vs Harvard T Shirt" while showing hoodies. It now names the main interest: "Because you've been looking at hoodies, like the Crew Left Chest Hoodie". `check_shop.py` was updated and still passes 15/15.
- **Wrote `output/app_check.html`:**
  - a self-contained page with no internet needed, so it opens by double-click;
  - a summary table of all 14 checks (all PASS);
  - for each check, a **heading**, the **screenshot** (relative path `app_check_images/...`), and a **"What this proves"** sentence or two;
  - all 14 image links were verified to resolve.

**Evidence:** `output/app_check.html`, `output/app_check_images/01–14_*.jpg`

### Follow-up prompts

_(added as I go)_

---

## Problem 12: Audit trail, safety, finish the harness

### Prompt 12.1: Audit trail, safety rules, final harness (my words)

> Problem 12: Audit trail, safety, finish harness
>
> Keep an append-only output/audit_trail.json of agent-loop activity (time, tool name, short args/result, stop reason). Don't wipe it between the runs
>
> Safety rules: stop the transaction from being complete if a payment method is not applied, double check the inventory count every hour to minimize the risk of transactions that can't be completed and fulfilled, make sure when the guest user is making a purchase that there is a field to have them input their phone number, email address and name. Provide them with a unique transaction number that can be trackable after the transaction is completed.
>
> Finish output/harness.md so it is clear how the system works. This will include the
>
> * Model fields in models.py and why you chose them
> * Tools and abilities
> * Safety rules
> * Specs (loop limits, result caps, models, how to run front + back)

**What the AI did:**
- **Append-only audit trail.**
  - New `backend/audit.py`, plus `agent.run_agent()`, which runs the agent step by step (`agent.iter`) and appends to `output/audit_trail.json`:
    - the user message (as `guest` or `user#id`, never an email);
    - each **tool call** with its time, name, short arguments and short result;
    - an **end** entry with the **stop reason**, model, request count, tokens and duration;
    - or an **error** entry with its stop reason.
  - Writes are locked and atomic, and existing entries are never removed. An unreadable file would be renamed aside, never wiped.
  - The website chat and the test script both use it. The trail grew 4 → 92 entries across runs with nothing lost.
  - The first run's crash (a bug fixed during this problem) is still recorded as an `error` entry.
- **Safety rules:**
  - **Payment method required.** Checkout must choose card or cash at pickup, or on delivery. Otherwise the server refuses with **402**, **before** anything is saved or any stock is taken. The Place order button is disabled until one is chosen. No card numbers are ever collected.
  - **Hourly inventory check.** A FastAPI background task runs `shop.inventory_check()` at startup and every 3600 s. It repairs impossible stock, flags low or sold-out sizes for restock, closes restocked lines, and logs to the new `inventory_checks` table and the audit trail. A temporary 3-second run proved it fires on its own.
  - **Guest name, email and phone.** These are required for guests (phone: 10–15 digits); the form has a phone field marked "required for guests".
  - **Unique, trackable transaction number.** `CC-YYMMDD-XXXXXX`, checked for uniqueness and backed by a UNIQUE constraint. It's shown on the confirmation page with a **📦 Track this order** button. The new **/track** page needs the number plus the email or phone, so other people's orders can't be browsed.
- **Updated Handsome Dan's prompt** for the payment-method requirement, guest details and order tracking. He can't look up orders, so he points shoppers to the Track order page.
- **Finished `output/harness.md`:**
  - a **system diagram** and quick links at the top;
  - **§11** every model in `models.py`, field by field, with why it was chosen;
  - **§12** tools and abilities;
  - **§13** safety rules, with where each is enforced;
  - **§14** specs: models, loop limits, result caps, and how to run the front and back end;
  - **§15** the audit trail format, with a real example.
- **Verified:**
  - `check_shop.py` passes **24/24** (9 new Problem 12 checks).
  - `check_agent.py` passes **22/22**, now writing to the audit trail.
  - `check_auth.py` passes **16/16**, and the build passes.
  - **In the browser as a guest:** Place order disabled without a payment method → chose Card at pickup → order **CC-261013-Q2AWVN** → Track page shows the timeline and the payment due at pickup.

**Evidence:** `output/audit_trail.json`, `output/harness.md` §11–§15, `output/screenshots/p12_payment_required_blocked.jpg`, `p12_payment_chosen.jpg`, `p12_transaction_number.jpg`, `p12_track_order.jpg`, and the `inventory_checks` and `orders` tables.

### Follow-up prompts

_(added as I go)_

---

## Problem 13: Push to GitHub and submit the URL

### Prompt 13.1: Publish the repo (my words)

> Problem 13: Push to GitHub and submit the URL
>
> Put the code in a folder named hw4 and push it to a public GitHub repository. I will need a repo URL that I can submit the repo URL, not a zip folder.
>
> Don't put the real .env, campus_customs.db or product images in the GitHub repo. Use .gitignore. Include the .env.example with placeholders only
>
> Here is the expected file layout in the 1st image
>
> Local-only data pack (not in git) is the 2nd image
>
> Lastly, the agent itself is going to be made up of 4 files under backend/: prompts/prompt.md, agent.py, tools.py, and models.py
>
> Read.md should explain how to run the front end and back end after placing the data pack
>
> Confirm that you were able to successfully complete all this once your done

_(I attached two images: the expected `hw4/` file layout, and the local-only `data/` pack: `campus_customs.db` and `products/`.)_

**What the AI did:**
- **Checked before publishing:**
  - Scanned every file that would be committed for the real secret values in `.env` (`PORTKEY_API_KEY`, `SESSION_SECRET`, `STAFF_KEY`, the demo password). None were found.
  - Found that `output/database_overview.html` listed real people from the provided `users` table (names and Yale emails). Changed `scripts/analyze_db.py` to show initials and masked emails, and regenerated the page.
- **Matched the expected layout:**
  - Moved `requirements.txt` to the repo root.
  - The agent is 4 files under `backend/`: `prompts/prompt.md`, `agent.py`, `tools.py`, `models.py`.
  - `main.py` runs with `uvicorn main:app --reload`, alongside supporting modules `auth.py`, `db.py`, `shop.py` and `audit.py`.
  - `output/` has `harness.md`, `design.md`, `usability.md`, `app_check.html`, `app_check_images/` and `audit_trail.json`.
- **`.gitignore` excludes:**
  - `data/` and `*.db` (the database and product images);
  - `.env`;
  - `.venv`, `node_modules`, `dist`;
  - audit-trail temp files.
- **`.env.example`** now has clear placeholders only, such as `your-portkey-api-key-here`.
- **Rewrote `README.md`.** It covers the repo layout, **placing the data pack** in `data/`, one-time setup, running the **backend** (`cd backend` → `uvicorn main:app --reload --port 8000`) and the **frontend** (`cd frontend` → `npm run dev` → http://localhost:5173), the checks, the API and security notes.
- **Published:**
  - `git init` → one commit (122 files, about 3 MB) → created the **public** GitHub repo **https://github.com/rscrivano/hw4** with `gh` → pushed `main`.
  - Cloning it creates a folder named **`hw4`**.
- **Verified from a fresh clone of GitHub:**
  - The layout matches the expected tree.
  - There's no `.env`, `data/` or `.db` in the repo.
  - After placing the data pack, `git status` stayed clean, which confirms `data/` is ignored.
  - A fresh venv from `requirements.txt` installed.
  - `uvicorn main:app --reload` from `backend/` started.
  - `/api/health` was OK, `/api/products` returned 102, images loaded, and the chat answered "25 left in XXL" (matching the database).
  - The frontend ran `npm install` and `npm run build` successfully.
  - The temporary clone, venv and server were removed afterwards.
- **Note:** a very deep temp path hit Windows' 260-character limit during `pip install`, so a "clone into a short path" tip was added to the README.

**Repo URL to submit:** https://github.com/rscrivano/hw4

#### Prompt 13.2

> show me the actual site now too

**What the AI did:** Checked that both servers were running, then opened http://localhost:5173 in my browser and in the browser pane.

#### Prompt 13.3

> does this site come up through my assignment submission url so the professor can see what I created?

**What the AI did:** Explained that the GitHub URL shows the code and documents, not a running site. The live site needs the data pack and a Portkey key on a local machine. It suggested publishing `app_check.html` with GitHub Pages so the professor can click through the screenshots.

#### Prompt 13.4

> yes do option 1 and make note of how he can easily access to the site to see it by providing the link to it in the package

**What the AI did:**
- **Checked the repo was safe to publish with GitHub Pages.** No Liquid template tags (double curly braces, or curly-brace-percent) appeared in any Markdown or HTML file, so it builds as-is with no extra files that would change the expected layout.
- **Hit one snag.** That log line originally typed the template characters themselves, which made the Pages build fail. It was reworded to describe them in words, and the build passed.
- **Added a "👀 See it online (no setup needed)" section at the top of `README.md`,** with links to:
  - the **live App check page**;
  - the project home page;
  - the harness, usability and design docs;
  - the prompt log;
  - the screenshots folder.
- **Added links back to the code** ("View the code on GitHub", "How to run it", "How the system works") in the `app_check.html` header.
- **Turned on GitHub Pages** (the `main` branch, from the root) and set the repo's website link to the App check page, so it also shows at the top right of the GitHub repo page.
- **Verified the live site:**
  - **https://rscrivano.github.io/hw4/output/app_check.html** is live: all 14 checks and **14/14 screenshots** load.
  - https://rscrivano.github.io/hw4/ shows the README as a web page.
- **Fixed a layout issue found on the live page:** the summary table was 8px too wide on phones, so on small screens it now uses tighter padding and hides the "Area" column.
