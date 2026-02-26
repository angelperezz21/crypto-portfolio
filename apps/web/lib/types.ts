export interface ApiResponse<T> {
  data: T
  error: string | null
  meta: Record<string, unknown>
}

export type SyncStatus = "idle" | "syncing" | "error"

// ─── /api/v1/dashboard/overview ──────────────────────────────────────────────

export interface TopAsset {
  asset: string
  value_usd: string
  portfolio_pct: string
  pnl_pct: string
}

export interface EvolutionPoint {
  date: string
  total_value_usd: string
  total_value_eur?: string
}

export interface OverviewData {
  total_value_usd: string
  total_value_eur: string
  invested_usd: string
  invested_eur: string
  pnl_unrealized_usd: string
  pnl_unrealized_eur: string
  pnl_realized_usd: string
  pnl_realized_eur: string
  roi_pct: string
  irr_annual_pct: string | null
  eur_usd_rate: string
  top_assets: TopAsset[]
  evolution_90d: EvolutionPoint[]
}

export interface OverviewMeta {
  account_name: string
  last_sync_at: string | null
  sync_status: SyncStatus
}

// ─── /api/v1/portfolio/assets ────────────────────────────────────────────────

export interface AssetMetric {
  asset: string
  quantity: string
  value_usd: string
  value_eur: string
  portfolio_pct: string
  avg_buy_price_usd: string
  avg_buy_price_eur: string
  cost_basis_usd: string
  cost_basis_eur: string
  pnl_usd: string
  pnl_eur: string
  pnl_pct: string
  realized_pnl_usd: string
  realized_pnl_eur: string
}

// ─── /api/v1/settings ────────────────────────────────────────────────────────

export interface AccountSettings {
  account_id: string
  name: string
  has_api_key: boolean
  has_api_secret: boolean
  last_sync_at: string | null
  sync_status: SyncStatus
}

// ─── /api/v1/sync/status ─────────────────────────────────────────────────────

export interface SyncStatusData {
  sync_status: SyncStatus
  last_sync_at: string | null
  last_job: Record<string, unknown> | null
}

// ─── /api/v1/dashboard/btc-insights ──────────────────────────────────────────

export interface BtcBuyEventRaw {
  date: string
  price_usd: string
  quantity: string
  total_usd: string
  timing_pct: string | null
}

export interface BtcBestWorstBuy {
  date: string
  price_usd: string
  quantity: string
  gain_pct: string
}

export interface BtcStats {
  total_buys: number
  buys_in_profit: number
  buys_in_profit_pct: string
  date_first_buy: string | null
  date_last_buy: string | null
  best_buy: BtcBestWorstBuy | null
  worst_buy: BtcBestWorstBuy | null
}

export interface BtcPricePoint {
  date: string
  price: string
  ma50: string | null
  ma200: string | null
}

export interface BtcHistogramBucket {
  bucket_min: number
  bucket_max: number
  label: string
  btc_quantity: string
  buy_count: number
}

export interface BtcMonthlyCell {
  year: number
  month: number
  total_usd: string
  total_btc: string
  buy_count: number
}

export interface BtcTimingDistribution {
  q1: number  // 0-25% (dip buyer)
  q2: number  // 25-50%
  q3: number  // 50-75%
  q4: number  // 75-100% (FOMO)
}

export interface BtcTimingAnalysis {
  avg_percentile: string | null
  label: string
  distribution: BtcTimingDistribution
  buys_below_ma200: number
  buys_above_ma200: number
}

export interface BtcInsightsData {
  current_price_usd: string
  vwap_usd: string
  stats: BtcStats
  timing_analysis: BtcTimingAnalysis
  price_history: BtcPricePoint[]
  buy_events: BtcBuyEventRaw[]
  price_histogram: BtcHistogramBucket[]
  monthly_heatmap: BtcMonthlyCell[]
}

// ─── /api/v1/dashboard/btc-insights/dca-simulation ───────────────────────────

export interface DcaCurvePoint {
  date: string
  btc_accumulated: string
}

export interface DcaSimulationSummary {
  total_invested_usd: string
  real_btc: string
  simulated_btc: string
  diff_btc: string
  diff_pct: string
  diff_value_usd: string
  diff_value_eur: string
  interval: string
  periods_simulated: number
}

export interface DcaSimulationData {
  real: DcaCurvePoint[]
  simulated: DcaCurvePoint[]
  summary: DcaSimulationSummary
}
