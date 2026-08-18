import json
from pathlib import Path

from app.entity import Card, Deal
from app.ranking import net_cost

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(name):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _deal_key(row):
    return (row["brand"].lower(), row["title"].lower(), row["source"].lower())


def merge_deals(source_a, source_b):
    merged = {}
    for row in source_a + source_b:
        key = _deal_key(row)
        if key not in merged:
            merged[key] = row
            continue
        old = merged[key]
        old_cost = net_cost(100, old.get("discount_pct"), old.get("reward_pct"), old.get("price"))
        new_cost = net_cost(100, row.get("discount_pct"), row.get("reward_pct"), row.get("price"))
        if new_cost < old_cost:
            merged[key] = row
    return list(merged.values())


def seed(db):
    if db.query(Deal).first():
        return

    for row in merge_deals(_load("deals_a.json"), _load("deals_b.json")):
        db.add(
            Deal(
                brand=row["brand"],
                title=row["title"],
                source=row["source"],
                discount_pct=row.get("discount_pct") or 0,
                reward_pct=row.get("reward_pct") or 0,
                price=row.get("price"),
            )
        )

    for row in _load("cards.json"):
        db.add(Card(name=row["name"], reward_pct=row["reward_pct"]))

    db.commit()
