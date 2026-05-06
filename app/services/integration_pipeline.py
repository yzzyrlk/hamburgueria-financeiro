"""
Pipeline disparado quando uma venda é confirmada.
Orquestra:
1. Order já salvo
2. Transaction registrada (já com transaction_fees)
3. Snapshot CMV em order
4. Atualização de fluxo de caixa / AR
5. Envio para Google Sheets
6. Alerta WhatsApp
"""
from __future__ import annotations
import logging
from uuid import UUID
from sqlalchemy.orm import Session
from ..models.models import Transaction, Order
from ..integrations.google_sheets import append_transaction
from ..integrations.whatsapp import send_message

log = logging.getLogger(__name__)


def on_payment_confirmed(db: Session, transaction_id: UUID) -> None:
    """Executa pós-confirmação de pagamento. Falhas em integrações
    NÃO devem reverter o pagamento — logamos e seguimos."""
    tx = db.get(Transaction, transaction_id)
    if not tx:
        log.warning("Transaction %s não encontrada", transaction_id)
        return
    order: Order = tx.order

    # 1) Google Sheets (best-effort)
    try:
        append_transaction({
            "transaction_id": str(tx.id),
            "order_id": str(order.id),
            "business_date": tx.business_date,
            "datetime": tx.paid_at.isoformat() if tx.paid_at else None,
            "method": tx.method,
            "channel": order.channel,
            "gross": tx.gross_amount,
            "fees": tx.fees_amount,
            "net": tx.net_amount,
            "status": tx.status,
        })
    except Exception:
        log.exception("Sheets push falhou")

    # 2) WhatsApp — alerta de venda alta (> R$ 200) ou marketplace
    try:
        if tx.gross_amount >= 200 or order.channel in ("ifood", "rappi", "99food"):
            send_message(
                f"Venda confirmada {order.channel} — R$ {float(tx.gross_amount):.2f} "
                f"({tx.method}). Líquido: R$ {float(tx.net_amount):.2f}."
            )
    except Exception:
        log.exception("WhatsApp falhou")
