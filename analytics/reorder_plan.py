import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from scipy.stats import norm

# -------------------------------
# 1. Database connection
# -------------------------------
USER = "root"
PASSWORD = ""   # empty since you're using no password
HOST = "localhost"
PORT = "3306"
DB = "inventory_db"

engine = create_engine(f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB}")

# -------------------------------
# 2. Parameters
# -------------------------------
SERVICE_LEVEL = 0.95   # 95% service level (z ≈ 1.65)
REVIEW_PERIOD = 7      # days between placing orders

z = norm.ppf(SERVICE_LEVEL)

# -------------------------------
# 3. Fetch demand & inventory data
# -------------------------------
demand_sql = """
SELECT product_id, avg_daily_units, std_daily_units
FROM v_avg_daily_demand;
"""
demand = pd.read_sql(demand_sql, engine)

inv_sql = """
SELECT product_id, qty_on_hand
FROM inventory_snapshots
WHERE dt = (SELECT MAX(dt) FROM inventory_snapshots);
"""
inventory = pd.read_sql(inv_sql, engine)

sup_sql = """
SELECT p.product_id, s.supplier_id, s.name AS supplier_name, s.lead_time_days, s.min_order_qty
FROM products p
JOIN suppliers s ON p.supplier_id = s.supplier_id;
"""
suppliers = pd.read_sql(sup_sql, engine)

# -------------------------------
# 4. Merge into one dataset
# -------------------------------
df = demand.merge(inventory, on="product_id", how="left") \
           .merge(suppliers, on="product_id", how="left")

# Fill missing values (if any product had no sales yet)
df["avg_daily_units"].fillna(0.5, inplace=True)
df["std_daily_units"].fillna(0.7, inplace=True)

# -------------------------------
# 5. Calculate Safety Stock & ROP
# -------------------------------
df["safety_stock"] = (z * df["std_daily_units"] * np.sqrt(df["lead_time_days"])).round()
df["reorder_point"] = (df["avg_daily_units"] * df["lead_time_days"] + df["safety_stock"]).round()

# -------------------------------
# 6. Suggested Order Quantity
# -------------------------------
df["below_rop"] = df["qty_on_hand"] < df["reorder_point"]
df["raw_order_qty"] = (df["reorder_point"] + df["avg_daily_units"]*REVIEW_PERIOD - df["qty_on_hand"]).clip(lower=0).round()
df["suggested_order_qty"] = np.where(
    df["below_rop"],
    np.maximum(df["raw_order_qty"], df["min_order_qty"]),
    0
).astype(int)

# -------------------------------
# 7. Save results
# -------------------------------
df_out = df[[
    "product_id", "supplier_id", "supplier_name",
    "qty_on_hand", "avg_daily_units", "std_daily_units",
    "lead_time_days", "safety_stock", "reorder_point",
    "below_rop", "suggested_order_qty"
]]

df_out.to_csv("data/processed/reorder_plan.csv", index=False)
print("✅ Reorder plan saved to data/processed/reorder_plan.csv")

print(df_out.head(10))
