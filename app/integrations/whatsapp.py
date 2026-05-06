"""
Integração WhatsApp — abstrai provider.
Default: Z-API (https://z-api.io). Trocar provider ajustando WHATSAPP_PROVIDER.
"""
from __future__ import annotations
import logging
import httpx
from ..core.config import settings

log = logging.getLogger(__name__)


class WhatsAppError(Exception):
    pass


def _send_zapi(to: str, message: str) -> dict:
    if not (settings.whatsapp_token and settings.whatsapp_instance):
        raise WhatsAppError("WHATSAPP_TOKEN/INSTANCE não configurados")
    url = f"https://api.z-api.io/instances/{settings.whatsapp_instance}/token/{settings.whatsapp_token}/send-text"
    with httpx.Client(timeout=15) as client:
        r = client.post(url, json={"phone": to, "message": message})
        r.raise_for_status()
        return r.json()


def send_message(message: str, to: str | None = None) -> bool:
    to = to or settings.whatsapp_to
    if not to:
        log.warning("WhatsApp 'to' não configurado; mensagem ignorada")
        return False
    try:
        if settings.whatsapp_provider == "zapi":
            _send_zapi(to, message)
        else:
            log.warning("Provider %s não implementado", settings.whatsapp_provider)
            return False
        return True
    except Exception as e:
        log.exception("WhatsApp send failed: %s", e)
        return False


def format_daily_summary(summary: dict) -> str:
    """summary é o dict do FinancialSummary (já em Decimal/float)."""
    return (
        f"*Resumo do dia* — {summary['period_end']}\n"
        f"Faturamento bruto: R$ {summary['gross_revenue']:.2f}\n"
        f"Deduções (taxas): R$ {summary['deductions']:.2f}\n"
        f"Receita líquida: R$ {summary['net_revenue']:.2f}\n"
        f"CMV: R$ {summary['cmv']:.2f}  ({float(summary['cmv_pct'])*100:.1f}%)\n"
        f"Lucro bruto: R$ {summary['gross_profit']:.2f}\n"
        f"Lucro líquido: R$ {summary['net_profit']:.2f}\n"
        f"Pedidos: {summary['orders_count']} | Ticket médio: R$ {summary['average_ticket']:.2f}"
    )
