from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    brand: str = Field(min_length=1, max_length=80)
    amount: float = Field(gt=0, le=1_000_000)

    @field_validator("brand")
    @classmethod
    def clean_brand(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("brand cannot be empty")
        return v


class CreateDealRequest(BaseModel):
    brand: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    source: str
    discount_pct: float = Field(default=0, ge=0, le=100)
    reward_pct: float = Field(default=0, ge=0, le=100)
    price: float | None = Field(default=None, gt=0)

    @field_validator("brand", "title")
    @classmethod
    def clean_text(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("cannot be empty")
        return v

    @field_validator("source")
    @classmethod
    def clean_source(cls, v):
        allowed = {"offer", "coupon", "cashback", "card_reward"}
        if v not in allowed:
            raise ValueError(f"source must be one of {sorted(allowed)}")
        return v
