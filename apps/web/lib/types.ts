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
  evolution_30d: EvolutionPoint[]
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
