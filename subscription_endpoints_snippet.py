# ---------------------------------------------------------------------------
# SUBSCRIPTION / PAYMENT ENDPOINTS
# ---------------------------------------------------------------------------

class CreateSubscriptionRequest(BaseModel):
    plan: str  # "monthly" or "yearly"


@app.post("/create-subscription")
async def create_subscription_endpoint(
    payload: CreateSubscriptionRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.plan not in ("monthly", "yearly"):
        raise HTTPException(400, "Plan must be 'monthly' or 'yearly'")

    plan_id = MONTHLY_PLAN_ID if payload.plan == "monthly" else YEARLY_PLAN_ID
    total_count = 12 if payload.plan == "monthly" else 1

    subscription = create_subscription(plan_id, total_count=total_count)

    current_user.razorpay_subscription_id = subscription["id"]
    current_user.subscription_plan = payload.plan
    current_user.subscription_status = "created"
    db.commit()

    return {"subscription_id": subscription["id"], "key_id": RAZORPAY_KEY_ID}


class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str


@app.post("/verify-subscription-payment")
async def verify_subscription_payment(
    payload: VerifyPaymentRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    is_valid = verify_payment_signature(
        payload.razorpay_payment_id,
        payload.razorpay_subscription_id,
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