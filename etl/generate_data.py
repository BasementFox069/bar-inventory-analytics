import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from etl.inventory_names import inventory_items   # product names + categories


np.random.seed(42)

# -----------------------
# Setup folders
# -----------------------
RAW_DIR = os.path.join("data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

# -----------------------
# 1. Suppliers (5 rows)
# -----------------------
suppliers = pd.DataFrame({
    "supplier_id": range(1, 6),
    "name": [f"Supplier {i}" for i in range(1, 6)],
    "lead_time_days": np.random.randint(5, 15, 5),
    "on_time_rate": np.round(np.random.uniform(0.7, 0.95, 5), 3),
    "min_order_qty": [10, 20, 30, 40, 50]
})
suppliers.to_csv(f"{RAW_DIR}/suppliers.csv", index=False)

# -----------------------
# 2. Products (20 rows)
# -----------------------
products = pd.DataFrame({
    "product_id": range(1, 21),
    "sku": [f"SKU{i:03}" for i in range(1, 21)],
    "product_name": [item["name"] for item in inventory_items],
    "category": [item["category"] for item in inventory_items],
    "unit_cost": np.random.uniform(5, 30, 20).round(2),
    "unit_price": np.random.uniform(35, 60, 20).round(2),
    "supplier_id": np.random.choice(suppliers["supplier_id"], 20)
})
products.to_csv(f"{RAW_DIR}/products.csv", index=False)

# -----------------------
# 3. Sales (90 days × 20 products = ~1800 rows)
# -----------------------
dates = pd.date_range(datetime.today() - timedelta(days=90), periods=90)
sales_records = []
for d in dates:
    for pid in products["product_id"]:
        units = np.random.poisson(5)   # avg ~5 units/day
        price = products.loc[products.product_id == pid, "unit_price"].iloc[0]
        sales_records.append([d.date(), pid, units, round(units * price, 2)])

sales = pd.DataFrame(sales_records, columns=["dt", "product_id", "units", "revenue"])
sales.to_csv(f"{RAW_DIR}/sales.csv", index=False)

# -----------------------
# 4. Purchase Orders (weekly × 20 products ≈ 2600 rows)
# -----------------------
po_records = []
po_id = 1
for pid in products["product_id"]:
    for d in dates[::7]:  # weekly orders
        qty = np.random.randint(20, 50)
        supplier_id = products.loc[products.product_id == pid, "supplier_id"].iloc[0]
        po_records.append([
            po_id, pid, supplier_id,
            d.date(),
            (d + timedelta(days=7)).date(), 
            (d + timedelta(days=7)).date(),   
            qty, qty
        ])
        po_id += 1

purchase_orders = pd.DataFrame(po_records, columns=[
    "po_id", "product_id", "supplier_id",
    "order_date", "promised_date", "received_date",
    "qty_ordered", "qty_received"
])
purchase_orders.to_csv(f"{RAW_DIR}/purchase_orders.csv", index=False)

# -----------------------
# 5. Inventory Snapshots (90 days × 20 products = ~1800 rows)
# -----------------------
inv_records = []
for pid in products["product_id"]:
    qty_on_hand = np.random.randint(100, 300)  # randomized starting stock
    for d in dates:
        # daily sales for that product
        day_sales = sales.loc[(sales["dt"] == d.date()) & (sales["product_id"] == pid), "units"].sum()
        qty_on_hand = max(0, qty_on_hand - int(day_sales))
        inv_records.append([d.date(), pid, qty_on_hand])

inventory = pd.DataFrame(inv_records, columns=["dt", "product_id", "qty_on_hand"])
inventory.to_csv(f"{RAW_DIR}/inventory_snapshots.csv", index=False)

print("✅ Synthetic CSVs generated in data/raw/")
