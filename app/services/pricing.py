"""Cálculo de CMV unitário (ficha técnica)."""
from __future__ import annotations
from decimal import Decimal
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..models.models import ProductRecipe


def compute_unit_cmv(db: Session, product_id: UUID) -> Decimal:
    """CMV unitário = Σ (qtd * unit_cost * (1 + loss_pct))."""
    recipes = db.scalars(
        select(ProductRecipe).where(ProductRecipe.product_id == product_id)
    ).all()
    total = Decimal("0")
    for r in recipes:
        ing = r.ingredient
        loss = Decimal(ing.loss_pct or 0)
        cost = Decimal(ing.unit_cost or 0)
        total += (r.quantity * cost) * (Decimal("1") + loss)
    return total.quantize(Decimal("0.01"))
