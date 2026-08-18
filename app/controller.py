import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dto import CreateDealRequest, SearchRequest
from app.service import DealService, IdempotencyConflict, InvalidCursor

router = APIRouter()


def get_service(db: Annotated[Session, Depends(get_db)]) -> DealService:
    return DealService(db)


@router.post("/deals/search")
def search(
    body: SearchRequest,
    service: Annotated[DealService, Depends(get_service)],
    idempotency_key: Annotated[str | None, Header()] = None,
):
    start = time.perf_counter()
    try:
        result = service.search(body, idempotency_key)
    except IdempotencyConflict:
        raise HTTPException(409, "Idempotency-Key reused with a different body")
    result["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
    return result


@router.post("/deals")
def add_deal(
    body: CreateDealRequest,
    service: Annotated[DealService, Depends(get_service)],
    idempotency_key: Annotated[str | None, Header()] = None,
):
    try:
        return service.add_deal(body, idempotency_key)
    except IdempotencyConflict:
        raise HTTPException(409, "Idempotency-Key reused with a different body")


@router.get("/deals/search/history")
def history(
    service: Annotated[DealService, Depends(get_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: str | None = None,
):
    try:
        return service.list_history(limit, cursor)
    except InvalidCursor:
        raise HTTPException(400, "invalid cursor")
