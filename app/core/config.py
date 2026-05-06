"""Configuração central. Lê variáveis de ambiente."""
from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # App
    app_name: str = os.getenv("APP_NAME", "hamburgueria-financeiro")
    env: str = os.getenv("ENV", "dev")
    timezone: str = os.getenv("TZ_APP", "America/Sao_Paulo")
    business_day_cutoff_hour: int = int(os.getenv("BUSINESS_DAY_CUTOFF", "4"))  # vira o dia às 04h

    # Banco
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/hamburgueria",
    )

    # Mercado Pago
    mp_access_token: str = os.getenv("MP_ACCESS_TOKEN", "")
    mp_webhook_secret: str = os.getenv("MP_WEBHOOK_SECRET", "")

    # Google Sheets
    gsheets_credentials_json: str = os.getenv("GSHEETS_CREDENTIALS_JSON", "")
    gsheets_spreadsheet_id: str = os.getenv("GSHEETS_SPREADSHEET_ID", "")
    gsheets_worksheet: str = os.getenv("GSHEETS_WORKSHEET", "transacoes")

    # WhatsApp (Z-API / Twilio / Meta Cloud API — abstraído)
    whatsapp_provider: str = os.getenv("WHATSAPP_PROVIDER", "zapi")
    whatsapp_token: str = os.getenv("WHATSAPP_TOKEN", "")
    whatsapp_instance: str = os.getenv("WHATSAPP_INSTANCE", "")
    whatsapp_to: str = os.getenv("WHATSAPP_TO", "")  # número do dono

    # Taxas padrão (fallback caso gateway não retorne)
    default_credit_rate: str = os.getenv("DEFAULT_CREDIT_RATE", "0.0399")
    default_debit_rate: str = os.getenv("DEFAULT_DEBIT_RATE", "0.0199")
    default_pix_rate: str = os.getenv("DEFAULT_PIX_RATE", "0.0099")
    default_ifood_rate: str = os.getenv("DEFAULT_IFOOD_RATE", "0.23")


settings = Settings()
