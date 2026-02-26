"use client"

import { useState } from "react"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import type { DcaSimulationData } from "@/lib/types"
import { formatCurrency } from "@/lib/formatters"

interface DcaSimulationProps {
  data: DcaSimulationData
  onIntervalChange: (interval: "weekly" | "monthly") => void
  interval: "weekly" | "monthly"
  loading?: boolean
}

interface MergedPoint {
  date: string
  ts: number
  real: number
  simulated: number
}

function buildMergedData(data: DcaSimulationData): MergedPoint[] {
  const simMap = new Map(data.simulated.map((p) => [p.date, parseFloat(p.btc_accumulated)]))
  const realMap = new Map(data.real.map((p) => [p.date, parseFloat(p.btc_accumulated)]))

  const allDates = Array.from(
    new Set([...data.simulated.map((p) => p.date), ...data.real.map((p) => p.date)])
  ).sort()

  let lastReal = 0
  let lastSim = 0

  return allDates.map((date) => {
    if (realMap.has(date)) lastReal = realMap.get(date)!
    if (simMap.has(date)) lastSim = simMap.get(date)!
    return {
      date,
      ts: new Date(date).getTime(),
      real: lastReal,
      simulated: lastSim,
    }
  })
}

function formatBtc(v: number): string {
  if (v === 0) return "0"
  if (v < 0.001) return v.toFixed(6)
  return v.toFixed(4)
}

export function DcaSimulation({ data, onIntervalChange, interval, loading }: DcaSimulationProps) {
  const merged = buildMergedData(data)
  const summary = data.summary
  const diffBtc = parseFloat(summary.diff_btc)
  const diffPct = parseFloat(summary.diff_pct)
  const isPositive = diffBtc >= 0

  const xTickFormatter = (ts: number) =>
    new Date(ts).toLocaleDateString("es-ES", { month: "short", year: "2-digit" })

  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-medium text-secondary">DCA real vs DCA perfecto</h2>
          <p className="text-xs text-tertiary mt-0.5">
            Mismo capital, distribuido en cuotas iguales {interval === "weekly" ? "semanales" : "mensuales"}
          </p>
        </div>

        {/* Toggle semanal / mensual */}
        <div className="flex items-center bg-elevated rounded-lg p-1 gap-1">
          {(["weekly", "monthly"] as const).map((iv) => (
            <button
              key={iv}
              onClick={() => onIntervalChange(iv)}
              disabled={loading}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                interval === iv
                  ? "bg-accent text-white"
                  : "text-tertiary hover:text-secondary"
              }`}
            >
              {iv === "weekly" ? "Semanal" : "Mensual"}
            </button>
          ))}
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-elevated rounded-lg p-3 text-center">
          <p className="text-xs text-tertiary mb-1">Tu acumulación real</p>
          <p className="text-base font-semibold text-primary tabular-nums">
            {formatBtc(parseFloat(summary.real_btc))} BTC
          </p>
        </div>
        <div className="bg-elevated rounded-lg p-3 text-center">
          <p className="text-xs text-tertiary mb-1">DCA perfecto</p>
          <p className="text-base font-semibold text-primary tabular-nums">
            {formatBtc(parseFloat(summary.simulated_btc))} BTC
          </p>
        </div>
        <div
          className={`rounded-lg p-3 text-center ${
            isPositive
              ? "bg-green-500/10 border border-green-500/20"
              : "bg-red-500/10 border border-red-500/20"
          }`}
        >
          <p className="text-xs text-tertiary mb-1">Tu ventaja</p>
          <p
            className={`text-base font-semibold tabular-nums ${
              isPositive ? "text-green-400" : "text-red-400"
            }`}
          >
            {isPositive ? "+" : ""}
            {formatBtc(diffBtc)} BTC
          </p>
          <p
            className={`text-[10px] tabular-nums ${
              isPositive ? "text-green-400" : "text-red-400"
            }`}
          >
            {isPositive ? "+" : ""}{diffPct.toFixed(1)}% ≈ {isPositive ? "+" : ""}
            {formatCurrency(Math.abs(parseFloat(summary.diff_value_eur)), "EUR")}
          </p>
        </div>
      </div>

      {/* Gráfico */}
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={merged} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="gradReal" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="gradSim" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#94a3b8" stopOpacity={0} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />

          <XAxis
            dataKey="ts"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            tick={{ fill: "var(--text-tertiary)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={xTickFormatter}
            tickCount={6}
          />

          <YAxis
            tick={{ fill: "var(--text-tertiary)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v.toFixed(3)}`}
            width={52}
          />

          <Tooltip content={<DcaTooltip />} />

          <Area
            type="monotone"
            dataKey="simulated"
            stroke="#94a3b8"
            strokeWidth={1.5}
            strokeDasharray="4 4"
            fill="url(#gradSim)"
            name="DCA perfecto"
          />
          <Area
            type="monotone"
            dataKey="real"
            stroke="#6366f1"
            strokeWidth={2}
            fill="url(#gradReal)"
            name="Tu DCA real"
          />
        </AreaChart>
      </ResponsiveContainer>

      <div className="flex items-center justify-center gap-6 text-xs text-tertiary">
        <span className="flex items-center gap-1.5">
          <span className="w-4 h-0.5 bg-[#6366f1] inline-block" />
          Tu DCA real
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="w-4 h-0.5 inline-block"
            style={{
              background: "repeating-linear-gradient(90deg, #94a3b8 0 4px, transparent 4px 8px)",
            }}
          />
          DCA perfecto
        </span>
      </div>
    </div>
  )
}

function DcaTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const ts = payload[0]?.payload?.ts
  const dateStr = ts
    ? new Date(ts).toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric" })
    : ""

  return (
    <div className="bg-elevated border border-[var(--border)] rounded-lg p-3 shadow-xl text-xs space-y-1">
      <p className="text-tertiary">{dateStr}</p>
      {payload.map((entry: any) => (
        <p key={entry.name} style={{ color: entry.stroke }} className="tabular-nums">
          {entry.name}: {parseFloat(entry.value).toFixed(6)} BTC
        </p>
      ))}
    </div>
  )
}

export function DcaSimulationSkeleton() {
  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl p-6 animate-pulse space-y-4">
      <div className="flex justify-between">
        <div className="space-y-2">
          <div className="h-4 bg-elevated rounded w-48" />
          <div className="h-3 bg-elevated rounded w-64" />
        </div>
        <div className="h-8 bg-elevated rounded-lg w-36" />
      </div>
      <div className="grid grid-cols-3 gap-3">
        {[0, 1, 2].map((i) => <div key={i} className="h-16 bg-elevated rounded-lg" />)}
      </div>
      <div className="h-[220px] bg-elevated rounded-lg" />
    </div>
  )
}
