---
name: ui-design-system
description: >
  Sistema de diseño completo del proyecto. Usar siempre al crear cualquier
  componente React nuevo, al tomar decisiones de layout, tipografía, color
  o espaciado. Define la identidad visual y las reglas que garantizan coherencia.
---

# UI Design System — Binance Portfolio Dashboard

## Filosofía
Dashboard financiero personal: **densa en información, limpia en presentación**.
Inspiración: Vercel Analytics + Linear + Raycast. No Bloomberg (demasiado denso),
no apps de banco (demasiado vacío).

## Tokens de diseño

### Colores (usar siempre como CSS variables, nunca hardcoded)
```css
/* Semánticos — significado fijo en toda la app */
--positive: theme('colors.emerald.500')   /* #10b981 — ganancias, subidas */
--negative: theme('colors.red.500')       /* #ef4444 — pérdidas, bajadas */
--warning:  theme('colors.amber.500')     /* #f59e0b — alertas, pendiente */
--btc:      theme('colors.orange.500')    /* #f97316 — Bitcoin */
--eth:      theme('colors.violet.400')    /* #a78bfa — Ethereum */
--accent:   theme('colors.indigo.500')    /* #6366f1 — acciones, links */

/* Superficies dark mode */
--bg-base:     #080808   /* fondo raíz */
--bg-surface:  #111111   /* cards, paneles */
--bg-elevated: #1c1c1c   /* dropdown, tooltip, modal */
--bg-hover:    #222222   /* hover de filas, items */
--border:      #2a2a2a   /* bordes de cards */
--border-subtle: #1a1a1a /* separadores internos */

/* Texto */
--text-primary:   #f5f5f5  /* valores principales */
--text-secondary: #888888  /* labels, metadata */
--text-tertiary:  #555555  /* placeholders, disabled */
```

### Tipografía
```tsx
// Jerarquía en dashboards financieros:
// Valor grande (número principal de una métrica KPI)
<span className="text-3xl font-bold tabular-nums tracking-tight text-white">
  $24,832.50
</span>

// Label de la métrica
<span className="text-xs font-medium uppercase tracking-wider text-gray-500">
  Valor del portafolio
</span>

// Delta (cambio porcentual)
<span className="text-sm font-semibold tabular-nums text-emerald-500">
  +12.4%
</span>

// Siempre: tabular-nums para números (evita que el layout salte)
// Siempre: tracking-tight para números grandes
```

### Espaciado — solo estos valores
`p-2 p-3 p-4 p-6 p-8 p-12` (8, 12, 16, 24, 32, 48px)
`gap-2 gap-3 gap-4 gap-6 gap-8`

### Border radius
- Cards grandes: `rounded-xl` (12px)
- Elementos internos: `rounded-lg` (8px)
- Badges, pills: `rounded-full`

## Componentes del sistema

### MetricCard — KPI principal
```tsx
// Estructura fija para todas las métricas del dashboard
<div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-6
                hover:border-[#3a3a3a] transition-colors">
  <div className="flex items-center justify-between mb-4">
    <span className="text-xs font-medium uppercase tracking-wider text-gray-500">
      {label}
    </span>
    <Icon className="w-4 h-4 text-gray-600" />
  </div>
  <div className="text-3xl font-bold tabular-nums tracking-tight text-white mb-2">
    {value}
  </div>
  <div className={cn("text-sm font-semibold tabular-nums",
    isPositive ? "text-emerald-500" : "text-red-500")}>
    {delta} <span className="text-gray-500 font-normal text-xs">{period}</span>
  </div>
</div>
```

### DataTable — tablas de transacciones
```tsx
// Filas alternadas, hover sutil, alineación de números a la derecha
<tr className="border-b border-[#1a1a1a] hover:bg-[#1c1c1c] transition-colors">
  <td className="py-3 px-4 text-sm text-gray-300">{fecha}</td>
  <td className="py-3 px-4 text-sm font-medium text-white">{activo}</td>
  <td className="py-3 px-4 text-sm tabular-nums text-right text-white">{cantidad}</td>
  <td className="py-3 px-4 text-sm tabular-nums text-right">
    <span className={pnl >= 0 ? "text-emerald-500" : "text-red-500"}>
      {formatCurrency(pnl)}
    </span>
  </td>
</tr>
```

### Skeleton loaders — obligatorio en todo componente async
```tsx
// MetricCard skeleton
<div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-6 animate-pulse">
  <div className="h-3 bg-[#2a2a2a] rounded w-24 mb-4" />
  <div className="h-8 bg-[#2a2a2a] rounded w-36 mb-2" />
  <div className="h-3 bg-[#2a2a2a] rounded w-20" />
</div>

// Chart skeleton
<div className="bg-[#111111] border border-[#2a2a2a] rounded-xl p-6 animate-pulse">
  <div className="h-4 bg-[#2a2a2a] rounded w-32 mb-6" />
  <div className="h-48 bg-[#1a1a1a] rounded-lg" />
</div>
```

### Badge de tipo de transacción
```tsx
const badgeStyles = {
  buy:      "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  sell:     "bg-red-500/10 text-red-400 border-red-500/20",
  deposit:  "bg-blue-500/10 text-blue-400 border-blue-500/20",
  withdraw: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  earn:     "bg-violet-500/10 text-violet-400 border-violet-500/20",
}
<span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium",
  badgeStyles[type])}>
  {type}
</span>
```

## Formateo de números (obligatorio usar estas funciones)
```ts
// lib/formatters.ts
export const formatCurrency = (value: number, currency = "USD") =>
  new Intl.NumberFormat("es-ES", {
    style: "currency", currency,
    minimumFractionDigits: 2, maximumFractionDigits: 2
  }).format(value)

export const formatPercent = (value: number) =>
  `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`

export const formatCrypto = (value: number, decimals = 8) =>
  new Intl.NumberFormat("es-ES", {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals
  }).format(value)

export const formatSats = (btc: number) =>
  `${Math.round(btc * 1e8).toLocaleString("es-ES")} sats`
```

## Estados que todo componente debe manejar
1. **Loading** → skeleton loader (nunca spinner global)
2. **Error** → mensaje amigable + botón de retry
3. **Empty** → ilustración/mensaje de estado vacío, no pantalla en blanco
4. **Data** → el componente en sí

```tsx
// Patrón estándar
if (isLoading) return <ComponentSkeleton />
if (error) return <ErrorState message="No se pudieron cargar los datos" onRetry={refetch} />
if (!data?.length) return <EmptyState message="No hay transacciones todavía" />
return <ComponentWithData data={data} />
```