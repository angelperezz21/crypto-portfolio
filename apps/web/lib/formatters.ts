export const formatCurrency = (value: number, currency = "USD"): string =>
  new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)

export const formatPercent = (value: number): string =>
  `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`

export const formatCrypto = (value: number, decimals = 8): string =>
  new Intl.NumberFormat("es-ES", {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  }).format(value)

export const formatSats = (btc: number): string =>
  `${Math.round(btc * 1e8).toLocaleString("es-ES")} sats`

/** Convierte string Decimal del backend ("0E-8", "1234.56") a number */
export const d = (value: string | null | undefined): number => {
  if (!value) return 0
  const n = parseFloat(value)
  return isNaN(n) ? 0 : n
}

export const formatRelativeTime = (iso: string | null): string => {
  if (!iso) return "nunca"
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return "ahora"
  if (mins < 60) return `hace ${mins}m`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `hace ${hours}h`
  return `hace ${Math.floor(hours / 24)}d`
}
