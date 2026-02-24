"use client"

import { useState, useEffect, useCallback } from "react"
import { Download, ChevronLeft, ChevronRight } from "lucide-react"
import { Topbar } from "@/components/layout/Topbar"
import { Button } from "@/components/ui/button"
import { AssetTableSkeleton } from "@/components/dashboard/AssetTable"
import { formatCurrency, formatCrypto, d } from "@/lib/formatters"
import { cn } from "@/lib/utils"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
function getToken() {
  if (typeof window === "undefined") return null
  return localStorage.getItem("auth_token")
}

const TYPE_BADGE: Record<string, string> = {
  buy:            "bg-positive/10 text-positive border-positive/20",
  sell:           "bg-negative/10 text-negative border-negative/20",
  deposit:        "bg-blue-500/10 text-blue-400 border-blue-500/20",
  withdrawal:     "bg-orange-500/10 text-orange-400 border-orange-500/20",
  convert:        "bg-violet-500/10 text-violet-400 border-violet-500/20",
  earn_interest:  "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  staking_reward: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
}

const TYPE_LABELS: Record<string, string> = {
  buy:            "Compra",
  sell:           "Venta",
  deposit:        "Depósito",
  withdrawal:     "Retiro",
  convert:        "Conversión",
  earn_interest:  "Earn",
  staking_reward: "Staking",
}

export default function TransactionsPage() {
  const [txs,     setTxs]     = useState<any[]>([])
  const [page,    setPage]     = useState(1)
  const [total,   setTotal]    = useState(0)
  const [pages,   setPages]    = useState(1)
  const [loading, setLoading]  = useState(true)
  const [filter,  setFilter]   = useState("")
  const [typeF,   setTypeF]    = useState("")

  const LIMIT = 20

  const load = useCallback(async (p: number) => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: String(p), limit: String(LIMIT) })
      if (typeF)  params.set("type",  typeF)
      if (filter) params.set("asset", filter.toUpperCase())

      const res  = await fetch(`${API_BASE}/api/v1/transactions?${params}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      const json = await res.json()
      setTxs(json.data  ?? [])
      setTotal(json.meta?.total ?? 0)
      setPages(json.meta?.pages ?? 1)
    } finally {
      setLoading(false)
    }
  }, [typeF, filter])

  useEffect(() => { setPage(1); load(1) }, [typeF, filter, load])
  useEffect(() => { load(page) }, [page, load])

  function exportCsv() {
    const params = new URLSearchParams()
    if (typeF)  params.set("type",  typeF)
    if (filter) params.set("asset", filter.toUpperCase())
    const url = `${API_BASE}/api/v1/transactions/export?${params}`
    const a   = document.createElement("a")
    a.href    = url
    a.setAttribute("download", "transacciones.csv")
    // Añade el token como query param no es ideal — en prod usar cookie httpOnly
    a.href = url + "&token=" + (getToken() ?? "")
    a.click()
  }

  return (
    <>
      <Topbar title="Transacciones" subtitle={`${total} operaciones en total`} />

      <div className="p-4 lg:p-6 space-y-4">

        {/* Filtros */}
        <div className="flex flex-wrap gap-3 items-center">
          <input
            type="text"
            placeholder="Filtrar por activo (BTC, ETH…)"
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="px-3 py-2 text-sm rounded-lg bg-surface border border-[var(--border)]
                       text-primary placeholder:text-tertiary
                       focus:outline-none focus:ring-2 focus:ring-accent/50 w-56"
          />
          <select
            value={typeF}
            onChange={e => setTypeF(e.target.value)}
            className="px-3 py-2 text-sm rounded-lg bg-surface border border-[var(--border)]
                       text-primary focus:outline-none focus:ring-2 focus:ring-accent/50"
          >
            <option value="">Todos los tipos</option>
            {Object.entries(TYPE_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
          <div className="ml-auto">
            <Button variant="outline" size="sm" onClick={exportCsv} className="gap-2">
              <Download className="w-3.5 h-3.5" />
              Exportar CSV
            </Button>
          </div>
        </div>

        {/* Tabla */}
        {loading ? (
          <AssetTableSkeleton />
        ) : txs.length === 0 ? (
          <div className="bg-surface border border-[var(--border)] rounded-xl p-8
                          flex flex-col items-center justify-center">
            <p className="text-secondary text-sm">No hay transacciones</p>
            <p className="text-tertiary text-xs mt-1">
              Sincroniza tu cuenta para importar el historial
            </p>
          </div>
        ) : (
          <div className="bg-surface border border-[var(--border)] rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)]">
                    {["Fecha", "Tipo", "Activo", "Cantidad", "Precio", "Total USD"].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-medium
                                              uppercase tracking-wider text-tertiary
                                              first:pl-6 last:pr-6">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {txs.map((tx: any) => (
                    <tr key={tx.id}
                        className="border-b border-[var(--border-subtle)] last:border-0
                                   hover:bg-hover transition-colors">
                      <td className="pl-6 pr-4 py-3 text-xs text-secondary tabular-nums whitespace-nowrap">
                        {new Date(tx.executed_at).toLocaleString("es-ES", {
                          day: "2-digit", month: "short", year: "2-digit",
                          hour: "2-digit", minute: "2-digit",
                        })}
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn(
                          "text-xs px-2 py-0.5 rounded-full border font-medium",
                          TYPE_BADGE[tx.type] ?? "bg-elevated text-secondary border-[var(--border)]",
                        )}>
                          {TYPE_LABELS[tx.type] ?? tx.type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm font-medium text-primary">
                        {tx.base_asset}
                        {tx.quote_asset && (
                          <span className="text-tertiary font-normal">/{tx.quote_asset}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm tabular-nums text-secondary">
                        {formatCrypto(d(tx.quantity))}
                      </td>
                      <td className="px-4 py-3 text-sm tabular-nums text-secondary">
                        {tx.price ? formatCurrency(d(tx.price)) : "—"}
                      </td>
                      <td className="pr-6 pl-4 py-3 text-sm tabular-nums text-primary font-medium">
                        {tx.total_value_usd ? formatCurrency(d(tx.total_value_usd)) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Paginación */}
            {pages > 1 && (
              <div className="px-6 py-3 border-t border-[var(--border-subtle)]
                              flex items-center justify-between">
                <span className="text-xs text-tertiary">
                  Página {page} de {pages} · {total} registros
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="ghost" size="sm"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost" size="sm"
                    onClick={() => setPage(p => Math.min(pages, p + 1))}
                    disabled={page === pages}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  )
}
