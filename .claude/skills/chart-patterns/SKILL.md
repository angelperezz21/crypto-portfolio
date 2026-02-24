---
name: chart-patterns
description: >
  Patrones de implementación para gráficos financieros. Usar cuando se construya
  cualquier visualización: gráficos de evolución de portafolio, DCA, distribución
  de activos, heatmaps o comparativas de rendimiento.
---

# Chart Patterns — Visualizaciones Financieras

## Librería por tipo de gráfico

| Tipo | Librería | Cuándo |
|------|----------|--------|
| Evolución de valor | Recharts AreaChart | Serie temporal del portafolio |
| Precio de activo | TradingView Lightweight | Candlestick, precio BTC |
| Distribución | Recharts PieChart | Composición del portafolio |
| Barras comparativas | Recharts BarChart | P&L por mes, rendimiento por activo |
| Heatmap | Custom CSS Grid | Rendimiento diario tipo GitHub |
| Área DCA | Recharts ComposedChart | Precio mercado vs precio promedio compra |

## Gráfico estrella: Evolución del portafolio (AreaChart)

```tsx
// components/charts/PortfolioChart.tsx
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { useMemo } from "react"

interface DataPoint { date: string; value: number; invested: number }

export function PortfolioChart({ data }: { data: DataPoint[] }) {
  // Color dinámico: verde si ganancia, rojo si pérdida
  const isPositive = data[data.length - 1]?.value >= data[0]?.value
  const color = isPositive ? "#10b981" : "#ef4444"

  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="portfolioGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.15} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fill: "#555", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(d) => new Date(d).toLocaleDateString("es-ES", { month: "short", day: "numeric" })}
        />
        <YAxis
          tick={{ fill: "#555", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          width={48}
        />
        <Tooltip content={<PortfolioTooltip />} />
        {/* Línea de capital invertido — referencia visual */}
        <Area type="monotone" dataKey="invested"
          stroke="#333" strokeWidth={1} strokeDasharray="4 4"
          fill="transparent" dot={false} />
        {/* Línea principal de valor */}
        <Area type="monotone" dataKey="value"
          stroke={color} strokeWidth={2}
          fill="url(#portfolioGradient)" dot={false}
          activeDot={{ r: 4, fill: color, strokeWidth: 0 }} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

// Tooltip custom — siempre mostrar más información de la que el usuario espera
function PortfolioTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const { value, invested } = payload[0].payload
  const pnl = value - invested
  const pnlPct = ((pnl / invested) * 100).toFixed(2)
  
  return (
    <div className="bg-[#1c1c1c] border border-[#2a2a2a] rounded-lg p-3 shadow-xl text-xs">
      <p className="text-gray-400 mb-2">
        {new Date(label).toLocaleDateString("es-ES", { weekday: "short", day: "numeric", month: "long" })}
      </p>
      <p className="text-white font-semibold tabular-nums">
        {new Intl.NumberFormat("es-ES", { style: "currency", currency: "USD" }).format(value)}
      </p>
      <p className="text-gray-500 tabular-nums">
        Invertido: {new Intl.NumberFormat("es-ES", { style: "currency", currency: "USD" }).format(invested)}
      </p>
      <p className={`font-semibold tabular-nums ${pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
        {pnl >= 0 ? "+" : ""}{new Intl.NumberFormat("es-ES", { style: "currency", currency: "USD" }).format(pnl)}
        {" "}({pnl >= 0 ? "+" : ""}{pnlPct}%)
      </p>
    </div>
  )
}
```

## Gráfico DCA: Precio mercado vs precio promedio de compra

```tsx
// ComposedChart con dos líneas: precio de mercado + VWAP acumulado
// + puntos de compra como dots/markers en el eje
<ComposedChart data={dcaData}>
  {/* Línea de precio de mercado BTC */}
  <Line type="monotone" dataKey="marketPrice"
    stroke="#f97316" strokeWidth={2} dot={false} name="Precio BTC" />
  
  {/* Línea de precio promedio de compra (VWAP) */}
  <Line type="monotone" dataKey="avgBuyPrice"
    stroke="#6366f1" strokeWidth={2} strokeDasharray="6 3"
    dot={false} name="Precio medio compra" />
  
  {/* Área entre las dos líneas: verde si por encima, rojo si por debajo */}
  <Area type="monotone" dataKey="spread"
    fill={isAboveAvg ? "#10b981" : "#ef4444"}
    fillOpacity={0.08} stroke="none" />
  
  {/* Puntos de compra — scatter sobre el gráfico */}
  <Scatter dataKey="buyEvent" shape={<BuyEventDot />} name="Compra" />
</ComposedChart>
```

## Pie chart de distribución del portafolio

```tsx
// Reglas del pie chart:
// - Máximo 8 segmentos. El resto agruparlo en "Otros"
// - Colores únicos por activo (lista predefinida, no random)
// - Label fuera del pie con línea (no dentro)
// - Hover muestra valor USD + % del portafolio

const ASSET_COLORS = {
  BTC: "#f97316", ETH: "#6366f1", BNB: "#f59e0b",
  SOL: "#10b981", ADA: "#06b6d4", DOT: "#8b5cf6",
  USDT: "#22c55e", USDC: "#3b82f6", default: "#6b7280"
}
```

## Heatmap de rendimiento (custom)

```tsx
// Grid CSS de 52 columnas (semanas) × 7 filas (días)
// Color: escala de rojo a verde según % de rendimiento diario
// Igual que el contributions graph de GitHub

const getHeatmapColor = (pct: number | null) => {
  if (pct === null) return "#1a1a1a"           // sin datos
  if (pct > 5)  return "#059669"               // verde intenso
  if (pct > 2)  return "#10b981"               // verde medio
  if (pct > 0)  return "#34d399"               // verde suave
  if (pct > -2) return "#f87171"               // rojo suave
  if (pct > -5) return "#ef4444"               // rojo medio
  return "#dc2626"                              // rojo intenso
}
```

## Selector de rango temporal (obligatorio en Performance)

```tsx
// Botones pill: 7D | 30D | 90D | 1A | Todo
// El activo tiene fondo accent, los demás transparentes con hover
const RANGES = ["7D", "30D", "90D", "1A", "Todo"] as const

<div className="flex gap-1 p-1 bg-[#1a1a1a] rounded-lg">
  {RANGES.map(range => (
    <button key={range}
      onClick={() => setActiveRange(range)}
      className={cn(
        "px-3 py-1.5 text-xs font-medium rounded-md transition-all",
        activeRange === range
          ? "bg-[#2a2a2a] text-white shadow-sm"
          : "text-gray-500 hover:text-gray-300"
      )}>
      {range}
    </button>
  ))}
</div>
```

## Reglas de oro para gráficos financieros
1. **Tooltip siempre custom** — el default de Recharts es feo. Siempre sobreescribir
2. **Sin ejes con líneas** — `axisLine={false}` y `tickLine={false}` siempre
3. **Grid horizontal solo** — `vertical={false}` en CartesianGrid
4. **Colores semánticos** — nunca usar colores aleatorios para P&L
5. **Números con formato** — nunca valores raw sin formatear en tooltips
6. **responsive** — siempre envolver en `<ResponsiveContainer width="100%" height={N}>`