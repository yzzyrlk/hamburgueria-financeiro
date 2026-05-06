from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List
from ..core.db import get_db
from ..models.schemas import FinancialSummary, CashFlowDay
from ..services.reporting_service import financial_summary, cash_flow_daily

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary", response_model=FinancialSummary)
def get_summary(start: date, end: date, db: Session = Depends(get_db)):
    return financial_summary(db, start, end)


@router.get("/cash-flow", response_model=List[CashFlowDay])
def get_cash_flow(
    start: date | None = None, end: date | None = None,
    db: Session = Depends(get_db),
):
    end = end or date.today()
    start = start or (end - timedelta(days=30))
    return cash_flow_daily(db, start, end)
