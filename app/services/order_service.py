"""Lógica de criação de pedidos."""
from __future__ import annotations
from decimal import Decimal
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..models.models import Order, OrderItem, Product, ProductRecipe
from ..models.schemas import OrderIn
from ..core.time import to_business_date
from .pricing import compute_unit_cmv


def create_order(db: Session, payload: OrderIn) -> Order:
    # Idempotência: se external_id já existe, retorna o mesmo
    if payload.external_id:
        existing = db.scalar(select(Order).where(Order.external_id == payload.external_id))
        if existing:
            return existing

    items: List[OrderItem] = []
    subtotal = Decimal("0")
    cmv_total = Decimal("0")

    for item in payload.items:
        product = db.get(Product, item.product_id)
        if not product or not product.active:
            raise ValueError(f"Produto inválido: {item.product_id}")

        unit_price = item.unit_price if item.unit_price is not None else product.price
        unit_cmv = compute_unit_cmv(db, product.id)
        line_total = (unit_price * item.quantity).quantize(Decimal("0.01"))
        line_cmv = (unit_cmv * item.quantity).quantize(Decimal("0.01"))

        items.append(OrderItem(
            product_id=product.id,
            quantity=item.quantity,
            unit_price=unit_price,
            unit_cmv=unit_cmv,
            total_price=line_total,
            total_cmv=line_cmv,
        ))
        subtotal += line_total
        cmv_total += line_cmv

    total = (subtotal - payload.discount + payload.delivery_fee).quantize(Decimal("0.01"))

    order = Order(
        external_id=payload.external_id,
        channel=payload.channel,
        status="open",
        customer_name=payload.customer_name,
        subtotal=subtotal,
        discount=payload.discount,
        delivery_fee=payload.delivery_fee,
        total=total,
        cmv_total=cmv_total,
        notes=payload.notes,
        business_date=to_business_date(),
        items=items,
    )
    db.add(order)
    db.flush()

    # Baixa de estoque (snapshot já foi feito; aqui debita para controle)
    for it in order.items:
        recipes = db.scalars(
            select(ProductRecipe).where(ProductRecipe.product_id == it.product_id)
        ).all()
        for r in recipes:
            r.ingredient.stock_qty = (r.ingredient.stock_qty or Decimal("0")) - (r.quantity * it.quantity)

    db.commit()
    db.refresh(order)
    return order
