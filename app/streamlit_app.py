import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from scipy.stats import norm

# -------------------------------
# DB Connection
# -------------------------------
USER = "root"
PASSWORD = ""   # no password
HOST = "localhost"
PORT = "3306"
DB = "inventory_db"

engine = create_engine(f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB}")

# -------------------------------
# Load Data
# -------------------------------
@st.cache_data
def load_reorder_plan():
    query = """
    SELECT p.product_id, p.product_name, p.category, s.name AS supplier_name,
           i.qty_on_hand, d.avg_daily_units, d.std_daily_units, s.lead_time_days
    FROM v_avg_daily_demand d
    JOIN products p ON d.product_id = p.product_id
    JOIN suppliers s ON p.supplier_id = s.supplier_id
    JOIN inventory_snapshots i ON p.product_id = i.product_id
    WHERE i.dt = (SELECT MAX(dt) FROM inventory_snapshots);
    """
    return pd.read_sql(query, engine)

df = load_reorder_plan()

# -------------------------------
# Sidebar Controls
# -------------------------------
st.sidebar.header("📊 Parameters")
service_level = st.sidebar.slider("Service Level (%)", 50, 99, 95) / 100
review_period = st.sidebar.slider("Review Period (days)", 1, 30, 7)
category_filter = st.sidebar.multiselect(
    "Filter by Category", options=df["category"].unique(), default=list(df["category"].unique())
)

z = norm.ppf(service_level)

# -------------------------------
# Calculations
# -------------------------------
df = df[df["category"].isin(category_filter)]

df["safety_stock"] = (z * df["std_daily_units"] * (df["lead_time_days"] ** 0.5)).round()
df["reorder_point"] = (df["avg_daily_units"] * df["lead_time_days"] + df["safety_stock"]).round()
df["below_rop"] = df["qty_on_hand"] < df["reorder_point"]
df["suggested_order_qty"] = (
    (df["reorder_point"] + df["avg_daily_units"] * review_period - df["qty_on_hand"])
    .clip(lower=0)
    .round()
)

# -------------------------------
# Dashboard
# -------------------------------
st.title("🍸 Bar Inventory Reorder Dashboard")

st.markdown(
    "Interactive dashboard for managing **bar inventory**. "
    "Adjust service level and review period in the sidebar to see reorder recommendations."
)

# KPI cards
col1, col2, col3 = st.columns(3)
col1.metric("Products", len(df))
col2.metric("Suppliers", df["supplier_name"].nunique())
col3.metric("Need Reorder", df["below_rop"].sum())

# Data table
st.subheader("🔎 Reorder Plan")
st.dataframe(
    df[[
        "product_id", "product_name", "category", "supplier_name",
        "qty_on_hand", "avg_daily_units", "lead_time_days",
        "safety_stock", "reorder_point", "below_rop", "suggested_order_qty"
    ]],
    use_container_width=True
)

# Filtered table
st.subheader("📉 Products Below Reorder Point")
st.dataframe(df[df["below_rop"] == True][[
    "product_id", "product_name", "category", "supplier_name",
    "qty_on_hand", "reorder_point", "suggested_order_qty"
]])

# Chart
st.subheader("📊 Inventory vs Reorder Point")
st.bar_chart(df.set_index("product_name")[["qty_on_hand", "reorder_point"]])
