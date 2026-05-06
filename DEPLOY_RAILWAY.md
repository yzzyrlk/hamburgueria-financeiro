# Deploy no Railway — passo a passo

O projeto já está pronto. O Railway sobe direto via Dockerfile e roda o `schema.sql` automaticamente no startup.

## 1. Subir o código no GitHub

Se ainda não fez:

```bash
cd "hamburgueria-financeiro"
git init
git add .
git commit -m "feat: sistema financeiro hamburgueria"
git branch -M main
git remote add origin https://github.com/SEU_USER/hamburgueria-financeiro.git
git push -u origin main
```

> O Railway aceita também `railway up` via CLI sem GitHub, mas pelo painel é mais simples.

## 2. Criar o projeto no Railway

1. Acesse https://railway.com → **New Project**.
2. Escolha **Deploy from GitHub repo** e selecione o repositório.
3. O Railway detecta o `Dockerfile` automaticamente e começa o build.

## 3. Adicionar o PostgreSQL

No mesmo projeto:

1. Clique em **+ New** → **Database** → **PostgreSQL**.
2. O Railway provisiona o banco e cria a variável `DATABASE_URL` no projeto.
3. Volte no service da API → aba **Variables** → clique em **Add Reference** e referencie a variável `DATABASE_URL` do banco.

> O `db.py` já normaliza o formato da URL automaticamente (`postgres://` → `postgresql+psycopg://`).

## 4. Configurar variáveis de ambiente

Na aba **Variables** do service da API, adicione:

| Variável | Valor sugerido |
|---|---|
| `TZ_APP` | `America/Sao_Paulo` |
| `BUSINESS_DAY_CUTOFF` | `4` |
| `AUTO_MIGRATE` | `true` |
| `MP_ACCESS_TOKEN` | (token de produção do Mercado Pago) |
| `MP_WEBHOOK_SECRET` | (string aleatória para validar webhook) |
| `WHATSAPP_PROVIDER` | `zapi` |
| `WHATSAPP_TOKEN` | (token Z-API) |
| `WHATSAPP_INSTANCE` | (instância Z-API) |
| `WHATSAPP_TO` | (seu número, ex.: 5511999999999) |
| `GSHEETS_CREDENTIALS_JSON` | (JSON inteiro da service account, com aspas escapadas) |
| `GSHEETS_SPREADSHEET_ID` | (ID da planilha) |
| `DEFAULT_CREDIT_RATE` | `0.0399` |
| `DEFAULT_DEBIT_RATE` | `0.0199` |
| `DEFAULT_PIX_RATE` | `0.0099` |
| `DEFAULT_IFOOD_RATE` | `0.23` |

> Você pode deixar as integrações em branco no início — a API sobe normalmente, só os endpoints de integração retornarão erro até preencher.

## 5. Expor a URL pública

1. Aba **Settings** do service → **Networking** → **Generate Domain**.
2. Railway gera algo como `hamburgueria-financeiro-production.up.railway.app`.

Teste:

- `GET https://SUA_URL.up.railway.app/health` → `{"status":"ok"}`
- `GET https://SUA_URL.up.railway.app/docs` → Swagger UI

## 6. Configurar o webhook do Mercado Pago

No painel do Mercado Pago → **Suas integrações** → **Webhooks**, aponte para:

```
https://SUA_URL.up.railway.app/mp/webhook
```

E coloque o mesmo `MP_WEBHOOK_SECRET` que cadastrou no Railway.

## 7. Fechamento diário (cron)

O Railway tem **Cron Jobs**. No projeto:

1. **+ New** → **Empty Service** ou use o mesmo service criando um **Cron**.
2. Schedule: `30 7 * * *` (07:30 UTC = 04:30 em São Paulo).
3. Comando: `python -m app.services.daily_close`.

## Verificação rápida

```bash
# Cria um pedido de teste
curl -X POST https://SUA_URL.up.railway.app/orders \
  -H "Content-Type: application/json" \
  -d '{"channel":"balcao","items":[{"product_id":"PRECISA_EXISTIR","quantity":1}]}'
```

(antes você precisa cadastrar produtos e ingredientes — o schema cria tabelas vazias)

## Custos estimados

- Plano Hobby do Railway: **US$ 5/mês** de crédito incluso.
- Postgres pequeno + 1 service web cabe nesse crédito para um restaurante começando.

## Problemas comuns

**Build falha em `psycopg`**: o `psycopg[binary]==3.2.3` no `requirements.txt` já resolve. Se ainda assim falhar, troque por `psycopg2-binary==2.9.9` e ajuste `_normalize_db_url` para usar `postgresql+psycopg2://`.

**Erro de schema no startup**: setar `AUTO_MIGRATE=false`, conectar via `railway connect Postgres` e rodar manualmente `psql < sql/schema.sql`.

**Cold start do webhook MP**: Railway mantém o container quente (não é serverless), então não há cold start. Se vier timeout, é rede ou DB.
