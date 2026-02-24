---
name: dashboard-layout
description: >
  Patrones de layout para los dashboards del proyecto. Usar cuando se construya
  el shell de la aplicación (sidebar, navbar), el layout de cualquier dashboard,
  o cuando se defina la estructura de grid de una página nueva.
---

# Dashboard Layout

## Shell de la aplicación

### Sidebar (desktop) + Bottom nav (mobile)
```
Desktop (≥ 1024px):
┌─────────────────────────────────────────────┐
│ Sidebar (240px fijo) │ Main content (flex-1) │
│                      │                       │
│ Logo                 │ Topbar                │
│ Nav items            │ ─────────────────────  │
│                      │ Page content          │
│ ─────────────────── │                       │
│ Sync status          │                       │
│ Settings             │                       │
└─────────────────────────────────────────────┘

Mobile (< 1024px):
┌──────────────────┐
│ Topbar (logo)    │
│ ─────────────── │
│ Page content     │
│                  │
│ ─────────────── │
│ Bottom tab bar   │
└──────────────────┘
```

### Implementación sidebar
```tsx
// components/layout/Sidebar.tsx
const NAV_ITEMS = [
  { href: "/",             icon: LayoutDashboard, label: "Overview"      },
  { href: "/performance",  icon: TrendingUp,      label: "Performance"   },
  { href: "/dca",          icon: Bitcoin,         label: "DCA Bitcoin"   },
  { href: "/transactions", icon: ArrowLeftRight,  label: "Transacciones" },
  { href: "/fiscal",       icon: FileText,        label: "Fiscal"        },
  { href: "/settings",     icon: Settings,        label: "Ajustes"       },
]

// Cada item:
<Link href={item.href}
  className={cn(
    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all",
    "text-gray-500 hover:text-gray-200 hover:bg-[#1c1c1c]",
    isActive && "bg-[#1c1c1c] text-white font-medium"
  )}>
  <item.icon className="w-4 h-4 flex-shrink-0" />
  {item.label}
</Link>
```

### Indicador de sync en sidebar
```tsx
// Abajo del sidebar, siempre visible
<div className="flex items-center gap-2 px-3 py-2 text-xs">
  <div className={cn("w-1.5 h-1.5 rounded-full",
    syncStatus === "syncing" ? "bg-amber-400 animate-pulse" :
    syncStatus === "error"   ? "bg-red-400" : "bg-emerald-400"
  )} />
  <span className="text-gray-500">
    {syncStatus === "syncing" ? "Sincronizando..." :
     syncStatus === "error"   ? "Error de sync" :
     `Sync: ${formatRelativeTime(lastSyncAt)}`}
  </span>
</div>
```

## Layouts de página

### Overview Dashboard — 4 KPIs + gráfico grande + tabla
```tsx
<div className="space-y-6 p-6">
  {/* KPIs — 4 columnas en desktop, 2 en tablet, 1 en mobile */}
  <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
    <MetricCard label="Valor total" ... />
    <MetricCard label="P&L total" ... />
    <MetricCard label="ROI" ... />
    <MetricCard label="Capital invertido" ... />
  </div>

  {/* Gráfico + distribución — 2/3 + 1/3 en desktop, stack en mobile */}
  <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div className="lg:col-span-2">
      <PortfolioChart />
    </div>
    <div>
      <PortfolioDistribution />
    </div>
  </div>

  {/* Tabla de activos — full width */}
  <AssetTable />
</div>
```

### Performance Dashboard — selector de rango + 3 KPIs + gráfico + comparativa
```tsx
<div className="space-y-6 p-6">
  {/* Header con selector de rango */}
  <div className="flex items-center justify-between">
    <h1 className="text-xl font-semibold text-white">Rendimiento</h1>
    <RangePicker />
  </div>

  {/* 3 KPIs secundarios */}
  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
    <MetricCard label="Drawdown máx" ... />
    <MetricCard label="Mejor día" ... />
    <MetricCard label="Peor día" ... />
  </div>

  {/* Gráfico grande + benchmarks */}
  <PerformanceChart /> {/* con vs BTC toggle */}

  {/* Heatmap debajo */}
  <PerformanceHeatmap />
</div>
```

### DCA Dashboard — métricas DCA + timeline + curva VWAP
```tsx
<div className="space-y-6 p-6">
  {/* 4 KPIs DCA */}
  <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
    <MetricCard label="Sats acumuladas" value={formatSats(sats)} ... />
    <MetricCard label="Precio promedio compra" ... />
    <MetricCard label="Precio actual BTC" ... />
    <MetricCard label="Compras realizadas" ... />
  </div>

  {/* Gráfico DCA — precio mercado vs VWAP */}
  <DCAChart />

  {/* Timeline de compras en dos columnas: calendario + tabla */}
  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <BuyCalendar />
    <BuyHistory />
  </div>
</div>
```

## Topbar — contexto de página + acciones globales
```tsx
<header className="h-14 border-b border-[#1a1a1a] flex items-center justify-between px-6">
  <div>
    <h1 className="text-sm font-semibold text-white">{pageTitle}</h1>
    <p className="text-xs text-gray-500">{pageSubtitle}</p>
  </div>
  <div className="flex items-center gap-3">
    {/* Selector de divisa */}
    <CurrencyPicker /> {/* USD | EUR | BTC */}
    {/* Botón sync manual */}
    <Button variant="ghost" size="sm" onClick={triggerSync}>
      <RefreshCw className="w-4 h-4" />
    </Button>
  </div>
</header>
```

## Reglas de grid
- Usar `grid` de CSS, no flex anidado, para layouts de página
- Columnas: siempre responden a `sm:`, `lg:`, `xl:` breakpoints
- Gap estándar entre cards: `gap-4` (16px)
- Padding de página: `p-6` (24px) en desktop, `p-4` en mobile
- Cards nunca tienen margin propio, el gap del grid los separa