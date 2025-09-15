import pandas as pd
from sqlalchemy import create_engine

# connection settings
USER = "root"
PASSWORD = ""   # empty since you’re using no password
HOST = "localhost"
PORT = "3306"
DB = "inventory_db"

# MySQL connection string
engine = create_engine(f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB}")

def load_table(csv_name, table_name, parse_dates=None):
    df = pd.read_csv(f"data/raw/{csv_name}.csv", parse_dates=parse_dates)
    df.to_sql(table_name, engine, if_exists="append", index=False)
    print(f"✅ Loaded {len(df)} rows into {table_name}")

if __name__ == "__main__":
    load_table("suppliers", "suppliers")
    load_table("products", "products")
    load_table("sales", "sales", parse_dates=["dt"])
    load_table("purchase_orders", "purchase_orders",
               parse_dates=["order_date","promised_date","received_date"])
    load_table("inventory_snapshots", "inventory_snapshots", parse_dates=["dt"])
