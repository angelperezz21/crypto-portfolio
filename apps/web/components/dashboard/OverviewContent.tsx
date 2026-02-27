"use client"

import { useEffect, useState } from "react"
import {
  DollarSign, TrendingUp, TrendingDown, PiggyBank, Wallet, Landmark,
} from "lucide-react"
import { MetricCard, MetricCardSkeleton } from "./MetricCard"
import { AssetTable, AssetTableSkeleton } from "./AssetTable"
import { PerformanceChart } from "./PerformanceChart"
import { Topbar } from "@/components/layout/Topbar"
import { fetchOverview, fetchAssets, fetchLiquidBalance } from "@/lib/api"
import { formatCurrency, formatPercent, d } from "@/lib/formatters"
import type { OverviewData, OverviewMeta, AssetMetric } from "@/lib/types"

type LiquidItem = { asset: string; quantity: string; value_usd: string; value_eur: string }
type LiquidData = { total_liquid_usd: string; total_liquid_eur: string; items: LiquidItem[] }

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-medium uppercase tracking-wider text-tertiary px-1">
      {children}
    </p>
  )
}

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

  const subtitle = meta?.last_sync_at
    ? `Último sync: ${new Date(meta.last_sync_at).toLocaleString("es-ES")}`
    : "Sin sincronizar aún"

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

  if (loading) {
    return (
      <>
        <Topbar title="Overview" />
        <div className="p-4 lg:p-6 space-y-6">
          <div className="space-y-2">
            <div className="h-3 bg-elevated rounded w-20 animate-pulse" />
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[0, 1, 2].map(i => <MetricCardSkeleton key={i} />)}
            </div>
          </div>
          <div className="space-y-2">
            <div className="h-3 bg-elevated rounded w-20 animate-pulse" />
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[0, 1, 2].map(i => <MetricCardSkeleton key={i} />)}
            </div>
          </div>
          <AssetTableSkeleton />
        </div>
      </>
    )
  }

  // ── Computed values ──────────────────────────────────────────────────────────
  const totalValueUsd     = d(overview?.total_value_usd)
  const investedUsd       = d(overview?.invested_usd)
  const pnlUnrealUsd      = d(overview?.pnl_unrealized_usd)
  const pnlRealUsd        = d(overview?.pnl_realized_usd)
  const roi               = d(overview?.roi_pct)
  const irr               = overview?.irr_annual_pct ? d(overview.irr_annual_pct) : null

  const totalValueEur     = d(overview?.total_value_eur)
  const investedEur       = d(overview?.invested_eur)
  const totalDepositedEur = d(overview?.total_deposited_eur)
  const feesEur           = d(overview?.fees_eur)
  const pnlUnrealEur      = d(overview?.pnl_unrealized_eur)
  const pnlRealEur        = d(overview?.pnl_realized_eur)

  const pnlUnrealPct = investedUsd > 0 ? (pnlUnrealUsd / investedUsd) * 100 : 0

  const liquidTotal = d(liquid?.total_liquid_eur)
  const liquidItems = liquid?.items ?? []
  const liquidDelta = liquidItems.length > 0
    ? liquidItems.map(i => `${i.asset} ${formatCurrency(d(i.value_eur), "EUR")}`).join(" · ")
    : undefined

  return (
    <>
      <Topbar title="Overview" subtitle={subtitle} />

      <div className="p-4 lg:p-6 space-y-6">

        {/* ── Sección: Resultados ─────────────────────────────────────────── */}
        <section className="space-y-2">
          <SectionLabel>Resultados</SectionLabel>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">

            <MetricCard
              label="Valor del portafolio"
              value={formatCurrency(totalValueEur, "EUR")}
              subValue={formatCurrency(totalValueUsd) + " USD"}
              delta={irr !== null ? `IRR ${formatPercent(irr)} anual` : undefined}
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
        </section>

        {/* ── Sección: Capital ────────────────────────────────────────────── */}
        <section className="space-y-2">
          <SectionLabel>Capital</SectionLabel>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">

            <MetricCard
              label="Capital invertido"
              value={formatCurrency(investedEur, "EUR")}
              subValue={formatCurrency(investedUsd) + " USD"}
              icon={PiggyBank}
            />

            <MetricCard
              label="Total aportado a Binance"
              value={formatCurrency(totalDepositedEur, "EUR")}
              subValue={formatCurrency(d(overview?.total_deposited_usd)) + " USD"}
              delta={feesEur > 0 ? `${formatCurrency(feesEur, "EUR")} en comisiones` : undefined}
              icon={Landmark}
            />

            <MetricCard
              label="Saldo líquido"
              value={formatCurrency(liquidTotal, "EUR")}
              delta={liquidDelta}
              icon={Wallet}
            />

          </div>
        </section>

        {/* ── Sección: Evolución ──────────────────────────────────────────── */}
        <section className="space-y-2">
          <SectionLabel>Evolución</SectionLabel>
          <PerformanceChart defaultRange="90D" showKpis={false} />
        </section>

        {/* ── Sección: Activos ────────────────────────────────────────────── */}
        <section className="space-y-2">
          <SectionLabel>Activos</SectionLabel>
          <AssetTable assets={assets ?? []} />
        </section>

      </div>
    </>
  )
}
