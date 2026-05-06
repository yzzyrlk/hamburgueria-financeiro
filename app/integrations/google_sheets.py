"""
Integração Google Sheets via gspread.
Espera credenciais de service account em GSHEETS_CREDENTIALS_JSON
(arquivo .json) e a planilha compartilhada com o e-mail da SA.
"""
from __future__ import annotations
import json
import logging
from decimal import Decimal
from typing import List, Optional
from datetime import datetime

from ..core.config import settings

log = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not settings.gsheets_credentials_json:
        raise RuntimeError("GSHEETS_CREDENTIALS_JSON não configurado")

    import gspread
    from google.oauth2.service_account import Credentials

    info = json.loads(settings.gsheets_credentials_json) \
        if settings.gsheets_credentials_json.strip().startswith("{") \
        else json.load(open(settings.gsheets_credentials_json))

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    _client = gspread.authorize(creds)
    return _client


def append_transaction(row: dict) -> bool:
    """
    row: dict com chaves esperadas:
        transaction_id, order_id, business_date, method, channel,
        gross, fees, net, status
    """
    try:
        gc = _get_client()
        sh = gc.open_by_key(settings.gsheets_spreadsheet_id)
        ws = sh.worksheet(settings.gsheets_worksheet)

        # Garante header
        if ws.row_count == 0 or not ws.acell("A1").value:
            ws.append_row([
                "transaction_id", "order_id", "business_date", "datetime",
                "method", "channel", "gross", "fees", "net", "status",
            ])

        ws.append_row([
            row.get("transaction_id"),
            row.get("order_id"),
            str(row.get("business_date")),
            row.get("datetime") or datetime.utcnow().isoformat(),
            row.get("method"),
            row.get("channel"),
            float(Decimal(str(row.get("gross", 0)))),
            float(Decimal(str(row.get("fees", 0)))),
            float(Decimal(str(row.get("net", 0)))),
            row.get("status"),
        ], value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        log.exception("Sheets append failed: %s", e)
        return False
