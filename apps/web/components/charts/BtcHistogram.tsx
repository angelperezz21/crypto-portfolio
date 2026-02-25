"use client"

import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts"
import type { BtcHistogramBucket } from "@/lib/types"
import { d } from "@/lib/formatters"

interface BtcHistogramProps {
  data: BtcHistogramBucket[]
  currentPriceUsd: number
}

const COLOR_PROFIT = "#10b981"
const COLOR_LOSS   = "#ef4444"

export function BtcHistogram({ data, currentPriceUsd }: BtcHistogramProps) {
  const chartData = data.map((b) => ({
    ...b,
    btc_qty: d(b.btc_quantity),
  }))

  const activeLabel = chartData.find(
    (b) => b.bucket_min <= currentPriceUsd && currentPriceUsd < b.bucket_max
  )?.label

  if (data.length === 0) {
    return (
      <div className="bg-surface border border-[var(--border)] rounded-xl p-6
                      flex flex-col items-center justify-center h-[300px]">
        <p className="text-secondary text-sm">Sin datos de distribución</p>
      </div>
    )
  }

  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-medium text-secondary">
          Distribución de BTC por precio de compra
        </h2>
        <div className="flex items-center gap-3 text-xs text-tertiary">
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#10b981] inline-block" />
            En beneficio
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#ef4444] inline-block" />
            En pérdida
          </span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={chartData}
          margin={{ top: 4, right: 8, bottom: 0, left: 0 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--border-subtle)"
            vertical={false}
          />

          <XAxis
            dataKey="label"
            tick={{ fill: "var(--text-tertiary)", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            interval={0}
            angle={-35}
            textAnchor="end"
            height={48}
          />

          <YAxis
            tick={{ fill: "var(--text-tertiary)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v.toFixed(4)}`}
            width={60}
          />

          <Tooltip
            content={(props) => (
              <HistogramTooltip {...props} currentPrice={currentPriceUsd} />
            )}
          />

          {activeLabel && (
            <ReferenceLine
              x={activeLabel}
              stroke="var(--text-secondary)"
              strokeWidth={2}
              label={{
                value: "Precio actual",
                fill: "var(--text-secondary)",
                fontSize: 10,
                position: "top",
              }}
            />
          )}

          <Bar dataKey="btc_qty" radius={[3, 3, 0, 0]}>
            {chartData.map((entry, idx) => (
              <Cell
                key={idx}
                fill={
                  entry.bucket_min < currentPriceUsd ? COLOR_PROFIT : COLOR_LOSS
                }
                fillOpacity={0.8}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function HistogramTooltip({ active, payload, currentPrice }: any) {
  if (!active || !payload?.length) return null
  const b = payload[0]?.payload as BtcHistogramBucket & { btc_qty: number }
  const inProfit = b.bucket_min < currentPrice

  return (
    <div className="bg-elevated border border-[var(--border)] rounded-lg p-3
                    shadow-xl text-xs space-y-1">
      <p className="text-secondary font-medium">{b.label}</p>
      <p className="text-primary tabular-nums font-semibold">
        {d(b.btc_quantity).toFixed(6)} BTC
      </p>
      <p className="text-tertiary tabular-nums">
        {b.buy_count} compra{b.buy_count !== 1 ? "s" : ""}
      </p>
      <p className={`font-semibold ${inProfit ? "text-positive" : "text-negative"}`}>
        {inProfit ? "En beneficio" : "En pérdida"}
      </p>
    </div>
  )
}

export function BtcHistogramSkeleton() {
  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl p-6 animate-pulse">
      <div className="h-4 bg-elevated rounded w-56 mb-6" />
      <div className="h-[260px] bg-elevated rounded-lg" />
    </div>
  )
}
