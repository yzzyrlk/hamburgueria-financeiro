from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..core.db import get_db
from ..models.schemas import OrderIn, OrderOut
from ..services.order_service import create_order

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=201)
def post_order(payload: OrderIn, db: Session = Depends(get_db)):
    try:
        order = create_order(db, payload)
        return order
    except ValueError as e:
        raise HTTPException(400, str(e))
