---
name: db-patterns
description: >
  Patrones de base de datos para el proyecto. Usar cuando se creen migraciones,
  nuevas queries, modelos SQLAlchemy o se optimicen consultas de series temporales.
---

# Database Patterns

## Tipos de datos críticos
- Cantidades cripto: NUMERIC(36,18)
- Precios USD: NUMERIC(20,8)  
- IDs de Binance: VARCHAR(100) con constraint UNIQUE

## Índices obligatorios
- transactions: (account_id, executed_at), (base_asset, executed_at)
- price_history: (symbol, interval, open_at) UNIQUE
- portfolio_snapshots: (account_id, snapshot_date) UNIQUE

## Evitar N+1
Usar SQLAlchemy joinedload() o selectinload() para relaciones.
Para series temporales largas usar queries nativas con text().

## Migraciones
Siempre con Alembic. Nunca modificar migraciones ya ejecutadas.
Cada migración debe tener downgrade() implementado.
```

---

### FASE 3 — Arrancar Claude Code y construir el proyecto por fases

Abre la terminal en la raíz del proyecto y ejecuta `claude`. A partir de aquí le vas dando prompts por fases, **una a la vez**. No le des todo de golpe.

**Prompt Fase 1 — Scaffolding:**
```
Lee el CLAUDE.md del proyecto. Luego crea el scaffolding completo:
1. docker-compose.yml con servicios: postgres, redis, api (FastAPI), web (Next.js), scheduler
2. apps/api/ con estructura FastAPI: main.py, routers/, services/, models/, sync/, core/config.py
3. apps/web/ con create-next-app (TypeScript, Tailwind, App Router)
4. Migraciones Alembic con las 5 tablas del SRS: accounts, transactions, balances_snapshot, price_history, portfolio_snapshots
5. .env.example con todas las variables necesarias
No implementes lógica todavía, solo estructura y configuración.
```

**Prompt Fase 1b — Cliente Binance:**
```
Implementa el cliente de la API de Binance en apps/api/sync/binance_client.py.
Requisitos según el skill binance-client:
- Autenticación HMAC-SHA256
- Rate limit manager que respete X-MBX-USED-WEIGHT-1M
- Retry con backoff exponencial
- Métodos: get_account_balances(), get_trades(symbol, from_id), get_deposits(), get_withdrawals(), get_fiat_orders(), get_klines(symbol, interval, start_time)
Incluye tests en tests/test_binance_client.py con mocks de httpx.
```

**Prompt Fase 1c — Sync service:**
```
Implementa el servicio de sincronización en apps/api/sync/sync_service.py:
- Sync incremental: consulta último timestamp en BD antes de llamar a Binance
- Maneja paginación de cada endpoint
- Persiste en BD usando SQLAlchemy (usa el skill db-patterns)
- Registra resultado en tabla sync_logs
- APScheduler job configurable via variable de entorno SYNC_INTERVAL_MINUTES
```

**Prompt Fase 2 — Cálculos financieros:**
```
Implementa apps/api/services/portfolio_service.py con todos los cálculos financieros.
Usa el skill financial-calcs para las fórmulas. Implementa:
- calculate_portfolio_overview(): valor total, P&L total, capital invertido
- calculate_asset_metrics(): métricas por activo con FIFO para coste base
- calculate_dca_analysis(asset): VWAP, sats acumuladas, calendario de compras
- calculate_performance_history(from_date, to_date): serie temporal diaria
- calculate_drawdown(): drawdown máximo sobre la serie histórica
Todos los cálculos con Decimal, tests con pytest para cada función.
```

**Prompt Fase 3 — API endpoints:**
```
Implementa los routers FastAPI en apps/api/routers/ según el SRS:
- dashboard.py: GET /api/v1/dashboard/overview, /performance, /dca/{asset}
- transactions.py: GET /api/v1/transactions (paginado), /export (CSV)
- portfolio.py: GET /api/v1/portfolio/assets, /history
- settings.py: GET/POST /api/v1/settings (cifrado AES-256-GCM de API Keys)
- sync.py: POST /api/v1/sync/trigger, GET /api/v1/sync/status
- fiscal.py: GET /api/v1/fiscal/{year}
Incluye autenticación JWT en todas las rutas.
```

**Prompt Fase 4 — Frontend:**
```
Implementa el frontend en apps/web/. Usa Next.js 14 App Router, Tailwind, shadcn/ui.
Empieza por:
1. Layout con sidebar de navegación (Overview, Performance, DCA, Transacciones, Fiscal, Settings)
2. Dashboard Overview: cards con valor total/P&L/ROI, gráfico de evolución 30d con Recharts
3. Settings page: formulario para introducir API Key y Secret con validación
4. Modo oscuro con next-themes
Cada componente en su propio archivo, tipado con TypeScript.
```

---

### FASE 4 — Tips para trabajar bien con Claude Code

**Usa `/compact` regularmente.** En sesiones largas el contexto se llena. Compacta cuando vayas a cambiar de módulo.

**Plan mode primero para tareas grandes.** Antes de implementar algo complejo escribe:
```
Planifica cómo implementarías el sistema de cálculo FIFO para P&L realizado.
No escribas código todavía, solo el plan.
```
Revisa el plan, corrígelo si algo no te cuadra, y luego pídele que implemente.

**Un módulo a la vez.** No le pidas hacer el sync service y los endpoints y el frontend en el mismo prompt. Ve módulo a módulo y verifica que funciona antes de continuar.

**Referencia el SRS en prompts complejos.** Puedes decirle:
```
Según las reglas de RF-02.5 del SRS (sincronización incremental), 
implementa el método que calcula desde qué timestamp hay que pedir datos a Binance.
```

**Para debugging**, en lugar de describir el error a Claude Code, pégale directamente el stack trace completo.

---

### Resumen de la estructura final de skills
```
.claude/
└── skills/
    ├── binance-client/
    │   └── SKILL.md      ← rate limit, auth, paginación
    ├── financial-calcs/
    │   └── SKILL.md      ← fórmulas, Decimal, FIFO
    └── db-patterns/
        └── SKILL.md      ← tipos NUMERIC, índices, SQLAlchemy
CLAUDE.md                 ← stack, reglas globales, convenciones