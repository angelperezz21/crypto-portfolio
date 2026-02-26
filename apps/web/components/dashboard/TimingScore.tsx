"use client"

import type { BtcTimingAnalysis } from "@/lib/types"

interface TimingScoreProps {
  timing: BtcTimingAnalysis
  totalBuys: number
}

export function TimingScore({ timing, totalBuys }: TimingScoreProps) {
  const avg = timing.avg_percentile != null ? parseFloat(timing.avg_percentile) : null
  const { q1, q2, q3, q4 } = timing.distribution
  const total = q1 + q2 + q3 + q4 || 1

  const barData = [
    { label: "Dip (0-25%)", count: q1, color: "#22c55e", bg: "bg-[#22c55e]" },
    { label: "Bajo (25-50%)", count: q2, color: "#84cc16", bg: "bg-[#84cc16]" },
    { label: "Alto (50-75%)", count: q3, color: "#f59e0b", bg: "bg-[#f59e0b]" },
    { label: "FOMO (75-100%)", count: q4, color: "#ef4444", bg: "bg-[#ef4444]" },
  ]

  const scoreBg =
    avg === null ? "from-slate-500/20 to-slate-500/5"
    : avg <= 33 ? "from-green-500/20 to-green-500/5"
    : avg <= 66 ? "from-amber-500/20 to-amber-500/5"
    : "from-red-500/20 to-red-500/5"

  const scoreColor =
    avg === null ? "text-secondary"
    : avg <= 33 ? "text-green-400"
    : avg <= 66 ? "text-amber-400"
    : "text-red-400"

  const labelEmoji =
    timing.label === "Dip Buyer" ? "🎯"
    : timing.label === "FOMO Buyer" ? "📈"
    : "⚖️"

  const ma200Total = timing.buys_below_ma200 + timing.buys_above_ma200

  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl p-6 space-y-5">
      <h2 className="text-sm font-medium text-secondary">Análisis de timing de compras</h2>

      {/* Score principal */}
      <div className={`bg-gradient-to-br ${scoreBg} rounded-xl p-4 flex items-center gap-4`}>
        {/* Gauge visual */}
        <div className="relative w-20 h-20 flex-shrink-0">
          <svg viewBox="0 0 80 80" className="w-full h-full -rotate-90">
            <circle cx="40" cy="40" r="32" fill="none" stroke="var(--border)" strokeWidth="8" />
            <circle
              cx="40" cy="40" r="32"
              fill="none"
              stroke={avg === null ? "#64748b" : avg <= 33 ? "#22c55e" : avg <= 66 ? "#f59e0b" : "#ef4444"}
              strokeWidth="8"
              strokeDasharray={`${2 * Math.PI * 32}`}
              strokeDashoffset={`${2 * Math.PI * 32 * (1 - (avg ?? 50) / 100)}`}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={`text-lg font-bold tabular-nums ${scoreColor}`}>
              {avg !== null ? Math.round(avg) : "—"}
            </span>
          </div>
        </div>

        <div>
          <p className="text-xs text-tertiary mb-1">Percentil medio de compra</p>
          <p className={`text-xl font-semibold ${scoreColor}`}>
            {labelEmoji} {timing.label}
          </p>
          <p className="text-xs text-tertiary mt-1">
            {avg !== null && avg <= 33
              ? "Tiendes a comprar en caídas. Buen ojo."
              : avg !== null && avg >= 67
              ? "Tiendes a comprar en máximos mensuales."
              : "Compras de forma bastante equilibrada."}
          </p>
        </div>
      </div>

      {/* Distribución de compras */}
      <div className="space-y-2">
        <p className="text-xs text-tertiary font-medium">Distribución de {total} compras</p>
        {barData.map((bar) => {
          const pct = (bar.count / total) * 100
          return (
            <div key={bar.label} className="flex items-center gap-2">
              <span className="text-xs text-tertiary w-28 flex-shrink-0">{bar.label}</span>
              <div className="flex-1 bg-elevated rounded-full h-2 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500`}
                  style={{ width: `${pct}%`, backgroundColor: bar.color }}
                />
              </div>
              <span className="text-xs tabular-nums text-secondary w-8 text-right">
                {bar.count}
              </span>
            </div>
          )
        })}
      </div>

      {/* MA200 context */}
      {ma200Total > 0 && (
        <div className="border-t border-[var(--border)] pt-4 grid grid-cols-2 gap-3">
          <div className="bg-elevated rounded-lg p-3 text-center">
            <p className="text-lg font-semibold text-green-400 tabular-nums">
              {timing.buys_below_ma200}
            </p>
            <p className="text-xs text-tertiary mt-0.5">bajo MA200</p>
            <p className="text-[10px] text-tertiary">bull market</p>
          </div>
          <div className="bg-elevated rounded-lg p-3 text-center">
            <p className="text-lg font-semibold text-amber-400 tabular-nums">
              {timing.buys_above_ma200}
            </p>
            <p className="text-xs text-tertiary mt-0.5">sobre MA200</p>
            <p className="text-[10px] text-tertiary">bear market</p>
          </div>
        </div>
      )}
    </div>
  )
}

export function TimingScoreSkeleton() {
  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl p-6 animate-pulse space-y-4">
      <div className="h-4 bg-elevated rounded w-48" />
      <div className="h-24 bg-elevated rounded-xl" />
      <div className="space-y-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="h-3 bg-elevated rounded w-28" />
            <div className="flex-1 h-2 bg-elevated rounded-full" />
            <div className="h-3 bg-elevated rounded w-6" />
          </div>
        ))}
      </div>
    </div>
  )
}
