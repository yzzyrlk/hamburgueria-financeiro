"""
Integração Mercado Pago — PIX.
Documentação: https://www.mercadopago.com.br/developers/pt/reference
"""
from __future__ import annotations
import uuid
import logging
from decimal import Decimal
from typing import Optional
import httpx
from ..core.config import settings

log = logging.getLogger(__name__)

MP_BASE = "https://api.mercadopago.com"


class MercadoPagoError(Exception):
    pass


def _headers(idempotency_key: Optional[str] = None) -> dict:
    h = {
        "Authorization": f"Bearer {settings.mp_access_token}",
        "Content-Type": "application/json",
    }
    if idempotency_key:
        h["X-Idempotency-Key"] = idempotency_key
    return h


def create_pix_payment(
    amount: Decimal,
    description: str,
    payer_email: str,
    external_reference: str,
    expires_in_minutes: int = 30,
) -> dict:
    """Cria pagamento PIX e retorna QR Code + ticket_url."""
    if not settings.mp_access_token:
        raise MercadoPagoError("MP_ACCESS_TOKEN não configurado")

    payload = {
        "transaction_amount": float(Decimal(amount).quantize(Decimal("0.01"))),
        "description": description,
        "payment_method_id": "pix",
        "payer": {"email": payer_email},
        "external_reference": external_reference,
        "date_of_expiration": None,
    }
    idem = f"pix-{external_reference}-{uuid.uuid4().hex[:8]}"

    try:
        with httpx.Client(timeout=15) as client:
            r = client.post(f"{MP_BASE}/v1/payments", json=payload, headers=_headers(idem))
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as e:
        log.error("MP PIX failed: %s", e)
        raise MercadoPagoError(str(e)) from e

    poi = data.get("point_of_interaction", {}).get("transaction_data", {})
    return {
        "id": data.get("id"),
        "status": data.get("status"),
        "qr_code": poi.get("qr_code"),
        "qr_code_base64": poi.get("qr_code_base64"),
        "ticket_url": poi.get("ticket_url"),
        "raw": data,
    }


def get_payment(payment_id: str) -> dict:
    with httpx.Client(timeout=15) as client:
        r = client.get(f"{MP_BASE}/v1/payments/{payment_id}", headers=_headers())
        r.raise_for_status()
        return r.json()
