"use client"

import {
  ComposedChart,
  Line,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Legend,
} from "recharts"
import type { BtcBuyEventRaw, BtcPricePoint } from "@/lib/types"
import { d } from "@/lib/formatters"

interface BtcPriceChartProps {
  priceHistory: BtcPricePoint[]
  buyEvents: BtcBuyEventRaw[]
  vwapUsd: number
  currentPriceUsd: number
}

interface LinePoint {
  ts: number
  price: number
  ma50?: number
  ma200?: number
}

interface ScatterPoint {
  ts: number
  price: number
  quantity: number
  total_usd: number
  timing_pct: number | null
}

function formatPrice(v: number): string {
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}k`
  return `$${v.toFixed(0)}`
}

function formatDate(ts: number): string {
  return new Date(ts).toLocaleDateString("es-ES", {
    day: "numeric",
    month: "short",
    year: "numeric",
  })
}

export function BtcPriceChart({
  priceHistory,
  buyEvents,
  vwapUsd,
  currentPriceUsd,
}: BtcPriceChartProps) {
  const lineData: LinePoint[] = priceHistory.map((p) => ({
    ts: new Date(p.date).getTime(),
    price: d(p.price),
    ...(p.ma50 != null ? { ma50: d(p.ma50) } : {}),
    ...(p.ma200 != null ? { ma200: d(p.ma200) } : {}),
  }))

  const quantities = buyEvents.map((e) => d(e.quantity))
  const maxQty = Math.max(...quantities, 0)

  const scatterData: ScatterPoint[] = buyEvents.map((e) => ({
    ts: new Date(e.date).getTime(),
    price: d(e.price_usd),
    quantity: d(e.quantity),
    total_usd: d(e.total_usd),
    timing_pct: e.timing_pct != null ? d(e.timing_pct) : null,
  }))

  const allPrices = lineData.map((p) => p.price).filter((p) => p > 0)
  const minPrice = allPrices.length ? Math.min(...allPrices) * 0.95 : 0
  const maxPrice = allPrices.length ? Math.max(...allPrices) * 1.05 : 0

  const xMin = lineData[0]?.ts ?? 0
  const xMax = lineData[lineData.length - 1]?.ts ?? 0

  const xTickFormatter = (ts: number) =>
    new Date(ts).toLocaleDateString("es-ES", { month: "short", year: "2-digit" })

  if (lineData.length === 0) {
    return (
      <div className="bg-surface border border-[var(--border)] rounded-xl p-6
                      flex flex-col items-center justify-center h-[320px]">
        <p className="text-secondary text-sm">Sin historial de precio aún</p>
        <p className="text-tertiary text-xs mt-1">
          Sincroniza para obtener datos históricos de BTCUSDT
        </p>
      </div>
    )
  }

  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-medium text-secondary">
          Precio BTC + compras realizadas
        </h2>
        <div className="flex items-center gap-4 text-xs text-tertiary">
          <span className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 bg-[#f97316] inline-block" />
            Precio
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 bg-[#3b82f6] inline-block" />
            MA50
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 bg-[#a855f7] inline-block" />
            MA200
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#22c55e] inline-block" />
            Compra
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 border-dashed border-t-2 border-[var(--text-tertiary)] inline-block" />
            VWAP
          </span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--border-subtle)"
            vertical={false}
          />

          <XAxis
            dataKey="ts"
            type="number"
            scale="time"
            domain={[xMin, xMax]}
            tick={{ fill: "var(--text-tertiary)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={xTickFormatter}
            tickCount={8}
          />

          <YAxis
            domain={[minPrice, maxPrice]}
            tick={{ fill: "var(--text-tertiary)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={formatPrice}
            width={56}
          />

          <Tooltip
            content={(props) => (
              <PriceChartTooltip {...props} maxQty={maxQty} />
            )}
          />

          {vwapUsd > 0 && (
            <ReferenceLine
              y={vwapUsd}
              stroke="var(--text-tertiary)"
              strokeDasharray="4 4"
              strokeWidth={1}
              label={{
                value: `VWAP $${vwapUsd.toLocaleString("es-ES", { maximumFractionDigits: 0 })}`,
                fill: "var(--text-tertiary)",
                fontSize: 10,
                position: "insideTopLeft",
              }}
            />
          )}

          {/* Precio BTC */}
          <Line
            data={lineData}
            dataKey="price"
            type="monotone"
            stroke="#f97316"
            strokeWidth={1.5}
            dot={false}
            activeDot={false}
          />

          {/* MA50 */}
          <Line
            data={lineData}
            dataKey="ma50"
            type="monotone"
            stroke="#3b82f6"
            strokeWidth={1}
            dot={false}
            activeDot={false}
            strokeOpacity={0.8}
            connectNulls={false}
          />

          {/* MA200 */}
          <Line
            data={lineData}
            dataKey="ma200"
            type="monotone"
            stroke="#a855f7"
            strokeWidth={1.5}
            dot={false}
            activeDot={false}
            strokeOpacity={0.9}
            connectNulls={false}
          />

          {/* Puntos de compra */}
          <Scatter
            data={scatterData}
            dataKey="price"
            shape={(props: any) => {
              const { cx, cy, payload } = props
              const r = maxQty > 0 ? 5 + (payload.quantity / maxQty) * 7 : 6
              // Color basado en timing: verde=buen timing, naranja=neutral, rojo=FOMO
              const tp = payload.timing_pct
              const fill =
                tp === null
                  ? "#22c55e"
                  : tp <= 33
                  ? "#22c55e"   // dip buyer — verde
                  : tp <= 66
                  ? "#f59e0b"   // neutral — ámbar
                  : "#ef4444"   // FOMO — rojo
              return (
                <circle
                  cx={cx}
                  cy={cy}
                  r={r}
                  fill={fill}
                  fillOpacity={0.8}
                  stroke={fill}
                  strokeWidth={1}
                  strokeOpacity={0.4}
                />
              )
            }}
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* Leyenda timing color */}
      <div className="flex items-center gap-4 mt-3 text-xs text-tertiary justify-end">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#22c55e] inline-block" />
          Dip (0-33%)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#f59e0b] inline-block" />
          Neutral (33-66%)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#ef4444] inline-block" />
          FOMO (66-100%)
        </span>
      </div>
    </div>
  )
}

function PriceChartTooltip({ active, payload, maxQty }: any) {
  if (!active || !payload?.length) return null
  const point = payload[0]?.payload

  const isScatter = "quantity" in point

  if (isScatter) {
    const tp = point.timing_pct
    const timingLabel =
      tp === null ? null
      : tp <= 33 ? `Dip buyer (${tp.toFixed(0)}%)`
      : tp <= 66 ? `Neutral (${tp.toFixed(0)}%)`
      : `FOMO (${tp.toFixed(0)}%)`
    const timingColor =
      tp === null ? "text-tertiary"
      : tp <= 33 ? "text-green-400"
      : tp <= 66 ? "text-amber-400"
      : "text-red-400"

    return (
      <div className="bg-elevated border border-[var(--border)] rounded-lg p-3
                      shadow-xl text-xs space-y-1">
        <p className="text-secondary font-medium">Compra BTC</p>
        <p className="text-tertiary">{formatDate(point.ts)}</p>
        <p className="text-primary tabular-nums font-semibold">
          ${point.price.toLocaleString("es-ES", { maximumFractionDigits: 0 })}
        </p>
        <p className="text-secondary tabular-nums">
          {point.quantity.toFixed(8)} BTC
        </p>
        <p className="text-tertiary tabular-nums">
          Total: ${point.total_usd.toFixed(2)}
        </p>
        {timingLabel && (
          <p className={`tabular-nums font-medium ${timingColor}`}>
            Timing: {timingLabel}
          </p>
        )}
      </div>
    )
  }

  return (
    <div className="bg-elevated border border-[var(--border)] rounded-lg p-3
                    shadow-xl text-xs space-y-1">
      <p className="text-tertiary">{formatDate(point.ts)}</p>
      <p className="text-primary tabular-nums font-semibold">
        ${point.price.toLocaleString("es-ES", { maximumFractionDigits: 0 })}
      </p>
      {point.ma50 != null && (
        <p className="text-[#3b82f6] tabular-nums text-[10px]">
          MA50: ${point.ma50.toLocaleString("es-ES", { maximumFractionDigits: 0 })}
        </p>
      )}
      {point.ma200 != null && (
        <p className="text-[#a855f7] tabular-nums text-[10px]">
          MA200: ${point.ma200.toLocaleString("es-ES", { maximumFractionDigits: 0 })}
        </p>
      )}
    </div>
  )
}

export function BtcPriceChartSkeleton() {
  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl p-6 animate-pulse">
      <div className="h-4 bg-elevated rounded w-64 mb-6" />
      <div className="h-[300px] bg-elevated rounded-lg" />
    </div>
  )
}
