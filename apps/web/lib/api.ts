import type { ApiResponse } from "./types"

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

// ─── Token helpers ────────────────────────────────────────────────────────────

export function getToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem("auth_token")
}

export function setToken(token: string): void {
  localStorage.setItem("auth_token", token)
}

export function clearToken(): void {
  localStorage.removeItem("auth_token")
}

// ─── Core fetch ───────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<ApiResponse<T>> {
  const token = getToken()
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> | undefined),
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  const json: ApiResponse<T> = await res.json()

  if (!res.ok) {
    if (res.status === 401) {
      clearToken()
      if (typeof window !== "undefined") window.location.href = "/login"
    }
    throw new Error(json.error ?? `HTTP ${res.status}`)
  }

  return json
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export async function login(password: string): Promise<string> {
  const res = await apiFetch<{ access_token: string; token_type: string }>(
    "/api/v1/auth/token",
    { method: "POST", body: JSON.stringify({ password }) },
  )
  return res.data.access_token
}

// ─── Settings ─────────────────────────────────────────────────────────────────

export async function fetchSettings() {
  return apiFetch<import("./types").AccountSettings | null>("/api/v1/settings")
}

export async function saveSettings(body: {
  name?: string
  api_key?: string
  api_secret?: string
}) {
  return apiFetch<import("./types").AccountSettings>("/api/v1/settings", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export async function fetchOverview() {
  return apiFetch<import("./types").OverviewData>("/api/v1/dashboard/overview")
}

export async function fetchAssets() {
  return apiFetch<import("./types").AssetMetric[]>("/api/v1/portfolio/assets")
}

export async function fetchSyncStatus() {
  return apiFetch<import("./types").SyncStatusData>("/api/v1/sync/status")
}

export async function triggerSync() {
  return apiFetch<{ job_id: string; status: string }>("/api/v1/sync/trigger", {
    method: "POST",
  })
}

// ─── Portfolio ─────────────────────────────────────────────────────────────────

export async function fetchLiquidBalance() {
  return apiFetch<{
    total_liquid_usd: string
    total_liquid_eur: string
    items: { asset: string; quantity: string; value_usd: string; value_eur: string }[]
  }>("/api/v1/portfolio/liquid")
}

export async function fetchBtcInsights() {
  return apiFetch<import("./types").BtcInsightsData>("/api/v1/dashboard/btc-insights")
}

export async function fetchDcaSimulation(interval: "weekly" | "monthly" = "weekly") {
  return apiFetch<import("./types").DcaSimulationData>(
    `/api/v1/dashboard/btc-insights/dca-simulation?interval=${interval}`
  )
}
