"""
Regras financeiras puras — sem dependência de DB ou framework.
Todas em Decimal; arredondamento bancário (HALF_EVEN) e quantize 2 casas.
"""
from __future__ import annotations
from decimal import Decimal, getcontext, ROUND_HALF_EVEN
from typing import Iterable, Mapping

getcontext().rounding = ROUND_HALF_EVEN
D2 = Decimal("0.01")
D4 = Decimal("0.0001")
ZERO = Decimal("0")


def q2(x: Decimal | int | float) -> Decimal:
    return Decimal(x).quantize(D2)


def pct(part: Decimal, whole: Decimal) -> Decimal:
    """Percentual com 4 casas decimais (multiplicar por 100 para apresentar)."""
    if not whole or whole == 0:
        return ZERO
    return (Decimal(part) / Decimal(whole)).quantize(D4)


# 1) Receita líquida ----------------------------------------------------
def net_revenue(gross: Decimal, fees: Iterable[Decimal] | Decimal) -> Decimal:
    """Receita líquida = Bruta − Σ taxas/deduções."""
    if isinstance(fees, Decimal):
        total_fees = fees
    else:
        total_fees = sum((Decimal(f) for f in fees), ZERO)
    return q2(Decimal(gross) - total_fees)


# 2) CMV pela ficha técnica --------------------------------------------
def cmv_from_recipe(recipe: Iterable[Mapping]) -> Decimal:
    """
    recipe: iterável de dicts {quantity, unit_cost, loss_pct}.
    Retorna CMV unitário do produto.
    """
    total = ZERO
    for r in recipe:
        qty = Decimal(r["quantity"])
        cost = Decimal(r["unit_cost"])
        loss = Decimal(r.get("loss_pct", 0))
        total += (qty * cost) * (Decimal("1") + loss)
    return q2(total)


def cmv_total(items: Iterable[Mapping]) -> Decimal:
    """items: [{unit_cmv, quantity}] -> CMV total."""
    return q2(sum((Decimal(i["unit_cmv"]) * Decimal(i["quantity"]) for i in items), ZERO))


# 3) Lucro bruto -------------------------------------------------------
def gross_profit(net_rev: Decimal, cmv: Decimal) -> Decimal:
    return q2(Decimal(net_rev) - Decimal(cmv))


# 4) Margem de contribuição -------------------------------------------
def contribution_margin(net_rev: Decimal, cmv: Decimal, variable_expenses: Decimal) -> Decimal:
    """MC = Receita Líquida − CMV − Despesas Variáveis."""
    return q2(Decimal(net_rev) - Decimal(cmv) - Decimal(variable_expenses))


def contribution_margin_pct(net_rev: Decimal, cmv: Decimal, variable_expenses: Decimal) -> Decimal:
    return pct(contribution_margin(net_rev, cmv, variable_expenses), net_rev)


# 5) Lucro líquido -----------------------------------------------------
def net_profit(gross_p: Decimal, fixed_expenses: Decimal, variable_expenses: Decimal) -> Decimal:
    return q2(Decimal(gross_p) - Decimal(fixed_expenses) - Decimal(variable_expenses))


# 6) Fluxo de caixa diário/mensal --------------------------------------
def cash_flow_consolidate(movements: Iterable[Mapping]) -> dict:
    """
    movements: [{direction: 'in'|'out', amount, business_date}]
    Retorna: {'inflow', 'outflow', 'net'} consolidado.
    """
    inflow = ZERO; outflow = ZERO
    for m in movements:
        amt = Decimal(m["amount"])
        if m["direction"] == "in":
            inflow += amt
        else:
            outflow += amt
    return {"inflow": q2(inflow), "outflow": q2(outflow), "net": q2(inflow - outflow)}


# 7) Ponto de equilíbrio -----------------------------------------------
def break_even_revenue(fixed_expenses: Decimal, contribution_margin_ratio: Decimal) -> Decimal:
    """
    Receita necessária para cobrir custos fixos.
    contribution_margin_ratio = MC / Receita Líquida (0..1).
    """
    cmr = Decimal(contribution_margin_ratio)
    if cmr <= 0:
        return Decimal("Infinity")
    return q2(Decimal(fixed_expenses) / cmr)


def break_even_units(fixed_expenses: Decimal, unit_price: Decimal,
                     unit_variable_cost: Decimal) -> Decimal:
    """Quantidade de unidades para empatar (ex.: hambúrgueres)."""
    contrib_unit = Decimal(unit_price) - Decimal(unit_variable_cost)
    if contrib_unit <= 0:
        return Decimal("Infinity")
    return (Decimal(fixed_expenses) / contrib_unit).quantize(Decimal("1"))


# Extras ---------------------------------------------------------------
def average_ticket(gross: Decimal, orders_count: int) -> Decimal:
    if not orders_count:
        return ZERO
    return q2(Decimal(gross) / Decimal(orders_count))


def projected_cash_flow(receivables: Iterable[Mapping], payables: Iterable[Mapping]) -> dict:
    """Projeção a partir de AR/AP pendentes agrupados por due_date."""
    from collections import defaultdict
    daily = defaultdict(lambda: {"in": ZERO, "out": ZERO})
    for r in receivables:
        daily[r["due_date"]]["in"] += Decimal(r["amount"])
    for p in payables:
        daily[p["due_date"]]["out"] += Decimal(p["amount"])

    days = sorted(daily.keys())
    accumulated = ZERO
    rows = []
    for d in days:
        net = daily[d]["in"] - daily[d]["out"]
        accumulated += net
        rows.append({
            "due_date": d,
            "inflow": q2(daily[d]["in"]),
            "outflow": q2(daily[d]["out"]),
            "net": q2(net),
            "accumulated": q2(accumulated),
        })
    return {"days": rows, "final_balance": q2(accumulated)}
