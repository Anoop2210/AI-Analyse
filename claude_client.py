"""
CLAUDE CLIENT
-------------
Yeh file KPI numbers (JSON) ko Claude AI ko bhejti hai aur business insights
+ recommendations wapas leke aati hai.

IMPORTANT: Hum raw Excel/CSV kabhi Claude ko nahi bhejte - sirf calculated
KPI summary bhejte hain. Isse cost kam rehti hai aur response fast aata hai.
"""

import os
from dotenv import load_dotenv
load_dotenv()
import json
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SALES_SYSTEM_PROMPT = """You are an expert Sales analyst for a business analytics SaaS product.

You will be given a JSON object containing calculated sales KPIs.
Your job:
1. Write a short, plain-language summary (3-5 sentences) of how the business is performing.
2. Identify 2-3 specific problems or risks visible in the data.
3. Give 3 actionable, specific recommendations.

Rules:
- Only use the numbers given to you. Do not invent data.
- If a trend looks like correlation rather than proven causation, say so explicitly.
- Be direct and concise.
- Respond ONLY in valid JSON with this exact structure, no markdown, no preamble:
{
  "summary": "string",
  "problems": ["string", "string"],
  "recommendations": ["string", "string", "string"]
}
"""

MARKETING_SYSTEM_PROMPT = """You are an expert Marketing analyst for a business analytics SaaS product.

You will be given a JSON object containing calculated marketing/campaign KPIs
(CTR, CPC, CPA, ROAS, ROI, conversion rate, campaign-wise performance).
Your job:
1. Write a short, plain-language summary (3-5 sentences) of how marketing campaigns are performing overall.
2. Identify 2-3 specific problems (e.g. campaigns with poor ROAS, high CPA, low CTR).
3. Give 3 actionable, specific recommendations (e.g. shift budget from X to Y, pause underperforming campaign Z).

Rules:
- Only use the numbers given to you. Do not invent data.
- Name specific campaigns by their actual name from the data when relevant.
- Be direct and concise.
- Respond ONLY in valid JSON with this exact structure, no markdown, no preamble:
{
  "summary": "string",
  "problems": ["string", "string"],
  "recommendations": ["string", "string", "string"]
}
"""


def generate_insights(kpi_json: dict, analyst_type: str = "sales") -> dict:
    system_prompt = MARKETING_SYSTEM_PROMPT if analyst_type == "marketing" else SALES_SYSTEM_PROMPT

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Here is the KPI data:\n\n{json.dumps(kpi_json, default=str)}"
            }
        ],
    )

    raw_text = "".join(
        block.text for block in message.content if block.type == "text"
    )

    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "summary": raw_text,
            "problems": [],
            "recommendations": [],
        }


def chat_with_data(kpi_json: dict, user_question: str, analyst_type: str = "sales", history: list[dict] | None = None) -> str:
    history = history or []
    context_label = "marketing campaign" if analyst_type == "marketing" else "sales"

    messages = history + [
        {
            "role": "user",
            "content": (
                f"Business {context_label} KPI data:\n{json.dumps(kpi_json, default=str)}\n\n"
                f"User question: {user_question}\n\n"
                "Answer using only the data above. Be specific and concise."
            ),
        }
    ]

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=messages,
    )

    return "".join(block.text for block in message.content if block.type == "text")