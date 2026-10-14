"""Export the restock purchase list (Problem 9) to output/purchase_list.csv for the business.

Run from the Homework 4 folder:
    .venv\\Scripts\\python scripts\\export_purchase_list.py

Same data as GET /api/staff/purchase-list (which needs the STAFF_KEY header).
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import shop  # noqa: E402

shop.ensure_tables()
data = shop.purchase_list("open")
out = ROOT / "output" / "purchase_list.csv"
with out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["product_id", "name", "size", "stock_when_flagged", "reorder_qty", "reason", "unit_price",
                "est_retail_value", "flagged_at", "updated_at"])
    for i in data["items"]:
        w.writerow([i["product_id"], i["name"], i["size"], i["stock_when_flagged"], i["reorder_qty"], i["reason"],
                    f"{i['price']:.2f}", f"{i['price'] * i['reorder_qty']:.2f}", i["created_at"], i["updated_at"]])
sold_out = sum(1 for i in data["items"] if i["stock_when_flagged"] == 0)
print(f"{data['lines']} sizes to restock ({sold_out} sold out, {data['lines'] - sold_out} low), "
      f"{data['total_units']} units in total -> {out.relative_to(ROOT)}")
