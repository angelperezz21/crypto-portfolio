"use client"

import { useEffect, useState } from "react"
import {
  DollarSign, TrendingUp, TrendingDown, PiggyBank, Wallet,
} from "lucide-react"
import { MetricCard, MetricCardSkeleton } from "./MetricCard"
import { AssetTable, AssetTableSkeleton } from "./AssetTable"
import { PortfolioChart, PortfolioChartSkeleton } from "@/components/charts/PortfolioChart"
import { Topbar } from "@/components/layout/Topbar"
import { fetchOverview, fetchAssets, fetchLiquidBalance } from "@/lib/api"
import { formatCurrency, formatPercent, d } from "@/lib/formatters"
import type { OverviewData, OverviewMeta, AssetMetric } from "@/lib/types"

type LiquidItem = { asset: string; quantity: string; value_usd: string; value_eur: string }
type LiquidData = { total_liquid_usd: string; total_liquid_eur: string; items: LiquidItem[] }

export function OverviewContent() {
  const [overview, setOverview] = useState<OverviewData | null>(null)
  const [meta,     setMeta]     = useState<OverviewMeta | null>(null)
  const [assets,   setAssets]   = useState<AssetMetric[] | null>(null)
  const [liquid,   setLiquid]   = useState<LiquidData | null>(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const [ov, as, lq] = await Promise.all([
        fetchOverview(),
        fetchAssets(),
        fetchLiquidBalance(),
      ])
      setOverview(ov.data)
      setMeta(ov.meta as unknown as OverviewMeta)
      setAssets(as.data)
      setLiquid(lq.data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error cargando datos")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  // ── Computed values — USD ───────────────────────────────────────────────────
  const totalValueUsd  = d(overview?.total_value_usd)
  const investedUsd    = d(overview?.invested_usd)
  const pnlUnrealUsd   = d(overview?.pnl_unrealized_usd)
  const pnlRealUsd     = d(overview?.pnl_realized_usd)
  const roi            = d(overview?.roi_pct)
  const irr            = overview?.irr_annual_pct ? d(overview.irr_annual_pct) : null

  // ── Computed values — EUR ───────────────────────────────────────────────────
  const totalValueEur  = d(overview?.total_value_eur)
  const investedEur    = d(overview?.invested_eur)
  const pnlUnrealEur   = d(overview?.pnl_unrealized_eur)
  const pnlRealEur     = d(overview?.pnl_realized_eur)

  const pnlUnrealPct = investedUsd > 0
    ? ((pnlUnrealUsd / investedUsd) * 100)
    : 0

  // ── Chart data (en EUR) ─────────────────────────────────────────────────────
  const chartData = (overview?.evolution_90d ?? []).map((p) => ({
    date:     p.date,
    value:    d(p.total_value_eur ?? p.total_value_usd),
    invested: investedEur,        // referencia plana al capital en EUR
  }))

  // ── Subtitle ────────────────────────────────────────────────────────────────
  const subtitle = meta?.last_sync_at
    ? `Último sync: ${new Date(meta.last_sync_at).toLocaleString("es-ES")}`
    : "Sin sincronizar aún"

  // ── Error state ─────────────────────────────────────────────────────────────
  if (error) {
    return (
      <>
        <Topbar title="Overview" subtitle={subtitle} />
        <div className="p-6 flex flex-col items-center justify-center min-h-[60vh]">
          <p className="text-secondary mb-4">No se pudieron cargar los datos</p>
          <p className="text-xs text-tertiary mb-6">{error}</p>
          <button
            onClick={load}
            className="px-4 py-2 rounded-lg bg-accent text-white text-sm hover:bg-indigo-600 transition-colors"
          >
            Reintentar
          </button>
        </div>
      </>
    )
  }

  // ── Loading state ────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <>
        <Topbar title="Overview" />
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {Array.from({ length: 5 }).map((_, i) => <MetricCardSkeleton key={i} />)}
          </div>
          <PortfolioChartSkeleton />
          <AssetTableSkeleton />
        </div>
      </>
    )
  }

  const liquidTotal  = d(liquid?.total_liquid_eur)
  const liquidItems  = liquid?.items ?? []
  const liquidDelta  = liquidItems.length > 0
    ? liquidItems.map(i => `${i.asset} ${formatCurrency(d(i.value_eur), "EUR")}`).join(" · ")
    : undefined

  // ── Data state ───────────────────────────────────────────────────────────────
  return (
    <>
      <Topbar title="Overview" subtitle={subtitle} />

      <div className="p-4 lg:p-6 space-y-4">

        {/* ── MetricCards ─────────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">

          <MetricCard
            label="Valor del portafolio"
            value={formatCurrency(totalValueEur, "EUR")}
            subValue={formatCurrency(totalValueUsd) + " USD"}
            delta={irr !== null ? `IRR: ${formatPercent(irr)} anual` : undefined}
            isPositive={irr !== null ? irr >= 0 : undefined}
            icon={DollarSign}
          />

          <MetricCard
            label="P&L no realizado"
            value={formatCurrency(pnlUnrealEur, "EUR")}
            subValue={formatCurrency(pnlUnrealUsd) + " USD"}
            delta={formatPercent(pnlUnrealPct)}
            deltaLabel="sobre capital"
            isPositive={pnlUnrealUsd >= 0}
            icon={pnlUnrealUsd >= 0 ? TrendingUp : TrendingDown}
          />

          <MetricCard
            label="ROI total"
            value={formatPercent(roi)}
            delta={formatCurrency(pnlRealEur, "EUR")}
            deltaLabel={`P&L realizado · ${formatCurrency(pnlRealUsd)} USD`}
            isPositive={roi >= 0}
            icon={TrendingUp}
          />

        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

          <MetricCard
            label="Capital invertido"
            value={formatCurrency(investedEur, "EUR")}
            subValue={formatCurrency(investedUsd) + " USD"}
            icon={PiggyBank}
          />

          <MetricCard
            label="Saldo líquido en Binance"
            value={formatCurrency(liquidTotal, "EUR")}
            delta={liquidDelta}
            icon={Wallet}
          />

        </div>

        {/* ── Gráfico de área 90d ───────────────────────────────────────── */}
        <PortfolioChart data={chartData} investedTotal={investedEur} title="Evolución del portafolio — 90 días" />

        {/* ── Tabla de activos ─────────────────────────────────────────── */}
        <AssetTable assets={assets ?? []} />

      </div>
    </>
  )
}
