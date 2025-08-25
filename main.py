from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import uuid4
import os

# SQLAlchemy setup
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./goldapp.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# -----------------------------
# Database Models
# -----------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    purchases = relationship("Purchase", back_populates="user")


class Purchase(Base):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    txn_id = Column(String, unique=True, index=True)
    grams = Column(Float)
    inr_amount = Column(Float)
    price_per_gram = Column(Float)
    provider = Column(String, default="SimplifyMoney-DigitalGold")
    status = Column(String, default="SUCCESS")
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="purchases")


Base.metadata.create_all(bind=engine)

# -----------------------------
# FastAPI Setup
# -----------------------------
app = FastAPI(title="Simplify Money – Kuber-like Gold Flow", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Utility Functions
# -----------------------------
GOLD_PRICE_PER_GRAM_INR_DEFAULT = float(os.getenv("GOLD_PRICE_PER_GRAM_INR", 6500))

GOLD_KEYWORDS = {
    "gold", "24k", "24 karat", "22k", "sovereign gold bond", "sgb", "digital gold",
    "invest in gold", "gold price", "gold rate", "buy gold", "sell gold", "gold etf",
    "gold mutual fund", "gold returns", "gold inflation hedge", "gold taxation"
}

BUY_INTENT = {"buy", "purchase", "invest", "yes", "proceed", "confirm", "place order"}


def is_gold_related(message: str) -> bool:
    return any(kw in message.lower() for kw in GOLD_KEYWORDS)


def has_buy_intent(message: str) -> bool:
    return any(w in message.lower() for w in BUY_INTENT)


def get_effective_price_per_gram_inr() -> float:
    return GOLD_PRICE_PER_GRAM_INR_DEFAULT

# -----------------------------
# Schemas
# -----------------------------
class AdvisorRequest(BaseModel):
    message: str
    user_id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class AdvisorResponse(BaseModel):
    is_gold_related: bool
    response: str
    suggest_purchase: bool
    redirect_to_purchase: bool = False
    next_action: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None


class PurchaseRequest(BaseModel):
    user_id: int
    amount_in_inr: Optional[float] = Field(None, ge=1)
    grams: Optional[float] = Field(None, ge=0.01)


class PurchaseReceipt(BaseModel):
    success: bool
    message: str
    txn_id: str
    user_id: int
    grams: float
    inr_amount: float
    price_per_gram: float
    provider: str
    created_at: datetime

# -----------------------------
# Routes
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/price")
def price():
    return {
        "price_per_gram_inr": get_effective_price_per_gram_inr(),
        "source": "fixed_env_or_default"
    }


@app.post("/advisor", response_model=AdvisorResponse)
def advisor(req: AdvisorRequest):
    db = SessionLocal()
    try:
        user_id = req.user_id
        if user_id is None and (req.name or req.email or req.phone):
            u = User(name=req.name, email=req.email, phone=req.phone)
            db.add(u)
            db.commit()
            db.refresh(u)
            user_id = u.id
        elif user_id:
            u = db.get(User, user_id)
            if u is None:
                u = User(id=user_id)
                db.add(u)
                db.commit()

        if not is_gold_related(req.message):
            return AdvisorResponse(
                is_gold_related=False,
                response="I can help with many finance topics. Ask about gold for advice and digital gold purchase options.",
                suggest_purchase=False,
                user_id=user_id
            )

        facts = []
        if "price" in req.message.lower():
            facts.append(f"Indicative price: ₹{get_effective_price_per_gram_inr()} per gram.")
        else:
            facts.append("Gold is a safe-haven asset and can hedge against inflation.")

        nudge = "You can invest in gold via the Simplify Money app using **Digital Gold** — start with just ₹10."
        buy_intent = has_buy_intent(req.message)

        return AdvisorResponse(
            is_gold_related=True,
            response="\n".join(facts + [nudge]),
            suggest_purchase=True,
            redirect_to_purchase=buy_intent,
            next_action={
                "label": "Buy digital gold now",
                "endpoint": "/purchase",
                "method": "POST",
                "expected_body": {"user_id": user_id or "<your_user_id>", "amount_in_inr": 1000},
            },
            user_id=user_id
        )
    finally:
        db.close()


@app.post("/purchase", response_model=PurchaseReceipt)
def purchase(req: PurchaseRequest):
    if req.amount_in_inr is None and req.grams is None:
        raise HTTPException(status_code=400, detail="Provide either amount_in_inr or grams")

    db = SessionLocal()
    try:
        user = db.get(User, req.user_id)
        if user is None:
            user = User(id=req.user_id)
            db.add(user)
            db.commit()

        price_per_gram = get_effective_price_per_gram_inr()
        grams = req.amount_in_inr / price_per_gram if req.amount_in_inr else req.grams
        inr_amount = grams * price_per_gram

        txn_id = str(uuid4())
        purchase_entry = Purchase(
            user_id=user.id,
            txn_id=txn_id,
            grams=round(grams, 4),
            inr_amount=round(inr_amount, 2),
            price_per_gram=price_per_gram,
            provider="SimplifyMoney-DigitalGold",
            status="SUCCESS"
        )
        db.add(purchase_entry)
        db.commit()
        db.refresh(purchase_entry)

        return PurchaseReceipt(
            success=True,
            message="Digital gold purchase successful (demo).",
            txn_id=txn_id,
            user_id=user.id,
            grams=purchase_entry.grams,
            inr_amount=purchase_entry.inr_amount,
            price_per_gram=purchase_entry.price_per_gram,
            provider=purchase_entry.provider,
            created_at=purchase_entry.created_at
        )
    finally:
        db.close()


@app.get("/purchases/{user_id}")
def list_purchases(user_id: int):
    db = SessionLocal()
    try:
        purchases = db.query(Purchase).filter(Purchase.user_id == user_id).order_by(Purchase.created_at.desc()).all()
        return [
            {
                "txn_id": p.txn_id,
                "grams": p.grams,
                "inr_amount": p.inr_amount,
                "price_per_gram": p.price_per_gram,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
            }
            for p in purchases
        ]
    finally:
        db.close()
