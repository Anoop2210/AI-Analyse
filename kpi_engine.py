"""
KPI ENGINE
----------
Yeh file raw sales data (Pandas DataFrame) leke important business numbers
(KPIs) calculate karti hai. Isme koi AI use nahi hota - sirf math/Pandas.

Expected columns (after column mapping):
- date
- revenue
- product
- region
- quantity (optional)
- customer (optional)
"""

import pandas as pd
import numpy as np
from datetime import datetime


def _to_native(obj):
    """
    Converts numpy/pandas number types into plain Python types
    so they can be safely converted to JSON.
    """
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_to_native(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif pd.isna(obj):
        return None
    else:
        return obj


def calculate_kpis(df: pd.DataFrame) -> dict:
    df = df.copy()

    # Ensure correct types
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")
    df = df.dropna(subset=["date", "revenue"])

    kpis = {}

    # 1. Total Revenue
    kpis["total_revenue"] = round(float(df["revenue"].sum()), 2)

    # 2. Total Orders
    kpis["total_orders"] = int(len(df))

    # 3. Average Order Value
    kpis["average_order_value"] = round(
        float(df["revenue"].sum()) / len(df), 2
    ) if len(df) > 0 else 0

    # 4. Monthly Revenue Trend
    monthly = (
        df.groupby(df["date"].dt.to_period("M"))["revenue"]
        .sum()
        .reset_index()
    )
    monthly["date"] = monthly["date"].astype(str)
    kpis["monthly_revenue_trend"] = monthly.to_dict(orient="records")

    # 5. Month-over-month growth %
    if len(monthly) >= 2:
        last = monthly["revenue"].iloc[-1]
        prev = monthly["revenue"].iloc[-2]
        growth = ((last - prev) / prev * 100) if prev != 0 else 0
        kpis["mom_growth_percent"] = round(float(growth), 2)
    else:
        kpis["mom_growth_percent"] = None

    # 6. Top Products
    if "product" in df.columns:
        top_products = (
            df.groupby("product")["revenue"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
            .reset_index()
        )
        kpis["top_products"] = top_products.to_dict(orient="records")

    # 7. Region-wise Sales
    if "region" in df.columns:
        region_sales = (
            df.groupby("region")["revenue"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        kpis["region_wise_sales"] = region_sales.to_dict(orient="records")

    # 8. Top Customers (optional)
    if "customer" in df.columns:
        top_customers = (
            df.groupby("customer")["revenue"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
            .reset_index()
        )
        kpis["top_customers"] = top_customers.to_dict(orient="records")

    kpis["generated_at"] = datetime.utcnow().isoformat()

    # Final safety net: convert any remaining numpy types to native Python types
    return _to_native(kpis)