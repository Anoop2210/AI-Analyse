"""
MARKETING KPI ENGINE
---------------------
Yeh marketing/campaign data se important numbers calculate karta hai:
CTR, CPC, CPA, ROAS, Conversion Rate, etc.

Expected columns (after column mapping):
- date
- campaign
- spend
- impressions
- clicks
- conversions
- revenue (revenue generated from the campaign)
"""

import pandas as pd
import numpy as np
from datetime import datetime


def _to_native(obj):
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


def calculate_marketing_kpis(df: pd.DataFrame) -> dict:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for col in ["spend", "impressions", "clicks", "conversions", "revenue"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df = df.dropna(subset=["date"])

    kpis = {}

    total_spend = float(df["spend"].sum()) if "spend" in df.columns else 0
    total_clicks = float(df["clicks"].sum()) if "clicks" in df.columns else 0
    total_impressions = float(df["impressions"].sum()) if "impressions" in df.columns else 0
    total_conversions = float(df["conversions"].sum()) if "conversions" in df.columns else 0
    total_revenue = float(df["revenue"].sum()) if "revenue" in df.columns else 0

    kpis["total_spend"] = round(total_spend, 2)
    kpis["total_clicks"] = int(total_clicks)
    kpis["total_impressions"] = int(total_impressions)
    kpis["total_conversions"] = int(total_conversions)
    kpis["total_revenue"] = round(total_revenue, 2)

    # CTR = Clicks / Impressions
    kpis["ctr_percent"] = round((total_clicks / total_impressions * 100), 2) if total_impressions > 0 else None

    # CPC = Spend / Clicks
    kpis["cpc"] = round((total_spend / total_clicks), 2) if total_clicks > 0 else None

    # CPA = Spend / Conversions
    kpis["cpa"] = round((total_spend / total_conversions), 2) if total_conversions > 0 else None

    # Conversion Rate = Conversions / Clicks
    kpis["conversion_rate_percent"] = round((total_conversions / total_clicks * 100), 2) if total_clicks > 0 else None

    # ROAS = Revenue / Spend
    kpis["roas"] = round((total_revenue / total_spend), 2) if total_spend > 0 else None

    # ROI % = (Revenue - Spend) / Spend * 100
    kpis["roi_percent"] = round(((total_revenue - total_spend) / total_spend * 100), 2) if total_spend > 0 else None

    # Campaign-wise performance
    if "campaign" in df.columns:
        campaign_group = df.groupby("campaign").agg(
            spend=("spend", "sum") if "spend" in df.columns else ("date", "count"),
            clicks=("clicks", "sum") if "clicks" in df.columns else ("date", "count"),
            conversions=("conversions", "sum") if "conversions" in df.columns else ("date", "count"),
            revenue=("revenue", "sum") if "revenue" in df.columns else ("date", "count"),
        ).reset_index()

        campaign_group["roas"] = campaign_group.apply(
            lambda r: round(r["revenue"] / r["spend"], 2) if r["spend"] > 0 else None, axis=1
        )
        campaign_group = campaign_group.sort_values("roas", ascending=False, na_position="last")
        kpis["campaign_performance"] = campaign_group.to_dict(orient="records")

        # Best and worst performing campaigns by ROAS
        valid = campaign_group.dropna(subset=["roas"])
        if len(valid) > 0:
            kpis["best_campaign"] = valid.iloc[0]["campaign"]
            kpis["worst_campaign"] = valid.iloc[-1]["campaign"]

    # Monthly spend/revenue trend
    monthly = df.groupby(df["date"].dt.to_period("M")).agg(
        spend=("spend", "sum") if "spend" in df.columns else ("date", "count"),
        revenue=("revenue", "sum") if "revenue" in df.columns else ("date", "count"),
    ).reset_index()
    monthly["date"] = monthly["date"].astype(str)
    kpis["monthly_trend"] = monthly.to_dict(orient="records")

    kpis["generated_at"] = datetime.utcnow().isoformat()

    return _to_native(kpis)