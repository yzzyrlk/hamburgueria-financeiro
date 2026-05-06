-- =====================================================================
-- Sistema Financeiro - Hamburgueria
-- PostgreSQL 14+
-- Convenções:
--   * Dinheiro:    NUMERIC(14,2)
--   * Alíquotas:   NUMERIC(7,4)  (ex.: 0.0399 = 3,99%)
--   * Quantidades: NUMERIC(14,4)
--   * Datas:       timestamptz (sempre UTC); business_date é DATE.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------- ENUMS ----------------------------------------------------
DO $$ BEGIN
  CREATE TYPE order_channel AS ENUM ('balcao','delivery_proprio','ifood','rappi','99food','outros');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE order_status AS ENUM ('open','paid','cancelled','refunded');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE payment_method AS ENUM ('dinheiro','pix','debito','credito','vale_refeicao','marketplace','outro');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE transaction_status AS ENUM ('pending','approved','refused','refunded','chargeback');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE fee_type AS ENUM ('mdr','marketplace','antecipacao','imposto','outro');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE cash_flow_direction AS ENUM ('in','out');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE ar_status AS ENUM ('pending','received','cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE ap_status AS ENUM ('pending','paid','cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ---------- INGREDIENTES (insumos) ----------------------------------
CREATE TABLE IF NOT EXISTS ingredients (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT NOT NULL UNIQUE,
  unit            TEXT NOT NULL,                 -- kg, g, L, ml, un
  unit_cost       NUMERIC(14,4) NOT NULL CHECK (unit_cost >= 0),
  stock_qty       NUMERIC(14,4) NOT NULL DEFAULT 0,
  min_stock_qty   NUMERIC(14,4) NOT NULL DEFAULT 0,
  loss_pct        NUMERIC(7,4)  NOT NULL DEFAULT 0,  -- perda/quebra
  active          BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------- PRODUTOS (cardápio) -------------------------------------
CREATE TABLE IF NOT EXISTS products (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sku             TEXT UNIQUE,
  name            TEXT NOT NULL,
  category        TEXT,                          -- burger, bebida, acompanhamento
  price           NUMERIC(14,2) NOT NULL CHECK (price >= 0),
  active          BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_products_active ON products(active);

-- ---------- FICHA TÉCNICA -------------------------------------------
CREATE TABLE IF NOT EXISTS product_recipes (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  ingredient_id   UUID NOT NULL REFERENCES ingredients(id) ON DELETE RESTRICT,
  quantity        NUMERIC(14,4) NOT NULL CHECK (quantity > 0),
  UNIQUE (product_id, ingredient_id)
);
CREATE INDEX IF NOT EXISTS idx_recipes_product ON product_recipes(product_id);

-- ---------- ORDERS (pedido) -----------------------------------------
CREATE TABLE IF NOT EXISTS orders (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id     TEXT UNIQUE,                   -- id do PDV/marketplace (idempotência)
  channel         order_channel NOT NULL DEFAULT 'balcao',
  status          order_status NOT NULL DEFAULT 'open',
  customer_name   TEXT,
  subtotal        NUMERIC(14,2) NOT NULL DEFAULT 0,
  discount        NUMERIC(14,2) NOT NULL DEFAULT 0,
  delivery_fee    NUMERIC(14,2) NOT NULL DEFAULT 0,
  total           NUMERIC(14,2) NOT NULL DEFAULT 0,
  cmv_total       NUMERIC(14,2) NOT NULL DEFAULT 0,    -- snapshot do CMV no momento
  notes           TEXT,
  business_date   DATE NOT NULL,                       -- dia operacional
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_orders_business_date ON orders(business_date);
CREATE INDEX IF NOT EXISTS idx_orders_status        ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_channel       ON orders(channel);

-- ---------- ORDER ITEMS ---------------------------------------------
CREATE TABLE IF NOT EXISTS order_items (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id        UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id      UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
  quantity        NUMERIC(14,4) NOT NULL CHECK (quantity > 0),
  unit_price      NUMERIC(14,2) NOT NULL CHECK (unit_price >= 0),  -- snapshot
  unit_cmv        NUMERIC(14,2) NOT NULL DEFAULT 0,                -- snapshot CMV unit
  total_price     NUMERIC(14,2) NOT NULL,
  total_cmv       NUMERIC(14,2) NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);

-- ---------- TRANSACTIONS (pagamentos) -------------------------------
CREATE TABLE IF NOT EXISTS transactions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id        UUID NOT NULL REFERENCES orders(id) ON DELETE RESTRICT,
  external_id     TEXT UNIQUE,                   -- id do gateway (idempotência)
  method          payment_method NOT NULL,
  status          transaction_status NOT NULL DEFAULT 'pending',
  gross_amount    NUMERIC(14,2) NOT NULL CHECK (gross_amount >= 0),
  fees_amount     NUMERIC(14,2) NOT NULL DEFAULT 0,
  net_amount      NUMERIC(14,2) NOT NULL DEFAULT 0,    -- gross - fees
  installments    INT NOT NULL DEFAULT 1,
  paid_at         TIMESTAMPTZ,
  business_date   DATE NOT NULL,
  raw_payload     JSONB,                          -- payload do gateway
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tx_order         ON transactions(order_id);
CREATE INDEX IF NOT EXISTS idx_tx_business_date ON transactions(business_date);
CREATE INDEX IF NOT EXISTS idx_tx_status        ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_tx_method        ON transactions(method);

-- ---------- TRANSACTION FEES (taxas/deduções) -----------------------
CREATE TABLE IF NOT EXISTS transaction_fees (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transaction_id  UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
  fee_type        fee_type NOT NULL,
  description     TEXT,
  rate            NUMERIC(7,4),                  -- ex.: 0.0399
  amount          NUMERIC(14,2) NOT NULL CHECK (amount >= 0),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_fees_tx ON transaction_fees(transaction_id);

-- ---------- ACCOUNTS RECEIVABLE -------------------------------------
CREATE TABLE IF NOT EXISTS accounts_receivable (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transaction_id  UUID REFERENCES transactions(id) ON DELETE SET NULL,
  description     TEXT NOT NULL,
  amount          NUMERIC(14,2) NOT NULL CHECK (amount >= 0),
  due_date        DATE NOT NULL,
  received_at     TIMESTAMPTZ,
  status          ar_status NOT NULL DEFAULT 'pending',
  bank_account    TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ar_due_date ON accounts_receivable(due_date);
CREATE INDEX IF NOT EXISTS idx_ar_status   ON accounts_receivable(status);

-- ---------- ACCOUNTS PAYABLE ----------------------------------------
CREATE TABLE IF NOT EXISTS accounts_payable (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id     TEXT UNIQUE,
  supplier        TEXT,
  category        TEXT NOT NULL,                 -- aluguel, insumos, salario...
  cost_center     TEXT,                          -- cozinha, marketing, admin
  description     TEXT NOT NULL,
  amount          NUMERIC(14,2) NOT NULL CHECK (amount >= 0),
  due_date        DATE NOT NULL,
  paid_at         TIMESTAMPTZ,
  status          ap_status NOT NULL DEFAULT 'pending',
  is_fixed        BOOLEAN NOT NULL DEFAULT FALSE,  -- fixa x variável
  bank_account    TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ap_due_date ON accounts_payable(due_date);
CREATE INDEX IF NOT EXISTS idx_ap_status   ON accounts_payable(status);
CREATE INDEX IF NOT EXISTS idx_ap_category ON accounts_payable(category);

-- ---------- CASH FLOW (movimentações reais) -------------------------
CREATE TABLE IF NOT EXISTS cash_flow (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id     TEXT UNIQUE,
  direction       cash_flow_direction NOT NULL,
  amount          NUMERIC(14,2) NOT NULL CHECK (amount >= 0),
  description     TEXT NOT NULL,
  category        TEXT,
  bank_account    TEXT,
  business_date   DATE NOT NULL,
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ar_id           UUID REFERENCES accounts_receivable(id) ON DELETE SET NULL,
  ap_id           UUID REFERENCES accounts_payable(id)    ON DELETE SET NULL,
  transaction_id  UUID REFERENCES transactions(id)        ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_cf_business_date ON cash_flow(business_date);
CREATE INDEX IF NOT EXISTS idx_cf_direction     ON cash_flow(direction);
CREATE INDEX IF NOT EXISTS idx_cf_bank          ON cash_flow(bank_account);

-- ---------- TRIGGER updated_at --------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['ingredients','products','orders','transactions']
  LOOP
    EXECUTE format($f$
      DROP TRIGGER IF EXISTS trg_%1$s_updated ON %1$s;
      CREATE TRIGGER trg_%1$s_updated BEFORE UPDATE ON %1$s
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    $f$, t);
  END LOOP;
END $$;
