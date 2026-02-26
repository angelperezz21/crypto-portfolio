"use client"

import { useState, useEffect } from "react"
import { Zap, TrendingUp, TrendingDown, ShoppingCart, CheckCircle } from "lucide-react"
import { Topbar } from "@/components/layout/Topbar"
import { MetricCard, MetricCardSkeleton } from "@/components/dashboard/MetricCard"
import { BtcPriceChart, BtcPriceChartSkeleton } from "@/components/charts/BtcPriceChart"
import { BtcHistogram, BtcHistogramSkeleton } from "@/components/charts/BtcHistogram"
import { BtcHeatmap, BtcHeatmapSkeleton } from "@/components/dashboard/BtcHeatmap"
import { TimingScore, TimingScoreSkeleton } from "@/components/dashboard/TimingScore"
import { DcaSimulation, DcaSimulationSkeleton } from "@/components/charts/DcaSimulation"
import { BuyScatter, BuyScatterSkeleton } from "@/components/charts/BuyScatter"
import { fetchBtcInsights, fetchDcaSimulation } from "@/lib/api"
import { d, formatCurrency, formatPercent } from "@/lib/formatters"
import type { BtcInsightsData, DcaSimulationData } from "@/lib/types"

export default function BtcInsightsPage() {
  const [data,        setData]        = useState<BtcInsightsData | null>(null)
  const [simData,     setSimData]     = useState<DcaSimulationData | null>(null)
  const [simInterval, setSimInterval] = useState<"weekly" | "monthly">("weekly")
  const [simLoading,  setSimLoading]  = useState(false)
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState<string | null>(null)

  useEffect(() => {
    fetchBtcInsights()
      .then((res) => setData(res.data))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    setSimLoading(true)
    fetchDcaSimulation(simInterval)
      .then((res) => setSimData(res.data))
      .catch(() => {/* silencioso */})
      .finally(() => setSimLoading(false))
  }, [simInterval])

  const stats         = data?.stats
  const inProfitPct   = d(stats?.buys_in_profit_pct)
  const bestGain      = d(stats?.best_buy?.gain_pct)
  const worstGain     = d(stats?.worst_buy?.gain_pct)
  const currentPrice  = d(data?.current_price_usd)
  const vwap          = d(data?.vwap_usd)
  const totalBuys     = stats?.total_buys ?? 0

  const dateFirst = stats?.date_first_buy
    ? new Date(stats.date_first_buy).toLocaleDateString("es-ES", { month: "short", year: "numeric" })
    : null
  const dateLast = stats?.date_last_buy
    ? new Date(stats.date_last_buy).toLocaleDateString("es-ES", { month: "short", year: "numeric" })
    : null

  const bestBuyPrice  = d(stats?.best_buy?.price_usd)
  const worstBuyPrice = d(stats?.worst_buy?.price_usd)

  return (
    <>
      <Topbar title="Insights BTC" subtitle="Análisis de timing y distribución de tus compras" />

      <div className="p-4 lg:p-6 space-y-4">

        {/* ── Estado vacío / error ──────────────────────────────────────────── */}
        {loading ? (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
              {[0, 1, 2, 3].map((i) => <MetricCardSkeleton key={i} />)}
            </div>
            <BtcPriceChartSkeleton />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <TimingScoreSkeleton />
              <BuyScatterSkeleton />
            </div>
            <DcaSimulationSkeleton />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <BtcHistogramSkeleton />
              <BtcHeatmapSkeleton />
            </div>
          </>
        ) : error ? (
          <div className="bg-surface border border-[var(--border)] rounded-xl p-8
                          flex flex-col items-center justify-center">
            <p className="text-secondary text-sm">Error cargando datos</p>
            <p className="text-tertiary text-xs mt-1">{error}</p>
          </div>
        ) : totalBuys === 0 ? (
          <div className="bg-surface border border-[var(--border)] rounded-xl p-8
                          flex flex-col items-center justify-center">
            <Zap className="w-8 h-8 text-tertiary mb-3" />
            <p className="text-secondary text-sm">No hay compras de BTC registradas</p>
            <p className="text-tertiary text-xs mt-1">
              Configura tus API Keys y sincroniza para ver los insights
            </p>
          </div>
        ) : (
          <>
            {/* ── Metric cards ─────────────────────────────────────────────── */}
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
              <MetricCard
                label="Compras en beneficio"
                value={`${inProfitPct.toFixed(1)}%`}
                delta={`${stats?.buys_in_profit ?? 0} de ${totalBuys} compras`}
                isPositive={inProfitPct >= 50}
                icon={CheckCircle}
              />
              <MetricCard
                label="Mejor entrada"
                value={bestBuyPrice > 0 ? formatCurrency(bestBuyPrice, "USD") : "—"}
                delta={bestGain !== 0 ? `${formatPercent(bestGain)} vs hoy` : undefined}
                isPositive={bestGain >= 0}
                icon={TrendingUp}
              />
              <MetricCard
                label="Peor entrada"
                value={worstBuyPrice > 0 ? formatCurrency(worstBuyPrice, "USD") : "—"}
                delta={worstGain !== 0 ? `${formatPercent(worstGain)} vs hoy` : undefined}
                isPositive={worstGain >= 0}
                icon={TrendingDown}
              />
              <MetricCard
                label="Total compras"
                value={String(totalBuys)}
                delta={
                  dateFirst && dateLast
                    ? `${dateFirst} → ${dateLast}`
                    : undefined
                }
                icon={ShoppingCart}
              />
            </div>

            {/* ── Gráfico de precio + MA50/MA200 + compras ─────────────────── */}
            <BtcPriceChart
              priceHistory={data?.price_history ?? []}
              buyEvents={data?.buy_events ?? []}
              vwapUsd={vwap}
              currentPriceUsd={currentPrice}
            />

            {/* ── Timing score + Scatter plot ───────────────────────────────── */}
            {data?.timing_analysis && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <TimingScore
                  timing={data.timing_analysis}
                  totalBuys={totalBuys}
                />
                <BuyScatter
                  buyEvents={data.buy_events ?? []}
                  currentPriceUsd={currentPrice}
                  vwapUsd={vwap}
                />
              </div>
            )}

            {/* ── DCA real vs simulado ──────────────────────────────────────── */}
            {simLoading ? (
              <DcaSimulationSkeleton />
            ) : simData && simData.real.length > 0 ? (
              <DcaSimulation
                data={simData}
                interval={simInterval}
                onIntervalChange={setSimInterval}
                loading={simLoading}
              />
            ) : null}

            {/* ── Histograma + Heatmap ──────────────────────────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <BtcHistogram
                data={data?.price_histogram ?? []}
                currentPriceUsd={currentPrice}
              />
              <BtcHeatmap data={data?.monthly_heatmap ?? []} />
            </div>
          </>
        )}

      </div>
    </>
  )
}
