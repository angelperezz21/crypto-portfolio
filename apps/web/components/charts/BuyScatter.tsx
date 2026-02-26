"use client"

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from "recharts"
import type { BtcBuyEventRaw } from "@/lib/types"
import { d } from "@/lib/formatters"

interface BuyScatterProps {
  buyEvents: BtcBuyEventRaw[]
  currentPriceUsd: number
  vwapUsd: number
}

interface ScatterDot {
  price: number
  gain_pct: number
  quantity: number
  date: string
  total_usd: number
}

function formatPct(v: number): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`
}

function formatPrice(v: number): string {
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}k`
  return `$${v.toFixed(0)}`
}

export function BuyScatter({ buyEvents, currentPriceUsd, vwapUsd }: BuyScatterProps) {
  if (!buyEvents.length || currentPriceUsd === 0) {
    return (
      <div className="bg-surface border border-[var(--border)] rounded-xl p-6
                      flex items-center justify-center h-[320px]">
        <p className="text-secondary text-sm">Sin datos de compras</p>
      </div>
    )
  }

  const dots: ScatterDot[] = buyEvents
    .filter((e) => d(e.price_usd) > 0)
    .map((e) => {
      const buyPrice = d(e.price_usd)
      const gain_pct = ((currentPriceUsd - buyPrice) / buyPrice) * 100
      return {
        price: buyPrice,
        gain_pct,
        quantity: d(e.quantity),
        date: e.date,
        total_usd: d(e.total_usd),
      }
    })

  const quantities = dots.map((d) => d.quantity)
  const maxQty = Math.max(...quantities, 0)

  const gains = dots.map((d) => d.gain_pct)
  const minGain = Math.min(...gains) * 1.15
  const maxGain = Math.max(...gains) * 1.15

  const prices = dots.map((d) => d.price)
  const minPrice = Math.min(...prices) * 0.92
  const maxPrice = Math.max(...prices) * 1.08

  const currentGainVsVwap = vwapUsd > 0
    ? ((currentPriceUsd - vwapUsd) / vwapUsd) * 100
    : 0

  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-medium text-secondary">Mapa de compras</h2>
          <p className="text-xs text-tertiary mt-0.5">
            Precio de entrada vs ganancia actual · tamaño = BTC comprado
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-tertiary">Precio actual</p>
          <p className="text-sm font-semibold text-primary tabular-nums">
            {formatPrice(currentPriceUsd)}
          </p>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <ScatterChart margin={{ top: 10, right: 16, bottom: 10, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />

          <XAxis
            type="number"
            dataKey="price"
            domain={[minPrice, maxPrice]}
            tick={{ fill: "var(--text-tertiary)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={formatPrice}
            tickCount={6}
            label={{
              value: "Precio de compra",
              fill: "var(--text-tertiary)",
              fontSize: 10,
              position: "insideBottomRight",
              offset: -8,
            }}
          />

          <YAxis
            type="number"
            dataKey="gain_pct"
            domain={[minGain, maxGain]}
            tick={{ fill: "var(--text-tertiary)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={formatPct}
            width={56}
            label={{
              value: "Ganancia actual",
              fill: "var(--text-tertiary)",
              fontSize: 10,
              angle: -90,
              position: "insideLeft",
              offset: 12,
            }}
          />

          <Tooltip content={<ScatterTooltip currentPrice={currentPriceUsd} />} />

          {/* Línea 0% */}
          <ReferenceLine
            y={0}
            stroke="var(--text-tertiary)"
            strokeWidth={1}
            strokeDasharray="3 3"
          />

          {/* Línea VWAP */}
          {vwapUsd > 0 && (
            <ReferenceLine
              x={vwapUsd}
              stroke="#6366f1"
              strokeWidth={1}
              strokeDasharray="4 4"
              label={{
                value: "VWAP",
                fill: "#6366f1",
                fontSize: 9,
                position: "insideTopRight",
              }}
            />
          )}

          <Scatter data={dots} shape={(props: any) => <BubbleDot {...props} maxQty={maxQty} />}>
            {dots.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.gain_pct >= 0 ? "#22c55e" : "#ef4444"}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>

      {/* Stats resumen */}
      <div className="flex items-center justify-center gap-6 text-xs text-tertiary pt-1 border-t border-[var(--border)]">
        <span>
          <span className="text-green-400 font-medium">
            {dots.filter((d) => d.gain_pct >= 0).length}
          </span>{" "}
          en beneficio
        </span>
        <span>
          <span className="text-red-400 font-medium">
            {dots.filter((d) => d.gain_pct < 0).length}
          </span>{" "}
          en pérdida
        </span>
        <span>
          Mejor:{" "}
          <span className="text-green-400 font-medium">
            {formatPct(Math.max(...gains))}
          </span>
        </span>
        <span>
          Peor:{" "}
          <span className="text-red-400 font-medium">
            {formatPct(Math.min(...gains))}
          </span>
        </span>
      </div>
    </div>
  )
}

function BubbleDot({ cx, cy, payload, maxQty }: any) {
  const r = maxQty > 0 ? 6 + (payload.quantity / maxQty) * 12 : 8
  const fill = payload.gain_pct >= 0 ? "#22c55e" : "#ef4444"
  return (
    <circle
      cx={cx}
      cy={cy}
      r={r}
      fill={fill}
      fillOpacity={0.65}
      stroke={fill}
      strokeWidth={1.5}
      strokeOpacity={0.3}
    />
  )
}

function ScatterTooltip({ active, payload, currentPrice }: any) {
  if (!active || !payload?.length) return null
  const p: ScatterDot = payload[0]?.payload
  if (!p) return null

  const dateStr = new Date(p.date).toLocaleDateString("es-ES", {
    day: "numeric", month: "short", year: "numeric",
  })

  return (
    <div className="bg-elevated border border-[var(--border)] rounded-lg p-3 shadow-xl text-xs space-y-1">
      <p className="text-secondary font-medium">Compra BTC</p>
      <p className="text-tertiary">{dateStr}</p>
      <p className="text-primary tabular-nums">
        Precio entrada: {formatPrice(p.price)}
      </p>
      <p className="text-secondary tabular-nums">
        Cantidad: {p.quantity.toFixed(8)} BTC
      </p>
      <p className="text-tertiary tabular-nums">
        Invertido: ${p.total_usd.toFixed(2)}
      </p>
      <p
        className={`font-semibold tabular-nums ${
          p.gain_pct >= 0 ? "text-green-400" : "text-red-400"
        }`}
      >
        Ganancia actual: {formatPct(p.gain_pct)}
      </p>
    </div>
  )
}

export function BuyScatterSkeleton() {
  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl p-6 animate-pulse space-y-4">
      <div className="flex justify-between">
        <div className="space-y-2">
          <div className="h-4 bg-elevated rounded w-36" />
          <div className="h-3 bg-elevated rounded w-56" />
        </div>
        <div className="h-8 bg-elevated rounded w-24" />
      </div>
      <div className="h-[260px] bg-elevated rounded-lg" />
    </div>
  )
}
