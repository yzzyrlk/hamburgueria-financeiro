# Sistema Financeiro — Hamburgueria

## 1. Estrutura financeira completa

### 1.1 Receitas (Receita Bruta)
- Vendas no balcão (dinheiro / cartão débito / cartão crédito / PIX / vale-refeição)
- Vendas via delivery próprio
- Vendas via marketplace (iFood, Rappi, 99Food)
- Outras receitas (eventos, catering)

Cada venda gera um `order` e, ao ser paga, uma ou mais `transactions`.

### 1.2 Deduções (sobre receita bruta)
Persistidas em `transaction_fees`, sempre vinculadas a uma `transaction`:
- Taxa do adquirente (Stone, Cielo, PagSeguro, Mercado Pago) — % + valor fixo por transação
- Taxa do marketplace (iFood ~12-23%, Rappi ~25-30%)
- Taxa de antecipação de recebíveis
- Impostos sobre venda (Simples Nacional ~6-15,5% conforme anexo e faixa)
- Devoluções e cancelamentos

> Receita Líquida = Receita Bruta − Deduções

### 1.3 CMV (Custo da Mercadoria Vendida)
Calculado a partir da **ficha técnica** (`product_recipes` + `ingredients`):
- CMV unitário do produto = Σ (quantidade do insumo × custo unitário do insumo) + perda%
- CMV do pedido = Σ CMV unitário × quantidade vendida
- CMV mensal compõe DRE; ideal entre 28%–35% do faturamento líquido em hamburgueria

### 1.4 Despesas
**Fixas** (não variam com vendas): aluguel, salários, pró-labore, contador, internet, software, seguro, depreciação.
**Variáveis** (variam com vendas): embalagens, gás, luz variável, comissão equipe, marketing performance, taxa de entrega própria.
**Semivariáveis**: energia elétrica base + extra por movimento.

Categorizadas por `cost_center` e `category` em `accounts_payable`.

### 1.5 Fluxo de caixa
- **Real**: o que **efetivamente** entrou/saiu (regime de caixa) — `cash_flow`.
- **Projetado**: a partir de `accounts_receivable` (D+1, D+30) e `accounts_payable` (vencimentos futuros).
- Visões: diária, semanal, mensal, por conta bancária.

### 1.6 Lucro real (DRE)
```
(+) Receita Bruta
(−) Deduções (taxas + impostos)
(=) Receita Líquida
(−) CMV
(=) Lucro Bruto
(−) Despesas Operacionais (fixas + variáveis)
(=) EBITDA
(−) Depreciação / Amortização
(=) EBIT
(−) Despesas financeiras (juros, taxa antecipação)
(=) Lucro Líquido
```

## 2. Módulos do sistema

1. **Pedidos (Orders)** — cadastro de venda, itens, canais, status.
2. **Pagamentos (Transactions)** — captura de pagamento, taxas, conciliação.
3. **Estoque & Ficha técnica** — produtos, insumos, receitas, custo.
4. **Contas a Pagar/Receber** — agenda financeira.
5. **Fluxo de Caixa** — saldo diário consolidado por conta bancária.
6. **DRE / Indicadores** — fechamento mensal e KPIs (CMV%, ticket médio, margem).
7. **Integrações** — Mercado Pago, Google Sheets, WhatsApp.
8. **Relatórios & Alertas** — resumo diário, ponto de equilíbrio, alertas de margem.

## 3. Fluxo: da venda até o impacto financeiro

```
1. Cliente faz pedido      → POST /orders         → cria order (status=open)
2. Cliente paga            → POST /transactions   → cria transaction + transaction_fees
3. Sistema baixa estoque   → service de estoque   → debita ingredients
4. Sistema calcula CMV     → snapshot no order    → guarda cmv_total
5. Sistema gera AR         → accounts_receivable  → prazo conforme método (D+1, D+30)
6. Quando recebível liquida → cash_flow IN        → atualiza saldo
7. Despesas (compras, salário) → accounts_payable → quando pagas → cash_flow OUT
8. Eventos disparam:       → Google Sheets, WhatsApp resumo
9. Fechamento diário (cron) → consolida business_date → DRE/KPIs
```

## 4. Boas práticas obrigatórias

### 4.1 Idempotência
- Toda `transaction` carrega `external_id UNIQUE` (id do gateway/marketplace).
- Webhooks reentrantes não duplicam: `INSERT ... ON CONFLICT (external_id) DO NOTHING RETURNING ...`.
- Endpoints sensíveis aceitam header `Idempotency-Key` (cache 24h em Redis).

### 4.2 Timezone
- Banco em **UTC** (`timestamptz`).
- Aplicação operando em `America/Sao_Paulo`.
- Campo `business_date` (DATE) representa o "dia operacional" da hamburgueria — uma venda à 01:30 da manhã pertence ao dia anterior se o turno fechar às 04:00. Definido no momento de gravar.

### 4.3 Precisão monetária
- Banco: `NUMERIC(14,2)` para valores, `NUMERIC(14,4)` para alíquotas.
- Python: `decimal.Decimal` com contexto `ROUND_HALF_EVEN` (bancário); arredondamento final só na apresentação.
- **Nunca** `float` para dinheiro.
- Quantidades de insumos: `NUMERIC(14,4)` (kg, L).

### 4.4 Outras
- Migrations versionadas (Alembic).
- Logs estruturados (JSON) com `request_id`, `order_id`.
- Webhooks com verificação de assinatura HMAC.
- Soft delete em entidades financeiras (auditoria).
- Snapshots: `order` guarda preço e CMV no momento da venda — alterar receita depois não reescreve o histórico.
