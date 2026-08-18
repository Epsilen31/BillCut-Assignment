# Deal Search

Small FastAPI service. You send a brand and an amount, it returns the cheapest way to pay from a seeded SQLite catalog. If there is no deal for that brand, it suggests the credit card with the highest reward rate.

## Run

```bash
pip install -r requirements.txt
python -m app.main
```

Open http://127.0.0.1:8000/docs

```bash
python -m pytest
```

## Layout

Same idea as a typical Java API: controller → service → repository → entity. DTOs are the request bodies.

| Layer | File | Role |
|---|---|---|
| Controller | `app/controller.py` | HTTP routes only |
| DTO | `app/dto.py` | request validation (`SearchRequest`, `CreateDealRequest`) |
| Service | `app/service.py` | ranking, fallback, cache, idempotency |
| Repository | `app/repository.py` | SQLAlchemy queries |
| Entity | `app/entity.py` | tables |
| Ranking | `app/ranking.py` | effective-price math used by the service |

`app/main.py` wires FastAPI. `app/database.py` is the SQLite session. `app/seed.py` loads the JSON catalogs.

## API

`POST /deals/search` `{ "brand": "Amazon", "amount": 100 }`

Returns matching deals, cheapest first, plus `best_pick`. Unknown brand → `fallback: true` and a card.

`GET /deals/search/history?limit=20&cursor=`

Cursor pagination of past searches.

`POST /deals` adds a deal. Both write endpoints accept `Idempotency-Key` so a retry does not write twice. Same key + different body → 409.

## Data model

SQLite file `deals.db`, created on startup.

- **deals** — brand, title, source (`offer` / `coupon` / `cashback` / `card_reward`), discount_pct, reward_pct, optional fixed `price` (used for fares / prepaid plans)
- **cards** — name, reward_pct
- **search_history** — each search
- **idempotency_keys** — key, body hash, saved response

Two JSON files are loaded and merged: `data/deals_a.json` and `data/deals_b.json`. Same brand + title + source is treated as one deal. If both files have it, we keep the cheaper terms. Cards come from `data/cards.json`.

## Ranking

We do **not** sort by the headline %. We sort by money you actually keep in your pocket:

```
checkout = amount * (1 - discount_pct / 100)
if the deal has a fixed price, checkout = min(checkout, price)
effective_price = checkout * (1 - reward_pct / 100)
```

Lowest `effective_price` wins.

Example on a $100 Amazon order:

| Deal | Headline | What you pay |
|---|---|---|
| 10% coupon + 4% cashback | 10% | $90 then 4% back → **$86.40** (best) |
| 12% coupon | 12% | $88 |
| 10% coupon | 10% | $90 |

Delta is the other example: a $189 promo fare beats 10% off when the amount is $400, but 10% off wins when the amount is $150.

If no deal matches, pick the card with the highest `reward_pct` (Amazon Prime Visa at 5% in the seed).

Repeated identical searches are served from an in-memory dict. Each response also has `latency_ms` and header `X-Response-Time-Ms` (about 3–5 ms locally).
