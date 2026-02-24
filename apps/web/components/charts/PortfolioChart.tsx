"use client"

import {
  AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts"
import { formatCurrency } from "@/lib/formatters"

interface ChartPoint {
  date:     string
  value:    number
  invested: number
}

interface PortfolioChartProps {
  data:          ChartPoint[]
  investedTotal: number
}

export function PortfolioChart({ data, investedTotal }: PortfolioChartProps) {
  const first = data[0]?.value ?? 0
  const last  = data[data.length - 1]?.value ?? 0
  const isPositive = last >= first
  const color = isPositive ? "#10b981" : "#ef4444"

  if (data.length === 0) {
    return (
      <div className="bg-surface border border-[var(--border)] rounded-xl p-6
                      flex flex-col items-center justify-center h-[300px]">
        <p className="text-secondary text-sm">Sin datos de evolución aún</p>
        <p className="text-tertiary text-xs mt-1">
          Configura tus API Keys y sincroniza para ver el gráfico
        </p>
      </div>
    )
  }

  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl p-6">
      <h2 className="text-sm font-medium text-secondary mb-4">
        Evolución del portafolio — 30 días
      </h2>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="portfolioGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={color} stopOpacity={0.15} />
              <stop offset="95%" stopColor={color} stopOpacity={0}    />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--border-subtle)"
            vertical={false}
          />

          <XAxis
            dataKey="date"
            tick={{ fill: "var(--text-tertiary)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(d) =>
              new Date(d).toLocaleDateString("es-ES", {
                month: "short", day: "numeric",
              })
            }
            interval="preserveStartEnd"
          />

          <YAxis
            tick={{ fill: "var(--text-tertiary)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) =>
              v >= 1000
                ? `€${(v / 1000).toFixed(0)}k`
                : `€${v.toFixed(0)}`
            }
            width={52}
          />

          <Tooltip content={<PortfolioTooltip />} />

          {/* Línea de capital invertido (referencia plana) */}
          {investedTotal > 0 && (
            <ReferenceLine
              y={investedTotal}
              stroke="var(--text-tertiary)"
              strokeDasharray="4 4"
              strokeWidth={1}
              label={{
                value: "Invertido",
                fill: "var(--text-tertiary)",
                fontSize: 10,
                position: "insideTopLeft",
              }}
            />
          )}

          {/* Área de valor */}
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            fill="url(#portfolioGradient)"
            dot={false}
            activeDot={{ r: 4, fill: color, strokeWidth: 0 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

function PortfolioTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const { value, invested } = payload[0].payload
  const pnl    = value - invested
  const pnlPct = invested > 0 ? ((pnl / invested) * 100).toFixed(2) : "0.00"

  return (
    <div className="bg-elevated border border-[var(--border)] rounded-lg p-3
                    shadow-xl text-xs space-y-1">
      <p className="text-secondary">
        {new Date(label).toLocaleDateString("es-ES", {
          weekday: "short", day: "numeric", month: "long",
        })}
      </p>
      <p className="text-primary font-semibold tabular-nums">
        {formatCurrency(value, "EUR")}
      </p>
      {invested > 0 && (
        <>
          <p className="text-tertiary tabular-nums">
            Invertido: {formatCurrency(invested, "EUR")}
          </p>
          <p className={`font-semibold tabular-nums ${pnl >= 0 ? "text-positive" : "text-negative"}`}>
            {pnl >= 0 ? "+" : ""}{formatCurrency(pnl, "EUR")}{" "}
            ({pnl >= 0 ? "+" : ""}{pnlPct}%)
          </p>
        </>
      )}
    </div>
  )
}

export function PortfolioChartSkeleton() {
  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl p-6 animate-pulse">
      <div className="h-4 bg-elevated rounded w-48 mb-6" />
      <div className="h-[220px] bg-elevated rounded-lg" />
    </div>
  )
}
