"use client"

import { useState, useEffect } from "react"
import { Bitcoin, TrendingUp, ShoppingCart, BarChart2 } from "lucide-react"
import { Topbar } from "@/components/layout/Topbar"
import { MetricCard, MetricCardSkeleton } from "@/components/dashboard/MetricCard"
import { formatCurrency, formatPercent, formatSats, formatCrypto, d } from "@/lib/formatters"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
function getToken() {
  if (typeof window === "undefined") return null
  return localStorage.getItem("auth_token")
}

export default function DcaPage() {
  const [data,    setData]    = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const res  = await fetch(`${API_BASE}/api/v1/dashboard/dca/BTC`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
        const json = await res.json()
        setData(json.data)
      } catch (e: any) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const currentPrice = d(data?.current_price_eur)
  const vwap         = d(data?.vwap_eur)
  const totalQty     = d(data?.total_quantity)
  const pnlPct       = d(data?.pnl_pct)
  const costBasis    = d(data?.cost_basis_eur)
  const pnlEur       = d(data?.pnl_eur)

  return (
    <>
      <Topbar title="DCA Bitcoin" subtitle="Análisis de tu estrategia de compra periódica" />

      <div className="p-4 lg:p-6 space-y-4">

        {/* KPIs */}
        {loading
          ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
              {[0,1,2,3].map(i => <MetricCardSkeleton key={i} />)}
            </div>
          ) : error ? (
            <div className="bg-surface border border-[var(--border)] rounded-xl p-8
                            flex flex-col items-center justify-center">
              <p className="text-secondary text-sm">Error cargando datos DCA</p>
              <p className="text-tertiary text-xs mt-1">{error}</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                <MetricCard
                  label="Sats acumuladas"
                  value={totalQty > 0 ? formatSats(totalQty) : "0 sats"}
                  delta={totalQty > 0 ? `${formatCrypto(totalQty, 8)} BTC` : undefined}
                  icon={Bitcoin}
                />
                <MetricCard
                  label="Precio medio compra"
                  value={vwap > 0 ? formatCurrency(vwap, "EUR") : "—"}
                  delta={currentPrice > 0 && vwap > 0
                    ? `Precio actual: ${formatCurrency(currentPrice, "EUR")}`
                    : undefined}
                  isPositive={currentPrice >= vwap}
                  icon={BarChart2}
                />
                <MetricCard
                  label="P&L no realizado"
                  value={formatCurrency(pnlEur, "EUR")}
                  delta={formatPercent(pnlPct)}
                  isPositive={pnlEur >= 0}
                  icon={TrendingUp}
                />
                <MetricCard
                  label="Compras realizadas"
                  value={String(data?.total_events ?? 0)}
                  delta={costBasis > 0 ? `Capital: ${formatCurrency(costBasis, "EUR")}` : undefined}
                  icon={ShoppingCart}
                />
              </div>

              {/* Tabla de compras */}
              {data?.buy_events?.length > 0 && (
                <div className="bg-surface border border-[var(--border)] rounded-xl overflow-hidden">
                  <div className="px-6 py-4 border-b border-[var(--border-subtle)]">
                    <h2 className="text-sm font-medium text-primary">Historial de compras BTC</h2>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-[var(--border-subtle)]">
                          {["Fecha", "Cantidad BTC", "Precio", "VWAP acumulado"].map(h => (
                            <th key={h} className="px-4 py-3 text-left text-xs font-medium
                                                    uppercase tracking-wider text-tertiary
                                                    first:pl-6 last:pr-6">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {data.buy_events.map((e: any, i: number) => (
                          <tr key={i} className="border-b border-[var(--border-subtle)] last:border-0
                                                   hover:bg-hover transition-colors">
                            <td className="pl-6 pr-4 py-3 text-sm text-secondary">
                              {new Date(e.date).toLocaleDateString("es-ES")}
                            </td>
                            <td className="px-4 py-3 text-sm tabular-nums font-medium text-primary">
                              {formatCrypto(d(e.quantity), 8)}
                            </td>
                            <td className="px-4 py-3 text-sm tabular-nums text-secondary">
                              {formatCurrency(d(e.price_eur), "EUR")}
                            </td>
                            <td className="pr-6 pl-4 py-3 text-sm tabular-nums text-accent">
                              {formatCurrency(d(e.cumulative_vwap_eur), "EUR")}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {data?.total_events === 0 && (
                <div className="bg-surface border border-[var(--border)] rounded-xl p-8
                                flex flex-col items-center justify-center">
                  <Bitcoin className="w-8 h-8 text-tertiary mb-3" />
                  <p className="text-secondary text-sm">No hay compras de BTC registradas</p>
                  <p className="text-tertiary text-xs mt-1">
                    Configura tus API Keys y sincroniza para ver tu historial DCA
                  </p>
                </div>
              )}
            </>
          )
        }
      </div>
    </>
  )
}
