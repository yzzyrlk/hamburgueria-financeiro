# Hamburgueria Financeiro

Sistema financeiro completo para hamburgueria: pedidos, pagamentos, taxas, CMV por ficha técnica, fluxo de caixa, DRE, integrações com Mercado Pago, Google Sheets e WhatsApp.

## Stack
- Python 3.12 / FastAPI
- PostgreSQL 16 (NUMERIC, timestamptz, JSONB)
- SQLAlchemy 2.x
- httpx, gspread

## Estrutura
```
app/
  core/          # config, db, time
  models/        # SQLAlchemy + Pydantic
  routes/        # FastAPI routers
  services/      # regras: order, transaction, finance, reporting, daily_close
  integrations/  # mercado_pago, google_sheets, whatsapp
sql/schema.sql   # DDL completo
docs/            # arquitetura
```

## Subir local
```bash
cp .env.example .env
docker compose up --build
```

## Endpoints principais
- `POST /orders` — cria pedido (com snapshot de CMV)
- `POST /transactions` — registra pagamento + taxas + AR/CashFlow
- `GET  /transactions?start=&end=` — listar
- `GET  /reports/summary?start=&end=` — DRE resumido
- `GET  /reports/cash-flow?start=&end=` — fluxo de caixa diário
- `POST /mp/pix` — gera cobrança PIX no Mercado Pago
- `POST /mp/webhook` — recebe confirmações de pagamento

## Boas práticas aplicadas
- `external_id UNIQUE` nas tabelas para idempotência (orders, transactions, cash_flow, accounts_payable)
- `business_date` separado do `created_at` (cutoff 04h configurável)
- `Decimal` em todo cálculo monetário; `NUMERIC(14,2)` em banco
- Webhook MP com verificação HMAC-SHA256
- Snapshot de preço/CMV no pedido (alterações futuras na ficha técnica não reescrevem o histórico)
- Falhas em integrações não revertem pagamento (best-effort, logadas)

## Fechamento diário
Cron sugerido (04:30):
```bash
0 4 * * *  python -m app.services.daily_close
```
