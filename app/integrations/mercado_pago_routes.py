"""Webhook do Mercado Pago + endpoint de criação de PIX."""
from __future__ import annotations
import hmac, hashlib, logging
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from uuid import UUID

from ..core.db import get_db
from ..core.config import settings
from ..models.schemas import TransactionIn
from ..services.transaction_service import register_transaction
from ..services.integration_pipeline import on_payment_confirmed
from .mercado_pago import create_pix_payment, get_payment, MercadoPagoError

log = logging.getLogger(__name__)
router = APIRouter(prefix="/mp", tags=["mercado-pago"])


class PixCreateIn(BaseModel):
    order_id: UUID
    amount: Decimal
    description: str
    payer_email: str


@router.post("/pix")
def create_pix(payload: PixCreateIn):
    try:
        return create_pix_payment(
            amount=payload.amount,
            description=payload.description,
            payer_email=payload.payer_email,
            external_reference=str(payload.order_id),
        )
    except MercadoPagoError as e:
        raise HTTPException(502, f"Mercado Pago: {e}")


def _verify_signature(raw_body: bytes, signature: str | None) -> bool:
    if not settings.mp_webhook_secret:
        return True  # ambiente sem secret configurado (dev)
    if not signature:
        return False
    expected = hmac.new(
        settings.mp_webhook_secret.encode(),
        raw_body, hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook")
async def webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_signature: Optional[str] = Header(default=None),
):
    raw = await request.body()
    if not _verify_signature(raw, x_signature):
        raise HTTPException(401, "invalid signature")

    body = await request.json()
    if body.get("type") != "payment":
        return {"ignored": True}

    payment_id = str(body.get("data", {}).get("id"))
    if not payment_id:
        raise HTTPException(400, "missing payment id")

    try:
        data = get_payment(payment_id)
    except MercadoPagoError as e:
        raise HTTPException(502, str(e))

    if data.get("status") != "approved":
        return {"status": data.get("status"), "skipped": True}

    order_id = data.get("external_reference")
    gross = Decimal(str(data.get("transaction_amount", 0)))
    fee_amt = Decimal(str(
        (data.get("fee_details") or [{}])[0].get("amount", 0)
        if data.get("fee_details") else 0
    ))

    payload = TransactionIn(
        order_id=UUID(order_id),
        external_id=f"mp:{payment_id}",  # idempotência
        method="pix",
        gross_amount=gross,
        installments=1,
        fees=[{"fee_type": "mdr", "description": "MP PIX", "amount": fee_amt}] if fee_amt else None,
        raw_payload=data,
    )
    tx = register_transaction(db, payload)

    # Pipeline: dispara Sheets + WhatsApp + atualiza fluxo
    try:
        on_payment_confirmed(db, tx.id)
    except Exception:
        log.exception("post-confirmation pipeline failed (non-fatal)")

    return {"ok": True, "transaction_id": str(tx.id)}
