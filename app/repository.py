from sqlalchemy import func
from sqlalchemy.orm import Session

from app.entity import Card, Deal, IdempotencyKey, SearchHistory


class DealRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_brand(self, brand: str):
        return self.db.query(Deal).filter(func.lower(Deal.brand) == brand.lower()).all()

    def find_one(self, brand: str, title: str, source: str):
        return (
            self.db.query(Deal)
            .filter(
                func.lower(Deal.brand) == brand.lower(),
                func.lower(Deal.title) == title.lower(),
                Deal.source == source,
            )
            .first()
        )

    def add(self, deal: Deal) -> Deal:
        self.db.add(deal)
        self.db.commit()
        self.db.refresh(deal)
        return deal


class CardRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_all(self):
        return self.db.query(Card).all()


class HistoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, row: SearchHistory):
        self.db.add(row)
        self.db.commit()

    def list_page(self, limit: int, created_at=None, row_id=None):
        q = self.db.query(SearchHistory).order_by(
            SearchHistory.created_at.desc(),
            SearchHistory.id.desc(),
        )
        if created_at is not None and row_id is not None:
            q = q.filter(
                (SearchHistory.created_at < created_at)
                | ((SearchHistory.created_at == created_at) & (SearchHistory.id < row_id))
            )
        return q.limit(limit + 1).all()


class IdempotencyRepository:
    def __init__(self, db: Session):
        self.db = db

    def find(self, key: str):
        return self.db.query(IdempotencyKey).filter_by(key=key).first()

    def save(self, row: IdempotencyKey):
        self.db.add(row)
        self.db.commit()
