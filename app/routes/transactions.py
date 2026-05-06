from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from datetime import date
from ..core.db import get_db
from ..models.models import Transaction
from ..models.schemas import TransactionIn, TransactionOut
from ..services.transaction_service import register_transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionOut, status_code=201)
def post_transaction(payload: TransactionIn, db: Session = Depends(get_db)):
    try:
        return register_transaction(db, payload)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("", response_model=List[TransactionOut])
def list_transactions(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    q = select(Transaction).order_by(Transaction.created_at.desc())
    if start:
        q = q.where(Transaction.business_date >= start)
    if end:
        q = q.where(Transaction.business_date <= end)
    return db.scalars(q.limit(500)).all()
