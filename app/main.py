"""Entrypoint FastAPI."""
import logging
import os
from fastapi import FastAPI
from .routes import orders, transactions, reports
from .integrations import mercado_pago_routes  # webhook
from .core.bootstrap import apply_schema

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Hamburgueria Financeiro", version="1.0.0")

app.include_router(orders.router)
app.include_router(transactions.router)
app.include_router(reports.router)
app.include_router(mercado_pago_routes.router)


@app.on_event("startup")
def _startup():
    if os.getenv("AUTO_MIGRATE", "true").lower() == "true":
        try:
            apply_schema()
        except Exception:
            log.exception("Falha ao aplicar schema no startup")


@app.get("/")
def root():
    return {"app": "hamburgueria-financeiro", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"status": "ok"}
