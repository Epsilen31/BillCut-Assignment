def paid_at_checkout(amount, discount_pct=0, price=None):
    paid = amount * (1 - (discount_pct or 0) / 100)
    if price is not None:
        paid = min(paid, price)
    return round(max(paid, 0), 2)


def net_cost(amount, discount_pct=0, reward_pct=0, price=None):
    paid = paid_at_checkout(amount, discount_pct, price)
    return round(paid * (1 - (reward_pct or 0) / 100), 2)


def rank_deals(deals, amount):
    rows = []
    for deal in deals:
        paid = paid_at_checkout(amount, deal.discount_pct, deal.price)
        cost = round(paid * (1 - (deal.reward_pct or 0) / 100), 2)
        rows.append(
            {
                "id": deal.id,
                "brand": deal.brand,
                "title": deal.title,
                "price": paid,
                "source": deal.source,
                "discount_pct": deal.discount_pct,
                "reward_pct": deal.reward_pct,
                "effective_price": cost,
                "savings": round(amount - cost, 2),
            }
        )
    rows.sort(key=lambda row: row["effective_price"])
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
    return rows


def pick_best_card(cards, amount):
    if not cards:
        return None
    card = max(cards, key=lambda c: c.reward_pct)
    rewards = round(amount * card.reward_pct / 100, 2)
    return {
        "type": "card",
        "card_name": card.name,
        "title": f"Pay with {card.name} ({card.reward_pct:g}% back)",
        "source": "card_reward",
        "price": round(amount, 2),
        "discount_pct": 0,
        "reward_pct": card.reward_pct,
        "effective_price": round(amount - rewards, 2),
        "savings": rewards,
        "rank": 1,
    }
