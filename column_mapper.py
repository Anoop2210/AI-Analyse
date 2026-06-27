"""
COLUMN MAPPER
-------------
User ka CSV/Excel har business mein different column names ke saath aata hai.
Yeh file un columns ko automatically guess karti hai (fuzzy matching).
"""

from difflib import SequenceMatcher

SALES_COLUMN_ALIASES = {
    "date": ["date", "order_date", "transaction_date", "txn_date", "order date"],
    "revenue": ["revenue", "sales", "amount", "total", "price", "total_amount", "sale_amount"],
    "product": ["product", "item", "product_name", "sku", "item_name"],
    "region": ["region", "city", "state", "location", "area"],
    "quantity": ["qty", "quantity", "units", "unit_sold"],
    "customer": ["customer", "customer_name", "client", "buyer"],
}

MARKETING_COLUMN_ALIASES = {
    "date": ["date", "campaign_date", "report_date", "day"],
    "campaign": ["campaign", "campaign_name", "ad_campaign", "ad_set"],
    "spend": ["spend", "cost", "ad_spend", "budget_spent", "amount_spent"],
    "impressions": ["impressions", "views", "reach"],
    "clicks": ["clicks", "link_clicks", "total_clicks"],
    "conversions": ["conversions", "leads", "purchases", "results"],
    "revenue": ["revenue", "sales", "conversion_value", "purchase_value"],
}


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def suggest_column_mapping(columns: list[str], analyst_type: str = "sales") -> dict:
    """
    Returns: { "date": "order_date", "revenue": "Sales_Amt", ... }
    Best-guess match for each standard field based on the uploaded file's actual columns.
    """
    aliases_map = MARKETING_COLUMN_ALIASES if analyst_type == "marketing" else SALES_COLUMN_ALIASES

    mapping = {}
    for standard_field, aliases in aliases_map.items():
        best_match = None
        best_score = 0.0
        for col in columns:
            for alias in aliases:
                score = _similarity(col, alias)
                if score > best_score:
                    best_score = score
                    best_match = col
        if best_score > 0.6:
            mapping[standard_field] = best_match
        else:
            mapping[standard_field] = None
    return mapping