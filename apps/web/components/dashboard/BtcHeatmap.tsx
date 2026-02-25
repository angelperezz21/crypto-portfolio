"use client"

import type { BtcMonthlyCell } from "@/lib/types"
import { d } from "@/lib/formatters"

const MONTH_LABELS = [
  "Ene", "Feb", "Mar", "Abr", "May", "Jun",
  "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]

interface BtcHeatmapProps {
  data: BtcMonthlyCell[]
}

export function BtcHeatmap({ data }: BtcHeatmapProps) {
  if (data.length === 0) {
    return (
      <div className="bg-surface border border-[var(--border)] rounded-xl p-6
                      flex flex-col items-center justify-center h-[240px]">
        <p className="text-secondary text-sm">Sin datos de actividad mensual</p>
      </div>
    )
  }

  // Build lookup map
  const lookup = new Map<string, BtcMonthlyCell>()
  for (const cell of data) {
    lookup.set(`${cell.year}-${cell.month}`, cell)
  }

  const years = [...new Set(data.map((c) => c.year))].sort()
  const maxUsd = Math.max(...data.map((c) => d(c.total_usd)), 1)

  const getAlpha = (totalUsd: number) =>
    0.15 + (totalUsd / maxUsd) * 0.75

  const getColor = (totalUsd: number) =>
    `rgba(59, 130, 246, ${getAlpha(totalUsd).toFixed(2)})`

  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl p-6">
      <h2 className="text-sm font-medium text-secondary mb-4">
        Actividad mensual de compras BTC
      </h2>

      <div className="overflow-x-auto">
        {/* Month header */}
        <div
          className="grid gap-1 mb-1"
          style={{ gridTemplateColumns: "48px repeat(12, minmax(28px, 1fr))" }}
        >
          <div />
          {MONTH_LABELS.map((m) => (
            <div
              key={m}
              className="text-center text-[10px] text-tertiary font-medium"
            >
              {m}
            </div>
          ))}
        </div>

        {/* Year rows */}
        {years.map((year) => (
          <div
            key={year}
            className="grid gap-1 mb-1"
            style={{ gridTemplateColumns: "48px repeat(12, minmax(28px, 1fr))" }}
          >
            <div className="text-[11px] text-tertiary flex items-center pr-1">
              {year}
            </div>
            {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => {
              const cell = lookup.get(`${year}-${month}`)
              const totalUsd = cell ? d(cell.total_usd) : 0
              const hasBuys = !!cell

              return (
                <div
                  key={month}
                  className="rounded-sm aspect-square"
                  style={{
                    backgroundColor: hasBuys
                      ? getColor(totalUsd)
                      : "var(--bg-elevated, #1e2028)",
                    minHeight: "20px",
                  }}
                  title={
                    hasBuys && cell
                      ? `${MONTH_LABELS[month - 1]} ${year}: $${d(cell.total_usd).toFixed(2)} · ${cell.buy_count} compra${cell.buy_count !== 1 ? "s" : ""}`
                      : `${MONTH_LABELS[month - 1]} ${year}: sin actividad`
                  }
                />
              )
            })}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-2 mt-4">
        <span className="text-[10px] text-tertiary">Menos</span>
        {[0.15, 0.35, 0.55, 0.75, 0.90].map((alpha) => (
          <div
            key={alpha}
            className="w-4 h-4 rounded-sm"
            style={{ backgroundColor: `rgba(59, 130, 246, ${alpha})` }}
          />
        ))}
        <span className="text-[10px] text-tertiary">Más</span>
      </div>
    </div>
  )
}

export function BtcHeatmapSkeleton() {
  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl p-6 animate-pulse">
      <div className="h-4 bg-elevated rounded w-56 mb-6" />
      <div className="space-y-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-6 bg-elevated rounded" />
        ))}
      </div>
    </div>
  )
}
