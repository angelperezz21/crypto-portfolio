"use client"

import { useState, useEffect } from "react"
import { FileText, TrendingUp, TrendingDown } from "lucide-react"
import { Topbar } from "@/components/layout/Topbar"
import { MetricCard, MetricCardSkeleton } from "@/components/dashboard/MetricCard"
import { formatCurrency, formatPercent, d } from "@/lib/formatters"
import { cn } from "@/lib/utils"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
function getToken() {
  if (typeof window === "undefined") return null
  return localStorage.getItem("auth_token")
}

const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: 5 }, (_, i) => CURRENT_YEAR - i)

export default function FiscalPage() {
  const [year,    setYear]    = useState(CURRENT_YEAR)
  const [data,    setData]    = useState<any>(null)
  const [meta,    setMeta]    = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const res  = await fetch(`${API_BASE}/api/v1/fiscal/${year}`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
        const json = await res.json()
        setData(json.data)
        setMeta(json.meta)
      } catch (e: any) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [year])

  const totalPnl  = d(data?.total_realized_pnl_usd)
  const isPos     = totalPnl >= 0
  const assets    = data?.assets ?? []

  return (
    <>
      <Topbar title="Fiscal" subtitle="P&L realizado por año fiscal (método FIFO)" />

      <div className="p-4 lg:p-6 space-y-4">

        {/* Selector de año */}
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-sm text-secondary">Año fiscal:</span>
          <div className="flex gap-1 p-1 bg-elevated rounded-lg">
            {YEARS.map(y => (
              <button
                key={y}
                onClick={() => setYear(y)}
                className={cn(
                  "px-3 py-1.5 text-xs font-medium rounded-md transition-all",
                  year === y
                    ? "bg-surface text-primary shadow-sm"
                    : "text-secondary hover:text-primary",
                )}
              >
                {y}
              </button>
            ))}
          </div>
        </div>

        {/* KPIs */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[0,1,2].map(i => <MetricCardSkeleton key={i} />)}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <MetricCard
              label={`P&L realizado ${year}`}
              value={formatCurrency(totalPnl)}
              isPositive={isPos}
              icon={isPos ? TrendingUp : TrendingDown}
            />
            <MetricCard
              label="Activos con ventas"
              value={String(assets.length)}
              delta={meta ? `${meta.sell_events_in_year} operaciones de venta` : undefined}
              icon={FileText}
            />
            <MetricCard
              label="Lotes de compra usados"
              value={meta ? String(meta.buy_lots_used) : "—"}
              delta="Método FIFO"
              icon={FileText}
            />
          </div>
        )}

        {/* Aviso fiscal */}
        {!loading && (
          <div className="px-4 py-3 rounded-lg bg-warning/5 border border-warning/20
                          text-xs text-secondary">
            ⚠️ {meta?.note ?? "El P&L realizado puede diferir de las obligaciones fiscales reales. Consulta a un asesor fiscal."}
          </div>
        )}

        {/* Detalle por activo */}
        {!loading && assets.length > 0 && (
          <div className="bg-surface border border-[var(--border)] rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-[var(--border-subtle)]">
              <h2 className="text-sm font-medium text-primary">Detalle por activo — {year}</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)]">
                    {["Activo", "Cantidad vendida", "Ingresos USD", "P&L realizado", "Operaciones"].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-medium
                                              uppercase tracking-wider text-tertiary
                                              first:pl-6 last:pr-6">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {assets.map((a: any) => {
                    const pnl   = d(a.realized_pnl_usd)
                    const isPos = pnl >= 0
                    return (
                      <tr key={a.asset}
                          className="border-b border-[var(--border-subtle)] last:border-0
                                     hover:bg-hover transition-colors">
                        <td className="pl-6 pr-4 py-3 text-sm font-medium text-primary">
                          {a.asset}
                        </td>
                        <td className="px-4 py-3 text-sm tabular-nums text-secondary">
                          {d(a.total_sold).toFixed(8)}
                        </td>
                        <td className="px-4 py-3 text-sm tabular-nums text-secondary">
                          {formatCurrency(d(a.total_proceeds_usd))}
                        </td>
                        <td className={cn(
                          "px-4 py-3 text-sm tabular-nums font-semibold",
                          isPos ? "text-positive" : "text-negative",
                        )}>
                          {pnl >= 0 ? "+" : ""}{formatCurrency(pnl)}
                        </td>
                        <td className="pr-6 pl-4 py-3 text-sm tabular-nums text-secondary">
                          {a.sell_events}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!loading && assets.length === 0 && !error && (
          <div className="bg-surface border border-[var(--border)] rounded-xl p-8
                          flex flex-col items-center justify-center">
            <FileText className="w-8 h-8 text-tertiary mb-3" />
            <p className="text-secondary text-sm">Sin ventas registradas en {year}</p>
            <p className="text-tertiary text-xs mt-1">
              Las ganancias/pérdidas realizadas aparecen aquí cuando hay operaciones de venta
            </p>
          </div>
        )}

      </div>
    </>
  )
}
