"""
DATABASE MODELS
----------------
Yeh define karta hai ki "User" table mein kya-kya store hoga.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    company_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_subscribed = Column(Boolean, default=False)
    subscription_plan = Column(String, nullable=True)        # "monthly" or "yearly"
    subscription_status = Column(String, nullable=True)      # "created" / "active" / "cancelled"
    razorpay_subscription_id = Column(String, nullable=True)