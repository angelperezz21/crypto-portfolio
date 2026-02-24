# Binance Portfolio Dashboard — Contexto Compartido

## Producto
Aplicación web personal para analizar un portafolio de Binance: balances, historial de
transacciones, DCA en Bitcoin, P&L, ROI, IRR y dashboards interactivos. Uso personal,
un solo usuario, datos sensibles.

## Stack
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, Recharts
- **Backend**: FastAPI (Python 3.12), SQLAlchemy 2.0, Alembic
- **DB**: PostgreSQL 15 — NUMERIC(36,18) para cantidades cripto, NUMERIC(20,8) para precios
- **Cache**: Redis
- **Scheduler**: APScheduler (proceso independiente)
- **Deploy**: Docker Compose

## Estructura de carpetas
```
apps/
  api/
    routers/        → endpoints FastAPI (/api/v1/*)
    services/       → lógica de negocio y cálculos financieros
    models/         → modelos SQLAlchemy
    sync/           → cliente Binance + scheduler
    core/           → config, seguridad, dependencias
  web/
    app/            → páginas Next.js (App Router)
    components/
      ui/           → componentes base (shadcn)
      charts/       → gráficos Recharts / TradingView
      layout/       → sidebar, navbar, shells
      dashboard/    → widgets de cada dashboard
    lib/            → utils, hooks, api client
    styles/
packages/
  shared/           → tipos TypeScript compartidos
```

## Reglas absolutas (todos los agentes)
- NUNCA float para cálculos financieros → siempre Python `Decimal` o `NUMERIC` en BD
- NUNCA exponer API Keys de Binance en logs, respuestas ni frontend
- NUNCA hardcodear secrets → variables de entorno en `.env`
- El scheduler es el ÚNICO proceso que escribe datos de Binance en la BD
- El frontend NUNCA llama directamente a la API de Binance
- Migraciones siempre con Alembic, siempre con `downgrade()` implementado

## Agentes del equipo
| Agente | Rol | Invocación |
|--------|-----|-----------|
| **Architect** | Lógica, backend, sync, BD, cálculos | `claude --agent architect` |
| **UI** | Frontend, componentes, UX, diseño | `claude --agent ui` |

## Convenciones de código
- Python: black + ruff, type hints en todo
- TypeScript: strict mode, no `any` explícito
- Commits: conventional commits (feat:, fix:, refactor:, test:)
- API responses: siempre `{ data, error, meta }` para consistencia