from fastapi.testclient import TestClient

from app.main import app


def test_search_ranks_by_effective_price():
    with TestClient(app) as client:
        r = client.post("/deals/search", json={"brand": "Amazon", "amount": 100})
        assert r.status_code == 200
        data = r.json()
        assert data["fallback"] is False
        prices = [d["effective_price"] for d in data["deals"]]
        assert prices == sorted(prices)
        assert data["best_pick"]["title"] == data["deals"][0]["title"]
        assert data["best_pick"]["effective_price"] == 86.4


def test_unknown_brand_returns_best_card():
    with TestClient(app) as client:
        r = client.post("/deals/search", json={"brand": "UnknownShop", "amount": 100})
        assert r.status_code == 200
        data = r.json()
        assert data["fallback"] is True
        assert data["deals"] == []
        assert data["best_pick"]["card_name"] == "Amazon Prime Visa"
        assert data["best_pick"]["savings"] == 5


def test_bad_input_is_rejected():
    with TestClient(app) as client:
        assert client.post("/deals/search", json={"brand": "Amazon"}).status_code == 422
        assert client.post("/deals/search", json={"brand": "  ", "amount": 10}).status_code == 422
        assert client.post("/deals/search", json={"brand": "Amazon", "amount": 0}).status_code == 422


def test_idempotency_and_history():
    with TestClient(app) as client:
        headers = {"Idempotency-Key": "test-key-1"}
        body = {"brand": "Nike", "amount": 80}
        first = client.post("/deals/search", json=body, headers=headers)
        second = client.post("/deals/search", json=body, headers=headers)
        assert first.status_code == 200
        assert second.status_code == 200

        conflict = client.post(
            "/deals/search",
            json={"brand": "Nike", "amount": 40},
            headers=headers,
        )
        assert conflict.status_code == 409

        page = client.get("/deals/search/history", params={"limit": 2})
        assert page.status_code == 200
        assert "items" in page.json()
        assert "next_cursor" in page.json()
