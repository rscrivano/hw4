# Campus Customs: Usability Improvements (Problem 9)

The core shop (browse, accounts, the Handsome Dan chat agent, memory) already worked. Before this, a shopper could find the perfect hoodie and then had **no way to buy it**. The business also had no idea what people were interested in, or what it was about to run out of.

This document records each improvement: **what was added** and **why it helps**. It was started as a plan before building and filled in as each part was finished and tested.

| # | Improvement | Who it helps | Status |
|---|---|---|---|
| 1 | Shopping cart you can see and open | Shoppers | ✅ Built and tested |
| 2 | Checkout, including **guest checkout** | Shoppers, sales | ✅ Built and tested |
| 3 | Click history → "Picked for you" recommendations (site and Handsome Dan) | Shoppers, marketing | ✅ Built and tested |
| 4 | Low-stock tracking → automatic restock **purchase list** | The business (inventory) | ✅ Built and tested |
| 5 | Small fixes found while testing | Shoppers | ✅ |

Code: `backend/shop.py` (new), `backend/main.py` (new routes), and in `frontend/src/`: `cart.tsx`, `pages/Cart.tsx`, `pages/Checkout.tsx`, `pages/OrderConfirmation.tsx`, `components/Recommendations.tsx`. Tests: `scripts/check_shop.py`.

---

## 1. Shopping cart

### What was added
- **Add to cart** on every product page:
  - Pick a size, then choose a quantity. The dropdown only goes up to the number actually in stock.
  - Sold-out sizes can't be added, and you can't add more than is in stock, counting what's already in the cart.
  - A green confirmation says "✓ Added 3 × size L to your cart · **View cart →**".
- **A 🛒 Cart icon with a live item-count badge** in the nav bar, on every page.
  - On phones the icon sits **outside** the collapsed ☰ menu, so the count is always visible.
- **A Cart page** (`/cart`) showing exactly what the shopper is ordering: photo, name, size, price each, a quantity selector, **Remove**, line totals, item count and subtotal.
  - Clicking an item returns to its product page.
- **The server always re-prices the cart.**
  - The cart in the browser only remembers *which* items and sizes were picked.
  - Every time the Cart page opens, `POST /api/cart/quote` re-reads **live prices and stock** from the database.
  - If something sold out or fell below the quantity in the cart, that line is marked ⚠ (e.g. "Only 2 left in size XL"), and Checkout is disabled until it's fixed.
- **The cart is kept in `localStorage`,** so it works for guests and survives reloads and navigation.

### Why it helps
- **Shoppers can buy more than one thing at once,** for example a hoodie for themselves and a tee for a sibling. Before, there was no path from "I like this" to "I'm buying this".
- **A visible cart builds confidence.** The always-on badge confirms the click worked, and the Cart page lets the shopper check sizes and quantities **before** paying. That cuts down on wrong-size orders and returns.
- **No surprises at checkout.** Because the server re-checks prices and stock, the cart never shows a stale price or promises an item that has just sold out.

---

## 2. Checkout, including as a guest

### What was added
- **A Checkout page** (`/checkout`) with name, email, and **in-store pickup** (57 Broadway, pay in store) or **ship to me** (address, pay on delivery).
- **Guest checkout.** No account is needed:
  - The page says "**Checking out as a guest**. No account needed. Just tell us where to send your confirmation", with an optional "Log in instead" link.
  - Logged-in shoppers see "Checking out as *Name*", with their details pre-filled. Their order is linked to their account (`orders.user_id`).
- **Safe order placement** (`POST /api/orders`), all in **one database transaction**:
  1. Re-check every line against live stock. It can **never oversell**: if someone else bought the last unit, the shopper gets a clear 409 message such as "only 5 left".
  2. Charge the **catalogue price** (never a price sent by the browser).
  3. Save the `orders` row and its `order_items`.
  4. **Reduce inventory.**
  5. Flag any size that is now low on the restock list (see #4).
- **An order confirmation page** with the order number (e.g. `CC-33FB9E`), the items, the subtotal and pickup or shipping instructions.
- **No card details are ever collected.** Payment is at pickup or on delivery. This class project shouldn't handle real payment data, and Handsome Dan's prompt tells shoppers never to share card details in chat.

### Why it helps
- **Fewer abandoned carts.** Being forced to create an account is one of the most common reasons people abandon a purchase. Parents, relatives and visitors buying a one-off gift can now check out in seconds with a name and email.
- **Accounts still have a purpose.** Logged-in shoppers get pre-filled details, and their orders are tied to their account and chat memory.
- **Accurate inventory.** Stock goes down the moment an order is placed, so Handsome Dan, the product pages and the cart all show what's really left.

---

## 3. Click history → better recommendations

### What was added
- **Every product a shopper opens is recorded** in a new `product_views` table (`POST /api/events/view`).
  - **Logged in:** saved under their `user_id`, so the history follows them across devices.
  - **Guests:** saved under an anonymous `visitor_id` (a random id kept in their browser), so guests get personalised picks too.
- **A recommendation engine** (`shop.recommend`). It scores every **in-stock** product against the shopper's recent clicks:
  - **+3** for the same category;
  - **+2** for the same garment color;
  - **+0.5** for each shared tag.
  - Newer clicks count more.
  - Items they've just looked at are pushed down, so the picks are *new* ideas.
  - With no history yet, it falls back to "Popular right now", the most-viewed products overall.
- **"Picked for you"** on the home page and **"You might also like"** on every product page, each showing the reason:
  - "**Because you viewed Basic Hoodie Big Yale**" after one click;
  - "**Because you've been looking at hoodies, like the Crew Left Chest Hoodie**" after several.
  - The label names the shopper's *main* interest, so it always matches the picks. This was fixed during Problem 11 testing: the label used to name only the most recent click.
- **Handsome Dan shares this memory.**
  - His context now includes the shopper's recently viewed products.
  - A new **`get_recommendations`** tool lets him answer "what would you recommend?" from their actual clicks.
  - The prompt tells him to suggest **one** relevant idea when it fits, and not to push recommendations into every reply.

### Why it helps
- **Shoppers find what they want faster.** Someone who looked at three navy sport hoodies sees *other* navy sport hoodies, not random tees.
- **Better advertising for the store.** The store can promote items each person is actually likely to buy. That's more effective than generic banners, and only uses what they clicked *on this site*.
- **The data is kept for the future.** The `product_views` history shows which products attract interest, even ones that don't sell. That can guide buying, promotions and which items to feature.

---

## 4. Low-stock tracking → restock purchase list

### What was added
- **A `purchase_list` table:** the business's inventory purchase list. Each line has the product, size, stock when flagged, **reorder quantity**, reason ("sold out" or "low stock (N left)"), status (`open` → `ordered` → `received`) and timestamps.
  - A database rule allows only **one open line per product and size**, so lines are updated, never duplicated.
- **Automatic flagging** whenever a size reaches **5 or fewer** units. That's the same "low stock" line Handsome Dan and the product pages use.
  - **After every order:** it runs inside the same transaction as the sale.
  - **When the server starts:** a full inventory sweep catches stock that changed outside the app.
- **The reorder quantity formula:**

  ```
  reorder_qty = (par level 25 − current stock) + units of that size sold in the last 30 days
  ```

  - The par level is 25, the highest stock level in the catalogue.
  - The 30-day sales term is a demand buffer, so sizes that are selling fast are reordered in larger amounts.
  - Example from testing: the Basic Hoodie Big Yale in L went 8 → 5 after a 3-unit order, so the reorder is (25 − 5) + 3 = **23**.
- **Staff access to the list:**
  - `GET /api/staff/purchase-list` returns the open lines, totals and units. It's protected by a `STAFF_KEY` (in `.env`) and returns 403 without it.
  - `scripts/export_purchase_list.py` writes **`output/purchase_list.csv`**, ready for a spreadsheet, with an estimated retail value per line.
  - Current list: **261 sizes to restock (145 sold out, 116 low), 6,122 units.**

### Why it helps
- **Fewer missed sales.** Before, a size quietly hit 0 and shoppers were turned away. Now it's on the purchase list the moment it's low, before it runs out.
- **No manual stock-counting.** The list is always current and says exactly **how many** to order, not just "this is low".
- **Demand-aware ordering.** Popular sizes are reordered in larger amounts, and slow sizes aren't overstocked.
- **Safe for shoppers.** The list is internal, behind a staff key, and never shown on the public site.

---

## 5. Small fixes found while testing
- **Cart count on phones.** The cart icon was hidden inside the collapsed ☰ menu on phones, so a dedicated cart button was added next to the menu button.
- **Brand name wrapping.** The longer nav bar made "Campus Customs" wrap onto two lines on small phones, so the tagline is hidden below 480px.
- **Results panel on the Cart page.** The chat's on-page search results (Problem 7) appeared above the Cart and pushed the order summary off-screen. They're now hidden on cart, checkout, order and account pages, and reappear everywhere else.
- **Stale stock in chat memory.** When recalling an earlier chat, Handsome Dan repeated an old "had 2 left" count, but stock changes as orders come in. The prompt now says to mention *what* the shopper looked at and re-check stock instead of quoting old numbers. The automated test caught this.

---

## How it was verified

| Check | Result |
|---|---|
| `scripts/check_shop.py`: cart quote, guest and logged-in checkout, no overselling, inventory reduced, restock flag and reorder math, click history, recommendations, staff key (`output/p9_shop_checks.txt`) | **15/15**. Afterwards it restores stock and removes only its own test rows |
| `scripts/check_agent.py`: 2 new Problem 9 scenarios (Dan recommends from click history; Dan explains guest checkout and pay-at-pickup) plus all earlier scenarios | **22/22** |
| `scripts/check_auth.py` and the production build | 16/16, and the build passes |

**In the browser, as a guest** (screenshots in `output/screenshots/p9_*.jpg/png`):
1. Opened the Basic Hoodie Big Yale, picked **L**, set **Qty 3**, then **Add to cart**. The confirmation appeared, and the cart badge showed **3**.
2. The Cart page showed Size L · Qty 3 · **$204.00**, with "No account needed: you can check out as a guest".
3. Checkout showed the "**Checking out as a guest**" banner. I entered a name and an example.com email, chose in-store pickup, and placed the order. The confirmation read **"Boola Boola, thank you, Guest! Your order number is CC-33FB9E"**.
4. In the database:
   - `orders` has CC-33FB9E with `user_id` NULL (guest) and $204.00;
   - L stock went **8 → 5**;
   - `purchase_list` gained "Basic Hoodie Big Yale · L · low stock (5 left) · reorder **23**";
   - `product_views` recorded the visit.
5. The home page now shows "**Picked for you · Because you viewed Basic Hoodie Big Yale**" with 4 navy pullover hoodies.
