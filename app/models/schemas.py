"""Schemas Pydantic (entrada e saída da API)."""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


# --- Itens de pedido --------------------------------------------------
class OrderItemIn(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_price: Optional[Decimal] = None  # se None, usa product.price


class OrderIn(BaseModel):
    external_id: Optional[str] = None
    channel: Literal["balcao", "delivery_proprio", "ifood", "rappi", "99food", "outros"] = "balcao"
    customer_name: Optional[str] = None
    discount: Decimal = Decimal("0")
    delivery_fee: Decimal = Decimal("0")
    notes: Optional[str] = None
    items: List[OrderItemIn]


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    external_id: Optional[str]
    channel: str
    status: str
    subtotal: Decimal
    discount: Decimal
    delivery_fee: Decimal
    total: Decimal
    cmv_total: Decimal
    business_date: date
    created_at: datetime


# --- Transações -------------------------------------------------------
class FeeIn(BaseModel):
    fee_type: Literal["mdr", "marketplace", "antecipacao", "imposto", "outro"]
    description: Optional[str] = None
    rate: Optional[Decimal] = None
    amount: Decimal = Field(ge=0)


class TransactionIn(BaseModel):
    order_id: UUID
    external_id: Optional[str] = None
    method: Literal["dinheiro", "pix", "debito", "credito", "vale_refeicao", "marketplace", "outro"]
    gross_amount: Decimal = Field(gt=0)
    installments: int = 1
    fees: Optional[List[FeeIn]] = None  # se None: calcula automático
    paid_at: Optional[datetime] = None
    raw_payload: Optional[dict] = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    order_id: UUID
    external_id: Optional[str]
    method: str
    status: str
    gross_amount: Decimal
    fees_amount: Decimal
    net_amount: Decimal
    installments: int
    business_date: date
    paid_at: Optional[datetime]


# --- Resumo financeiro / fluxo ---------------------------------------
class FinancialSummary(BaseModel):
    period_start: date
    period_end: date
    gross_revenue: Decimal
    deductions: Decimal
    net_revenue: Decimal
    cmv: Decimal
    gross_profit: Decimal
    fixed_expenses: Decimal
    variable_expenses: Decimal
    net_profit: Decimal
    cmv_pct: Decimal
    gross_margin_pct: Decimal
    net_margin_pct: Decimal
    orders_count: int
    average_ticket: Decimal


class CashFlowDay(BaseModel):
    business_date: date
    inflow: Decimal
    outflow: Decimal
    net: Decimal
    accumulated: Decimal
