"use client"

import { useEffect, useState } from "react"
import { cn } from "@/lib/utils"
import { fetchSyncStatus } from "@/lib/api"
import { formatRelativeTime } from "@/lib/formatters"
import type { SyncStatus } from "@/lib/types"

export function SyncIndicator() {
  const [status,   setStatus]   = useState<SyncStatus>("idle")
  const [lastSync, setLastSync] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetchSyncStatus()
        setStatus(res.data.sync_status)
        setLastSync(res.data.last_sync_at)
      } catch {
        /* silently ignore */
      }
    }
    load()
    const id = setInterval(load, 30_000)
    return () => clearInterval(id)
  }, [])

  const label =
    status === "syncing" ? "Sincronizando…" :
    status === "error"   ? "Error de sync"  :
    `Sync: ${formatRelativeTime(lastSync)}`

  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-secondary">
      <div className={cn(
        "w-1.5 h-1.5 rounded-full flex-shrink-0",
        status === "syncing" && "bg-warning animate-pulse",
        status === "error"   && "bg-negative",
        status === "idle"    && "bg-positive",
      )} />
      <span>{label}</span>
    </div>
  )
}
