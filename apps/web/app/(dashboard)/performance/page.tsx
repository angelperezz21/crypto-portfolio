"use client"

import { useState, useEffect } from "react"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"
import { Topbar } from "@/components/layout/Topbar"
import { MetricCard, MetricCardSkeleton } from "@/components/dashboard/MetricCard"
import { PortfolioChart, PortfolioChartSkeleton } from "@/components/charts/PortfolioChart"
import { formatPercent, formatCurrency, d } from "@/lib/formatters"
import { cn } from "@/lib/utils"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

const RANGES = [
  { label: "7D",   days: 7   },
  { label: "30D",  days: 30  },
  { label: "90D",  days: 90  },
  { label: "1A",   days: 365 },
  { label: "Todo", days: 0   },
] as const

function getToken() {
  if (typeof window === "undefined") return null
  return localStorage.getItem("auth_token")
}

export default function PerformancePage() {
  const [range,    setRange]    = useState<(typeof RANGES)[number]>(RANGES[1])
  const [series,   setSeries]   = useState<any[]>([])
  const [drawdown, setDrawdown] = useState<any>(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const to   = new Date()
        const from = range.days > 0
          ? new Date(to.getTime() - range.days * 86_400_000)
          : new Date("2000-01-01")
        const params = new URLSearchParams({
          from_date: from.toISOString().slice(0, 10),
          to_date:   to.toISOString().slice(0, 10),
        })
        const res  = await fetch(
          `${API_BASE}/api/v1/dashboard/performance?${params}`,
          { headers: { Authorization: `Bearer ${getToken()}` } },
        )
        const json = await res.json()
        setSeries(json.data?.series ?? [])
        setDrawdown(json.data?.drawdown ?? null)
      } catch (e: any) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [range])

  const chartData = series.map((p: any) => ({
    date:     p.date,
    value:    d(p.total_value_eur ?? p.total_value_usd),
    invested: d(p.invested_eur    ?? p.invested_usd),
  }))

  const first   = chartData[0]?.value   ?? 0
  const last    = chartData.at(-1)?.value ?? 0
  const change  = first > 0 ? ((last - first) / first) * 100 : 0
  const maxDD   = drawdown ? d(drawdown.max_drawdown_pct) : 0

  return (
    <>
      <Topbar title="Rendimiento" subtitle="Evolución temporal del portafolio" />

      <div className="p-4 lg:p-6 space-y-4">

        {/* Selector de rango */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h2 className="text-sm font-medium text-secondary">Rango temporal</h2>
          <div className="flex gap-1 p-1 bg-elevated rounded-lg">
            {RANGES.map((r) => (
              <button
                key={r.label}
                onClick={() => setRange(r)}
                className={cn(
                  "px-3 py-1.5 text-xs font-medium rounded-md transition-all",
                  range.label === r.label
                    ? "bg-surface text-primary shadow-sm"
                    : "text-secondary hover:text-primary",
                )}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        {/* KPIs */}
        {loading
          ? (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[0,1,2].map(i => <MetricCardSkeleton key={i} />)}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <MetricCard
                label={`Variación (${range.label})`}
                value={formatPercent(change)}
                isPositive={change >= 0}
                icon={change >= 0 ? TrendingUp : TrendingDown}
              />
              <MetricCard
                label="Drawdown máximo"
                value={formatPercent(maxDD)}
                delta={drawdown?.peak_date ? `Pico: ${drawdown.peak_date}` : undefined}
                isPositive={false}
                icon={TrendingDown}
              />
              <MetricCard
                label="Valor final"
                value={last > 0 ? formatCurrency(last, "EUR") : "—"}
                delta={last > 0 ? `Inicio: ${formatCurrency(first, "EUR")}` : undefined}
                icon={Minus}
              />
            </div>
          )
        }

        {/* Gráfico */}
        {loading
          ? <PortfolioChartSkeleton />
          : error
          ? (
            <div className="bg-surface border border-[var(--border)] rounded-xl p-8
                            flex flex-col items-center justify-center">
              <p className="text-secondary text-sm">Error cargando datos</p>
              <p className="text-tertiary text-xs mt-1">{error}</p>
            </div>
          )
          : <PortfolioChart data={chartData} investedTotal={chartData[0]?.invested ?? 0} />
        }

      </div>
    </>
  )
}
