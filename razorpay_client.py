"""
RAZORPAY CLIENT
----------------
Yeh file Razorpay one-time payment order create karti hai aur signature verify karti hai.
"""

import os
import hmac
import hashlib
from dotenv import load_dotenv
load_dotenv()

import razorpay

client = razorpay.Client(
    auth=(os.environ.get("RAZORPAY_KEY_ID"), os.environ.get("RAZORPAY_KEY_SECRET"))
)


def create_order(amount_rupees: int, receipt: str) -> dict:
    """Razorpay order create karta hai. amount_rupees ko paise mein convert karna padta hai (x100)."""
    order = client.order.create({
        "amount": amount_rupees * 100,
        "currency": "INR",
        "receipt": receipt,
        "payment_capture": 1,
    })
    return order


def verify_payment_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
    """Razorpay se aaye payment signature ko verify karta hai (security check)."""
    secret = os.environ.get("RAZORPAY_KEY_SECRET").encode()
    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    generated_signature = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(generated_signature, razorpay_signature)