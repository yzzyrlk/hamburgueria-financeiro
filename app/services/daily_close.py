"""
Fechamento diário — rodar via cron / scheduler às 04:30.
Liquida AR de PIX/dinheiro, gera resumo e envia no WhatsApp.
"""
from __future__ import annotations
import logging
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..models.models import AccountReceivable, CashFlow
from ..core.db import db_session
from ..core.time import to_business_date
from .reporting_service import financial_summary
from ..integrations.whatsapp import send_message, format_daily_summary

log = logging.getLogger(__name__)


def settle_due_receivables(db: Session, today: date) -> int:
    pendings = db.scalars(
        select(AccountReceivable).where(
            AccountReceivable.status == "pending",
            AccountReceivable.due_date <= today,
        )
    ).all()
    n = 0
    for ar in pendings:
        ar.status = "received"
        from datetime import datetime, timezone
        ar.received_at = datetime.now(timezone.utc)
        db.add(CashFlow(
            direction="in", amount=ar.amount,
            description=f"Liquidação AR {ar.id}",
            category="recebivel",
            business_date=today,
            ar_id=ar.id,
            transaction_id=ar.transaction_id,
        ))
        n += 1
    return n


def run_daily_close():
    today = to_business_date()
    yesterday = today - timedelta(days=1)
    with db_session() as db:
        n = settle_due_receivables(db, today)
        log.info("Liquidados %d recebíveis", n)
        summary = financial_summary(db, yesterday, yesterday).model_dump()
        # converte Decimal pra float só pra apresentação
        summary = {k: (float(v) if hasattr(v, "quantize") else v) for k, v in summary.items()}
        send_message(format_daily_summary(summary))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_daily_close()
