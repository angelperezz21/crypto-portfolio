import { cn } from "@/lib/utils"
import { formatCurrency, formatPercent, formatCrypto, d } from "@/lib/formatters"
import type { AssetMetric } from "@/lib/types"

interface AssetTableProps {
  assets: AssetMetric[]
}

export function AssetTable({ assets }: AssetTableProps) {
  if (assets.length === 0) {
    return (
      <div className="bg-surface border border-[var(--border)] rounded-xl p-8
                      flex flex-col items-center justify-center">
        <p className="text-secondary text-sm">No hay activos en cartera</p>
        <p className="text-tertiary text-xs mt-1">
          Sincroniza tu cuenta para ver tus balances
        </p>
      </div>
    )
  }

  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-[var(--border-subtle)]">
        <h2 className="text-sm font-medium text-primary">Activos en cartera</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[var(--border-subtle)]">
              {["Activo", "Cantidad", "Valor", "% Cartera", "P. Medio Compra", "P&L", "P&L %"].map(
                (h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-xs font-medium uppercase
                               tracking-wider text-tertiary first:pl-6 last:pr-6"
                  >
                    {h}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {assets.map((a) => {
              const pnlEur = d(a.pnl_eur)
              const pnlUsd = d(a.pnl_usd)
              const pnlPct = d(a.pnl_pct)
              const isPos  = pnlEur >= 0

              return (
                <tr
                  key={a.asset}
                  className="border-b border-[var(--border-subtle)] last:border-0
                             hover:bg-hover transition-colors"
                >
                  {/* Activo */}
                  <td className="pl-6 pr-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-elevated flex items-center
                                      justify-center text-xs font-bold text-primary">
                        {a.asset.slice(0, 2)}
                      </div>
                      <span className="text-sm font-medium text-primary">{a.asset}</span>
                    </div>
                  </td>

                  {/* Cantidad */}
                  <td className="px-4 py-3 text-sm tabular-nums text-secondary">
                    {formatCrypto(d(a.quantity))}
                  </td>

                  {/* Valor — EUR primario, USD secundario */}
                  <td className="px-4 py-3">
                    <div className="text-sm tabular-nums text-primary font-medium">
                      {formatCurrency(d(a.value_eur), "EUR")}
                    </div>
                    <div className="text-xs tabular-nums text-tertiary mt-0.5">
                      {formatCurrency(d(a.value_usd))} USD
                    </div>
                  </td>

                  {/* % Cartera */}
                  <td className="px-4 py-3 text-sm tabular-nums text-secondary">
                    {d(a.portfolio_pct).toFixed(2)}%
                  </td>

                  {/* Precio medio — EUR primario, USD secundario */}
                  <td className="px-4 py-3">
                    {d(a.avg_buy_price_eur) > 0 ? (
                      <>
                        <div className="text-sm tabular-nums text-secondary">
                          {formatCurrency(d(a.avg_buy_price_eur), "EUR")}
                        </div>
                        <div className="text-xs tabular-nums text-tertiary mt-0.5">
                          {formatCurrency(d(a.avg_buy_price_usd))} USD
                        </div>
                      </>
                    ) : (
                      <span className="text-sm text-tertiary">—</span>
                    )}
                  </td>

                  {/* P&L absoluto — EUR primario, USD secundario */}
                  <td className="px-4 py-3">
                    <div className={cn(
                      "text-sm tabular-nums font-medium",
                      isPos ? "text-positive" : "text-negative",
                    )}>
                      {pnlEur >= 0 ? "+" : ""}{formatCurrency(pnlEur, "EUR")}
                    </div>
                    <div className="text-xs tabular-nums text-tertiary mt-0.5">
                      {pnlUsd >= 0 ? "+" : ""}{formatCurrency(pnlUsd)} USD
                    </div>
                  </td>

                  {/* P&L % */}
                  <td className={cn(
                    "pr-6 pl-4 py-3 text-sm tabular-nums font-semibold",
                    isPos ? "text-positive" : "text-negative",
                  )}>
                    {formatPercent(pnlPct)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function AssetTableSkeleton() {
  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl overflow-hidden animate-pulse">
      <div className="px-6 py-4 border-b border-[var(--border-subtle)]">
        <div className="h-4 bg-elevated rounded w-36" />
      </div>
      <div className="p-6 space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4">
            <div className="w-7 h-7 rounded-full bg-elevated" />
            <div className="h-4 bg-elevated rounded flex-1" />
            <div className="h-4 bg-elevated rounded w-24" />
            <div className="h-4 bg-elevated rounded w-16" />
          </div>
        ))}
      </div>
    </div>
  )
}
