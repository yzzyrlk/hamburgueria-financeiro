"""Registro de pagamentos e taxas."""
from __future__ import annotations
from datetime import timedelta
from decimal import Decimal
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..models.models import Transaction, TransactionFee, Order, AccountReceivable, CashFlow
from ..models.schemas import TransactionIn, FeeIn
from ..core.config import settings
from ..core.time import to_business_date, now_utc

D2 = Decimal("0.01")


def _default_fees(method: str, gross: Decimal, channel: str) -> List[FeeIn]:
    fees: List[FeeIn] = []
    if channel in ("ifood", "rappi", "99food"):
        rate = Decimal(settings.default_ifood_rate)
        fees.append(FeeIn(fee_type="marketplace", description=f"Marketplace {channel}",
                          rate=rate, amount=(gross * rate).quantize(D2)))
        return fees
    if method == "credito":
        rate = Decimal(settings.default_credit_rate)
        fees.append(FeeIn(fee_type="mdr", description="MDR Crédito", rate=rate,
                          amount=(gross * rate).quantize(D2)))
    elif method == "debito":
        rate = Decimal(settings.default_debit_rate)
        fees.append(FeeIn(fee_type="mdr", description="MDR Débito", rate=rate,
                          amount=(gross * rate).quantize(D2)))
    elif method == "pix":
        rate = Decimal(settings.default_pix_rate)
        fees.append(FeeIn(fee_type="mdr", description="PIX gateway", rate=rate,
                          amount=(gross * rate).quantize(D2)))
    return fees


def _settlement_due_date(method: str, channel: str):
    today = to_business_date()
    if channel in ("ifood", "rappi", "99food"):
        return today + timedelta(days=30)
    if method in ("dinheiro", "pix"):
        return today
    if method == "debito":
        return today + timedelta(days=1)
    if method == "credito":
        return today + timedelta(days=30)
    return today


def register_transaction(db: Session, payload: TransactionIn) -> Transaction:
    # Idempotência por external_id
    if payload.external_id:
        existing = db.scalar(select(Transaction).where(Transaction.external_id == payload.external_id))
        if existing:
            return existing

    order = db.get(Order, payload.order_id)
    if not order:
        raise ValueError("Order not found")

    fees = payload.fees or _default_fees(payload.method, payload.gross_amount, order.channel)
    fees_total = sum((f.amount for f in fees), Decimal("0")).quantize(D2)
    net = (payload.gross_amount - fees_total).quantize(D2)

    tx = Transaction(
        order_id=order.id,
        external_id=payload.external_id,
        method=payload.method,
        status="approved",
        gross_amount=payload.gross_amount,
        fees_amount=fees_total,
        net_amount=net,
        installments=payload.installments,
        paid_at=payload.paid_at or now_utc(),
        business_date=to_business_date(),
        raw_payload=payload.raw_payload,
        fees=[TransactionFee(
            fee_type=f.fee_type, description=f.description, rate=f.rate, amount=f.amount
        ) for f in fees],
    )
    db.add(tx)

    # Order paga (se quitar o total)
    paid_total = sum((t.gross_amount for t in order.transactions), Decimal("0")) + payload.gross_amount
    if paid_total >= order.total:
        order.status = "paid"

    db.flush()

    # Contas a receber: para dinheiro/PIX já entra direto no fluxo
    due = _settlement_due_date(payload.method, order.channel)
    if payload.method in ("dinheiro", "pix") and order.channel == "balcao":
        db.add(CashFlow(
            direction="in",
            amount=net,
            description=f"Recebimento {payload.method} pedido {order.id}",
            category="venda",
            business_date=to_business_date(),
            transaction_id=tx.id,
        ))
    else:
        db.add(AccountReceivable(
            transaction_id=tx.id,
            description=f"Recebível {payload.method} pedido {order.id}",
            amount=net,
            due_date=due,
            status="pending",
        ))

    db.commit()
    db.refresh(tx)
    return tx
