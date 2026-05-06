# Revisão final — pontos de atenção e evolução

## Performance

- **Índices** já cobrem os filtros mais comuns (`business_date`, `status`, `channel`). Conforme o volume cresce, criar índices parciais para acelerar consultas frequentes:
  ```sql
  CREATE INDEX idx_ar_pending_due ON accounts_receivable(due_date) WHERE status = 'pending';
  CREATE INDEX idx_ap_pending_due ON accounts_payable(due_date)    WHERE status = 'pending';
  CREATE INDEX idx_orders_paid    ON orders(business_date)         WHERE status = 'paid';
  ```
- **Materialized view** para DRE/KPI mensal — recalcula uma vez por dia em vez de em cada request:
  ```sql
  CREATE MATERIALIZED VIEW mv_dre_daily AS
  SELECT business_date, SUM(gross_amount) gross, SUM(fees_amount) fees, ...
  FROM transactions WHERE status='approved' GROUP BY business_date;
  ```
- **Pool de conexão** dimensionado em `db.py` (`pool_size=10, max_overflow=20`) — ajustar pelo `pgbouncer` em produção.
- **Cache de resumo** em Redis (TTL 60s) — `/reports/summary` é o endpoint mais consultado pelo dashboard.

## Segurança

- **Secrets**: nada de credenciais em git. Use `.env` apenas em dev; em produção, AWS Secrets Manager / GCP Secret Manager / Doppler.
- **Webhook MP**: já valida HMAC. Adicionar também rate limit (slowapi) e verificação de IP origem.
- **Auth na API**: hoje aberta. Adicionar OAuth2 / JWT (`fastapi-users`) com escopos: `staff`, `manager`, `owner`.
- **PII**: `customer_name` deve ter retenção limitada (LGPD). Considerar pseudonimização após 90 dias.
- **Auditoria**: criar tabela `audit_log` (user_id, action, entity, before/after JSONB).
- **Banco**: usuário da app sem permissão de DDL; rodar migrations com role separada.

## Organização e qualidade

- Adicionar **Alembic** (`alembic init alembic`) para migrações versionadas em vez de aplicar `schema.sql` direto.
- **Testes**: pytest + factory_boy + container Postgres efêmero (testcontainers). Cobrir:
  - cálculo de CMV (valores limítrofes, perda %)
  - idempotência de transactions (mesmo `external_id` 2x)
  - business_date no cutoff (00:30 vira dia anterior?)
  - webhook reentrante
- **Linters**: ruff + mypy estrito + pre-commit.
- **Logs estruturados**: `structlog` com `request_id` propagado via middleware.
- **Observabilidade**: OpenTelemetry → Grafana/Tempo; métricas Prometheus (latência por endpoint, taxa de erro, fila de webhooks).

## Escalabilidade

- **Webhook**: hoje processa síncrono. Em volume, enfileirar (Celery + Redis ou RQ) e responder 200 rapidamente. O MP reenvia se demorar.
- **Integrações best-effort**: Sheets e WhatsApp já estão isolados em try/except. Mover para fila assíncrona com retries exponenciais.
- **Read replica** para relatórios pesados (consultas de DRE histórico).
- **Multi-loja**: adicionar `store_id` em todas as tabelas operacionais e índice composto `(store_id, business_date)`.
- **Particionamento** de `transactions` e `cash_flow` por mês quando passar de ~10M de linhas.

## Ajustes específicos para hamburgueria

- **Mix de canais**: dashboard separando margem real por canal. iFood com 23% de taxa muda completamente o ponto de equilíbrio.
- **CMV alvo**: alerta automático no WhatsApp se CMV diário ultrapassar 35% — sintoma de desperdício, ficha desatualizada ou fornecedor reajustando.
- **Combos / promoções**: criar tabela `product_combos` com regras de preço; o snapshot já cobre o histórico.
- **Insumos sazonais**: campo `unit_cost` atualizado pelo módulo de compras (entrada de NF) — manter histórico em `ingredient_price_history`.
- **Comanda x pedido**: hoje 1 order = 1 venda. Em mesa, 1 comanda pode virar várias orders (couvert, bebida, prato). Modelar `tabs` se necessário.
- **Consumo da equipe**: `orders` com `channel='outros'` e `discount = total` para zerar receita sem perder o custo (CMV continua contando).
- **Conciliação bancária**: importar extrato OFX/CSV e bater com `cash_flow` por valor + data — fundamental antes de aceitar como receita realizada.
- **Indicadores adicionais**:
  - CMC (custo da mão de obra) % faturamento — meta 20-25%
  - Custo de ocupação (aluguel + condomínio + IPTU) % faturamento — meta < 12%
  - Ticket médio por canal
  - DRR (dias de recebíveis em aberto)

## Próximos passos sugeridos

1. Subir Alembic e mover `schema.sql` para a primeira migration.
2. Adicionar autenticação JWT em todas as rotas exceto `/health` e `/mp/webhook`.
3. Criar fila assíncrona para integrações Sheets/WhatsApp (Celery + Redis).
4. Dashboard front (Next.js) consumindo `/reports/*` com gráficos de margem e fluxo.
5. Importação de extrato bancário e conciliação semi-automática.
