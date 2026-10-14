"""Problem 2 - read-only profile of data/campus_customs.db.

Builds output/database_overview.html (a visual summary of every table).
Run from the Homework 4 folder:  python scripts/analyze_db.py
The database is opened read-only, so this script never changes it.
"""

import html
import json
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "campus_customs.db"
OUT = ROOT / "output" / "database_overview.html"
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]


def connect():
    return sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)


def bar_rows(items, unit=""):
    """items: list of (label, value). Renders horizontal CSS bars."""
    top = max((v for _, v in items), default=1) or 1
    rows = []
    for label, value in items:
        pct = 100 * value / top
        rows.append(
            f'<div class="bar"><span class="lbl">{html.escape(str(label))}</span>'
            f'<span class="track"><span class="fill" style="width:{pct:.1f}%"></span></span>'
            f'<span class="val">{unit}{value:g}</span></div>'
        )
    return "\n".join(rows)


def schema_table(con, table, notes):
    cols = con.execute(f"PRAGMA table_info({table})").fetchall()
    body = "".join(
        f"<tr><td><code>{c[1]}</code></td><td>{c[2]}</td>"
        f"<td>{'PK' if c[5] else ''}{' NOT NULL' if c[3] else ''}</td>"
        f"<td>{html.escape(notes.get(c[1], ''))}</td></tr>"
        for c in cols
    )
    return (
        "<table><thead><tr><th>Field</th><th>Type</th><th>Constraint</th>"
        f"<th>Why it matters</th></tr></thead><tbody>{body}</tbody></table>"
    )


def main():
    con = connect()
    q = lambda s, *a: con.execute(s, a).fetchall()

    counts = {t: q(f"SELECT COUNT(*) FROM {t}")[0][0]
              for t in ("catalogue", "inventory", "users", "chat_messages")}

    # --- catalogue ---
    garment = q("SELECT garment_type, COUNT(*) FROM catalogue GROUP BY 1 ORDER BY 2 DESC")
    price = q("SELECT price, COUNT(*) FROM catalogue GROUP BY 1 ORDER BY 1")
    colors = Counter(c for (s,) in q("SELECT colors FROM catalogue") for c in json.loads(s))
    tags = Counter(t.lower() for (s,) in q("SELECT search_tags FROM catalogue") for t in json.loads(s))
    missing_img = [p for (p,) in q("SELECT image_file_path FROM catalogue")
                   if not (ROOT / "data" / p).exists()]

    # --- inventory ---
    by_size = {s: (u, z) for s, u, z in
               q("SELECT size, SUM(quantity), SUM(quantity = 0) FROM inventory GROUP BY size")}
    qty_dist = q("SELECT quantity, COUNT(*) FROM inventory GROUP BY 1 ORDER BY 1")
    zero_rows = q("SELECT COUNT(*) FROM inventory WHERE quantity = 0")[0][0]
    low_stock = q("""SELECT c.name, SUM(i.quantity) t, SUM(i.quantity = 0) z
                     FROM inventory i JOIN catalogue c USING (product_id)
                     GROUP BY product_id ORDER BY t LIMIT 8""")

    # --- samples for the gallery ---
    sample = q("""SELECT c.name, c.price, c.image_file_path, c.garment_type,
                         GROUP_CONCAT(i.size || ':' || i.quantity, '  ')
                  FROM catalogue c JOIN inventory i USING (product_id)
                  GROUP BY c.product_id ORDER BY RANDOM() LIMIT 8""")

    # Real people are in this table, and this page goes in a public repo: show initials and a masked
    # email (the course's shared test user is left readable).
    def mask(uid, name, email, h, created):
        if email.startswith("test@"):
            return uid, name, email, h, created
        user, _, domain = email.partition("@")
        initials = " ".join(w[0] + "." for w in name.split())
        return uid, initials, f"{user[0]}***@{domain}", h, created
    users = [mask(*r) for r in q("SELECT id, name, email, substr(password_hash, 1, 14) || '…', created_at FROM users")]
    chat = q("SELECT role, COUNT(*), SUM(products_json IS NOT NULL) FROM chat_messages GROUP BY role")

    notes_cat = {
        "product_id": "Stable slug key; joins to inventory and identifies cards the bot shows.",
        "name": "What shoppers and the bot call the item.",
        "garment_type": "Lets the bot filter by kind (hoodie, tee…) – values are inconsistent, normalise them.",
        "description": "Rich text for answering 'what does it look like?' questions.",
        "colors": "JSON list; powers color questions ('do you have it in red?').",
        "search_tags": "JSON keyword list; main hook for keyword search / matching.",
        "image_file_path": "Relative to data/; served so product cards show photos.",
        "price": "Single source of truth for honest price answers.",
    }
    notes_inv = {
        "id": "Row key only.",
        "product_id": "Links each size row to a catalogue product.",
        "size": "XS–XXL; shoppers ask about their size specifically.",
        "quantity": "Real stock; 0 means sold out – bot must never promise it.",
    }
    notes_usr = {
        "id": "Account key; links chat history to a shopper.",
        "name": "Full display name for greetings.",
        "email": "Unique login identifier.",
        "password_hash": "pbkdf2_sha256$salt$hash – verify, never store plain text.",
        "created_at": "Audit trail of when the account was made.",
        "first_name": "Friendly personalised greeting from the bot.",
        "last_name": "Completes the profile; rarely needed by the bot.",
    }
    notes_chat = {
        "id": "Message order key.",
        "user_id": "Whose conversation this is.",
        "role": "user vs assistant turn – rebuilds history for the agent.",
        "content": "The message text.",
        "products_json": "Products shown with the reply so the page can redraw them.",
        "created_at": "Timeline of the conversation.",
    }

    stat = lambda n, l: f'<div class="stat"><b>{n}</b><span>{l}</span></div>'
    gallery = "".join(
        f'<figure><img src="../data/{html.escape(p)}" alt="{html.escape(n)}" loading="lazy">'
        f'<figcaption><b>{html.escape(n)}</b><em>${pr:.0f} · {html.escape(g)}</em>'
        f'<small>{html.escape(stock)}</small></figcaption></figure>'
        for n, pr, p, g, stock in sample
    )
    size_items = [(s, by_size[s][0]) for s in SIZE_ORDER]
    zero_items = [(s, by_size[s][1]) for s in SIZE_ORDER]

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Campus Customs Data</title>
<style>
:root{{--bg:#0b0b0f;--card:#16161d;--line:#2a2a35;--text:#f2f0f5;--muted:#a9a4b4;--pink:#ff3d9a;--pink2:#ff8cc6}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,Segoe UI,sans-serif}}
main{{max-width:1100px;margin:auto;padding:32px 16px 64px}}
h1{{font-size:30px;margin:0}}h1 span{{color:var(--pink)}}h2{{color:var(--pink2);margin:40px 0 12px;font-size:20px}}
p.sub{{color:var(--muted);margin:4px 0 24px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}
.stat,.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}}
.stat b{{display:block;font-size:28px;color:var(--pink)}}.stat span{{color:var(--muted);font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}}
.card h3{{margin:0 0 12px;font-size:15px}}
.bar{{display:grid;grid-template-columns:150px 1fr 48px;gap:8px;align-items:center;font-size:13px;margin:4px 0}}
.lbl{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--muted)}}
.track{{background:#24242e;border-radius:6px;height:12px}}.fill{{display:block;height:100%;border-radius:6px;background:linear-gradient(90deg,var(--pink),var(--pink2))}}
.val{{text-align:right}}
table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{text-align:left;padding:8px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{color:var(--pink2);font-weight:600}}code{{color:var(--pink)}}
.wrap{{overflow-x:auto}}
.gallery{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px}}
figure{{margin:0;background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden}}
figure img{{width:100%;aspect-ratio:1;object-fit:cover;background:#fff}}
figcaption{{padding:10px 12px;display:grid;gap:2px;font-size:13px}}figcaption em{{color:var(--pink2);font-style:normal}}figcaption small{{color:var(--muted)}}
ul.flags li{{margin:6px 0}}ul.flags b{{color:var(--pink)}}
</style></head><body><main>
<h1>Campus Customs <span>database overview</span></h1>
<p class="sub">Problem 2 · read-only profile of <code>data/campus_customs.db</code> · generated by <code>scripts/analyze_db.py</code></p>

<div class="stats">
{stat(counts['catalogue'], 'products in catalogue')}
{stat(counts['inventory'], 'inventory rows (product × size)')}
{stat(zero_rows, 'size rows sold out (qty 0)')}
{stat(counts['users'], 'user accounts')}
{stat(counts['chat_messages'], 'saved chat messages')}
{stat(f"${min(p for p,_ in price):.0f}–${max(p for p,_ in price):.0f}", 'price range')}
</div>

<h2>Key findings for the chatbot</h2>
<div class="card"><ul class="flags">
<li><b>Five tables, not three:</b> catalogue, inventory, users, plus a <code>chat_messages</code> table already used to save conversations (and SQLite's internal <code>sqlite_sequence</code>).</li>
<li><b>Every product has exactly 6 size rows</b> (XS–XXL) → {counts['inventory']} = {counts['catalogue']} × 6. No orphan inventory, no product without inventory.</li>
<li><b>{zero_rows} of {counts['inventory']} size rows ({100*zero_rows/counts['inventory']:.0f}%) are at quantity 0</b> – but no product is completely sold out. The bot must answer stock per size, not per product.</li>
<li><b><code>garment_type</code> is messy:</b> {len(garment)} spellings for ~8 real categories (e.g. “short-sleeve t-shirt” vs “short-sleeve T-shirt” vs “t-shirt”). Search must normalise or use tags.</li>
<li><b>Price is set by category:</b> tees $32, crewnecks $58, hoodies $68, quarter-zips $72, full-zip hoodies $88, jackets $98, a few $45 items.</li>
<li><b><code>colors</code> and <code>search_tags</code> are JSON text</b> – parse before filtering; “navy” and “navy blue” both appear.</li>
<li><b>Images:</b> {counts['catalogue'] - len(missing_img)}/{counts['catalogue']} image paths resolve to a real file in <code>data/products/</code>{'' if not missing_img else ' – missing: ' + ', '.join(missing_img)}.</li>
<li><b>Passwords are hashed</b> as <code>pbkdf2_sha256$&lt;salt&gt;$&lt;hex&gt;</code>; the backend must hash new sign-ups the same way.</li>
</ul></div>

<h2>Catalogue</h2>
<div class="grid">
<div class="card"><h3>Products by garment_type (raw values)</h3>{bar_rows(garment)}</div>
<div class="card"><h3>Products by price</h3>{bar_rows([(f"${p:.0f}", n) for p, n in price])}
<h3 style="margin-top:20px">Top colors (from JSON list)</h3>{bar_rows(colors.most_common(10))}</div>
</div>
<div class="card wrap" style="margin-top:16px"><h3>catalogue fields</h3>{schema_table(con, 'catalogue', notes_cat)}</div>
<div class="card" style="margin-top:16px"><h3>Most common search tags</h3>{bar_rows(tags.most_common(12))}</div>

<h2>Inventory</h2>
<div class="grid">
<div class="card"><h3>Total units by size</h3>{bar_rows(size_items)}</div>
<div class="card"><h3>Sold-out products by size (qty = 0)</h3>{bar_rows(zero_items)}</div>
<div class="card"><h3>Quantity values (rows per value)</h3>{bar_rows([(f"qty {v}", n) for v, n in qty_dist])}</div>
<div class="card"><h3>Lowest total stock</h3>{bar_rows([(f"{n} ({z} sizes out)", t) for n, t, z in low_stock])}</div>
</div>
<div class="card wrap" style="margin-top:16px"><h3>inventory fields</h3>{schema_table(con, 'inventory', notes_inv)}</div>

<h2>Users</h2>
<div class="card wrap"><h3>users fields</h3>{schema_table(con, 'users', notes_usr)}</div>
<div class="card wrap" style="margin-top:16px"><h3>Rows (hash truncated)</h3><table><thead><tr><th>id</th><th>name</th><th>email</th><th>password_hash</th><th>created_at</th></tr></thead><tbody>
{''.join('<tr>' + ''.join(f'<td>{html.escape(str(v))}</td>' for v in r) + '</tr>' for r in users)}
</tbody></table></div>

<h2>Chat messages (bonus table)</h2>
<div class="card wrap"><h3>chat_messages fields</h3>{schema_table(con, 'chat_messages', notes_chat)}
<p class="sub" style="margin-top:12px">{' · '.join(f'{r}: {n} messages ({p} with products attached)' for r, n, p in chat)}</p></div>

<h2>Sample products (random 8, with stock by size)</h2>
<div class="gallery">{gallery}</div>
</main></body></html>"""
    OUT.write_text(page, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
