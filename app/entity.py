from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.database import Base, utcnow


class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True)
    brand = Column(String, index=True)
    title = Column(String)
    source = Column(String)
    discount_pct = Column(Float, default=0)
    reward_pct = Column(Float, default=0)
    price = Column(Float, nullable=True)


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    reward_pct = Column(Float)


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True)
    brand = Column(String)
    amount = Column(Float)
    match_count = Column(Integer, default=0)
    used_fallback = Column(Boolean, default=False)
    best_pick_title = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow, index=True)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key = Column(String, primary_key=True)
    body_hash = Column(String)
    response_json = Column(Text)
