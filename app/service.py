import base64
import hashlib
import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.dto import CreateDealRequest, SearchRequest
from app.entity import Deal, IdempotencyKey, SearchHistory
from app.ranking import pick_best_card, rank_deals
from app.repository import CardRepository, DealRepository, HistoryRepository, IdempotencyRepository

cache = {}


class IdempotencyConflict(Exception):
    pass


class InvalidCursor(Exception):
    pass


class DealService:
    def __init__(self, db: Session):
        self.deals = DealRepository(db)
        self.cards = CardRepository(db)
        self.history = HistoryRepository(db)
        self.keys = IdempotencyRepository(db)

    def search(self, req: SearchRequest, idempotency_key: str | None = None) -> dict:
        data = req.model_dump()
        saved = self._replay(idempotency_key, data)
        if saved is not None:
            saved["cached"] = True
            return saved

        cache_key = f"{req.brand.lower()}|{req.amount:.2f}"
        cached = cache.get(cache_key)
        if cached is not None:
            result = dict(cached)
            result["cached"] = True
        else:
            matches = self.deals.find_by_brand(req.brand)
            if matches:
                ranked = rank_deals(matches, req.amount)
                best = ranked[0]
            else:
                ranked = []
                best = pick_best_card(self.cards.find_all(), req.amount)
            result = {
                "brand": req.brand,
                "amount": req.amount,
                "deals": ranked,
                "best_pick": best,
                "fallback": not matches,
                "cached": False,
            }
            cache[cache_key] = result

        self.history.add(
            SearchHistory(
                brand=req.brand,
                amount=req.amount,
                match_count=len(result["deals"]),
                used_fallback=result["fallback"],
                best_pick_title=(result["best_pick"] or {}).get("title"),
            )
        )

        result = dict(result)
        self._save_replay(idempotency_key, data, result)
        return result

    def add_deal(self, req: CreateDealRequest, idempotency_key: str | None = None) -> dict:
        data = req.model_dump()
        saved = self._replay(idempotency_key, data)
        if saved is not None:
            return saved

        existing = self.deals.find_one(req.brand, req.title, req.source)
        if existing:
            result = {"created": False, "deal": _deal_dict(existing)}
        else:
            deal = self.deals.add(
                Deal(
                    brand=req.brand,
                    title=req.title,
                    source=req.source,
                    discount_pct=req.discount_pct,
                    reward_pct=req.reward_pct,
                    price=req.price,
                )
            )
            cache.clear()
            result = {"created": True, "deal": _deal_dict(deal)}

        self._save_replay(idempotency_key, data, result)
        return result

    def list_history(self, limit: int, cursor: str | None = None) -> dict:
        created_at = row_id = None
        if cursor:
            created_at, row_id = _decode_cursor(cursor)

        rows = self.history.list_page(limit, created_at, row_id)
        has_more = len(rows) > limit
        page = rows[:limit]
        return {
            "items": [
                {
                    "id": row.id,
                    "brand": row.brand,
                    "amount": row.amount,
                    "match_count": row.match_count,
                    "used_fallback": row.used_fallback,
                    "best_pick_title": row.best_pick_title,
                    "created_at": row.created_at.isoformat(),
                }
                for row in page
            ],
            "next_cursor": _encode_cursor(page[-1]) if has_more and page else None,
            "has_more": has_more,
        }

    def _replay(self, key: str | None, data: dict):
        if not key:
            return None
        row = self.keys.find(key)
        if not row:
            return None
        if row.body_hash != _body_hash(data):
            raise IdempotencyConflict()
        return json.loads(row.response_json)

    def _save_replay(self, key: str | None, data: dict, result: dict):
        if not key:
            return
        self.keys.save(
            IdempotencyKey(
                key=key,
                body_hash=_body_hash(data),
                response_json=json.dumps(result),
            )
        )


def _deal_dict(deal: Deal) -> dict:
    return {
        "id": deal.id,
        "brand": deal.brand,
        "title": deal.title,
        "price": deal.price,
        "source": deal.source,
        "discount_pct": deal.discount_pct,
        "reward_pct": deal.reward_pct,
    }


def _body_hash(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _encode_cursor(row: SearchHistory) -> str:
    raw = f"{row.created_at.isoformat()}|{row.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str):
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        stamp, row_id = raw.rsplit("|", 1)
        return datetime.fromisoformat(stamp), int(row_id)
    except ValueError:
        raise InvalidCursor()
