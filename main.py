"""
MAIN APP
--------
Yeh sabse main file hai. Yeh sab pieces ko jodti hai:
Login/Signup -> Payment -> Upload (Sales/Marketing) -> Column Mapping -> KPI Calculation -> Insights -> Chat
"""

import os
import io
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import engine, get_db, Base
import models
from auth import hash_password, verify_password, create_access_token, get_current_user

from kpi_engine import calculate_kpis
from marketing_kpi_engine import calculate_marketing_kpis
from column_mapper import suggest_column_mapping
from gemini_client import generate_insights, chat_with_data
from razorpay_client import create_order, verify_payment_signature

Base.metadata.create_all(bind=engine)

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
PLAN_PRICES = {"monthly": 49, "yearly": 400}

app = FastAPI(title="AI Sales Analyst API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Key = user's email, Value = {"df": ..., "kpis": ..., "type": "sales"/"marketing"}
USER_DATA = {}


def _read_file(file: UploadFile) -> pd.DataFrame:
    contents = file.file.read()
    if file.filename.endswith(".csv"):
        return pd.read_csv(io.BytesIO(contents))
    elif file.filename.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(contents))
    else:
        raise HTTPException(400, "Only CSV or Excel files are supported")


def require_subscription(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Sirf active subscription waale users ko aage jaane do."""
    if not current_user.is_subscribed:
        raise HTTPException(402, "Active subscription required. Please subscribe to continue.")
    return current_user


# ---------------------------------------------------------------------------
# AUTH ENDPOINTS
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    email: str
    password: str
    company_name: str | None = None


@app.post("/signup")
async def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(400, "An account with this email already exists")

    user = models.User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        company_name=payload.company_name,
    )
    db.add(user)
    db.commit()

    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(401, "Incorrect email or password")

    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/me")
async def get_me(current_user: models.User = Depends(get_current_user)):
    return {"email": current_user.email, "company_name": current_user.company_name}


# ---------------------------------------------------------------------------
# PAYMENT ENDPOINTS
# ---------------------------------------------------------------------------

class CreateOrderRequest(BaseModel):
    plan: str  # "monthly" or "yearly"


@app.post("/create-order")
async def create_order_endpoint(
    payload: CreateOrderRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.plan not in PLAN_PRICES:
        raise HTTPException(400, "Plan must be 'monthly' or 'yearly'")

    amount = PLAN_PRICES[payload.plan]
    order = create_order(amount, receipt=f"order_{current_user.id}_{payload.plan}")

    current_user.subscription_plan = payload.plan
    current_user.subscription_status = "order_created"
    db.commit()

    return {"order_id": order["id"], "amount": amount, "key_id": RAZORPAY_KEY_ID}


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@app.post("/verify-payment")
async def verify_payment(
    payload: VerifyPaymentRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    is_valid = verify_payment_signature(
        payload.razorpay_order_id,
        payload.razorpay_payment_id,
        payload.razorpay_signature,
    )
    if not is_valid:
        raise HTTPException(400, "Payment verification failed. Please try again.")

    current_user.is_subscribed = True
    current_user.subscription_status = "active"
    db.commit()

    return {"status": "success", "is_subscribed": True}


@app.get("/subscription-status")
async def subscription_status(current_user: models.User = Depends(get_current_user)):
    return {
        "is_subscribed": current_user.is_subscribed,
        "plan": current_user.subscription_plan,
        "status": current_user.subscription_status,
    }


# ---------------------------------------------------------------------------
# DATA ENDPOINTS (subscription required)
# ---------------------------------------------------------------------------

@app.post("/upload")
async def upload_file(
    analyst_type: str = Query("sales", regex="^(sales|marketing)$"),
    file: UploadFile = File(...),
    current_user: models.User = Depends(require_subscription),
):
    df = _read_file(file)
    mapping = suggest_column_mapping(list(df.columns), analyst_type=analyst_type)

    USER_DATA[current_user.email] = {"df": df, "kpis": None, "type": analyst_type}

    return {
        "analyst_type": analyst_type,
        "columns_found": list(df.columns),
        "suggested_mapping": mapping,
        "row_count": len(df),
        "preview": df.head(5).to_dict(orient="records"),
    }


class ConfirmMappingRequest(BaseModel):
    mapping: dict


@app.post("/confirm-mapping")
async def confirm_mapping(
    payload: ConfirmMappingRequest,
    current_user: models.User = Depends(require_subscription),
):
    user_record = USER_DATA.get(current_user.email)
    if not user_record or user_record["df"] is None:
        raise HTTPException(400, "No file uploaded yet")

    df = user_record["df"]
    analyst_type = user_record["type"]

    rename_map = {v: k for k, v in payload.mapping.items() if v}
    df = df.rename(columns=rename_map)

    if "date" not in df.columns:
        raise HTTPException(400, "Date column is required")

    if analyst_type == "marketing":
        if "spend" not in df.columns:
            raise HTTPException(400, "Spend column is required for marketing analysis")
        kpis = calculate_marketing_kpis(df)
    else:
        if "revenue" not in df.columns:
            raise HTTPException(400, "Revenue column is required for sales analysis")
        kpis = calculate_kpis(df)

    USER_DATA[current_user.email]["kpis"] = kpis

    return {"kpis": kpis, "analyst_type": analyst_type}


@app.post("/generate-insights")
async def get_insights(current_user: models.User = Depends(require_subscription)):
    user_record = USER_DATA.get(current_user.email)
    if not user_record or user_record["kpis"] is None:
        raise HTTPException(400, "No KPIs calculated yet. Upload and confirm mapping first.")

    insights = generate_insights(user_record["kpis"], analyst_type=user_record["type"])
    return insights


class ChatRequest(BaseModel):
    question: str


@app.post("/chat")
async def chat(
    payload: ChatRequest,
    current_user: models.User = Depends(require_subscription),
):
    user_record = USER_DATA.get(current_user.email)
    if not user_record or user_record["kpis"] is None:
        raise HTTPException(400, "No data available. Upload a file first.")

    answer = chat_with_data(user_record["kpis"], payload.question, analyst_type=user_record["type"])
    return {"answer": answer}


@app.get("/")
async def root():
    return {"message": "AI Sales Analyst API is running. Visit /docs to test it."}