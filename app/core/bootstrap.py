"""
Bootstrap do banco. Roda o schema.sql automaticamente na primeira inicialização.
Idempotente — usa CREATE TABLE IF NOT EXISTS / DO $$ ... duplicate_object NULL.
"""
from __future__ import annotations
import logging
from pathlib import Path
from sqlalchemy import text
from .db import engine

log = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "sql" / "schema.sql"


def apply_schema() -> None:
    if not SCHEMA_PATH.exists():
        log.warning("schema.sql não encontrado em %s", SCHEMA_PATH)
        return
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.execute(text(sql))
    log.info("Schema aplicado a partir de %s", SCHEMA_PATH)
