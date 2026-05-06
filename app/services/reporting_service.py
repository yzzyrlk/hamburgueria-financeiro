"""Resumo financeiro e fluxo de caixa."""
from __future__ import annotations
from decimal import Decimal
from datetime import date, timedelta
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ..models.models import Order, Transaction, AccountPayable, CashFlow
from ..models.schemas import FinancialSummary, CashFlowDay
from ..services.finance import (
    pct, gross_profit, net_profit, contribution_margin, average_ticket,
)


D2 = Decimal("0.01")


def financial_summary(db: Session, start: date, end: date) -> FinancialSummary:
    # Receita bruta + deduções a partir das transactions aprovadas
    gross = db.scalar(select(func.coalesce(func.sum(Transaction.gross_amount), 0))
                      .where(Transaction.status == "approved",
                             Transaction.business_date.between(start, end))) or Decimal("0")
    fees = db.scalar(select(func.coalesce(func.sum(Transaction.fees_amount), 0))
                     .where(Transaction.status == "approved",
                            Transaction.business_date.between(start, end))) or Decimal("0")

    # CMV dos pedidos pagos
    cmv = db.scalar(select(func.coalesce(func.sum(Order.cmv_total), 0))
                    .where(Order.status == "paid",
                           Order.business_date.between(start, end))) or Decimal("0")

    # Despesas pagas no período (regime de caixa)
    fixed_exp = db.scalar(select(func.coalesce(func.sum(AccountPayable.amount), 0))
                          .where(AccountPayable.status == "paid",
                                 AccountPayable.is_fixed.is_(True),
                                 AccountPayable.paid_at.between(start, end + timedelta(days=1)))) or Decimal("0")
    var_exp = db.scalar(select(func.coalesce(func.sum(AccountPayable.amount), 0))
                        .where(AccountPayable.status == "paid",
                               AccountPayable.is_fixed.is_(False),
                               AccountPayable.paid_at.between(start, end + timedelta(days=1)))) or Decimal("0")

    orders_count = db.scalar(select(func.count(Order.id))
                             .where(Order.status == "paid",
                                    Order.business_date.between(start, end))) or 0

    gross = Decimal(gross); fees = Decimal(fees); cmv = Decimal(cmv)
    fixed_exp = Decimal(fixed_exp); var_exp = Decimal(var_exp)

    net_rev = (gross - fees).quantize(D2)
    gp = gross_profit(net_rev, cmv)
    np_ = net_profit(gp, fixed_exp, var_exp)
    ticket = average_ticket(gross, orders_count)

    return FinancialSummary(
        period_start=start, period_end=end,
        gross_revenue=gross, deductions=fees, net_revenue=net_rev,
        cmv=cmv, gross_profit=gp,
        fixed_expenses=fixed_exp, variable_expenses=var_exp,
        net_profit=np_,
        cmv_pct=pct(cmv, net_rev),
        gross_margin_pct=pct(gp, net_rev),
        net_margin_pct=pct(np_, net_rev),
        orders_count=orders_count,
        average_ticket=ticket,
    )


def cash_flow_daily(db: Session, start: date, end: date) -> List[CashFlowDay]:
    rows = db.execute(
        select(
            CashFlow.business_date,
            func.coalesce(func.sum(func.case((CashFlow.direction == "in", CashFlow.amount), else_=0)), 0).label("inflow"),
            func.coalesce(func.sum(func.case((CashFlow.direction == "out", CashFlow.amount), else_=0)), 0).label("outflow"),
        )
        .where(CashFlow.business_date.between(start, end))
        .group_by(CashFlow.business_date)
        .order_by(CashFlow.business_date)
    ).all()

    out: List[CashFlowDay] = []
    accumulated = Decimal("0")
    for r in rows:
        inflow = Decimal(r.inflow); outflow = Decimal(r.outflow)
        net = (inflow - outflow).quantize(D2)
        accumulated += net
        out.append(CashFlowDay(business_date=r.business_date, inflow=inflow,
                               outflow=outflow, net=net, accumulated=accumulated))
    return out
