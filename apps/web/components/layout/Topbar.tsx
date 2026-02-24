"use client"

import { useState } from "react"
import { RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ThemeToggle } from "./ThemeToggle"
import { triggerSync } from "@/lib/api"
import { cn } from "@/lib/utils"

interface TopbarProps {
  title: string
  subtitle?: string
}

export function Topbar({ title, subtitle }: TopbarProps) {
  const [syncing, setSyncing] = useState(false)

  async function handleSync() {
    setSyncing(true)
    try {
      await triggerSync()
    } finally {
      setTimeout(() => setSyncing(false), 2000)
    }
  }

  return (
    <header className="h-14 flex-shrink-0 border-b border-[var(--border-subtle)]
                       flex items-center justify-between px-6 bg-surface">
      <div>
        <h1 className="text-sm font-semibold text-primary leading-none">{title}</h1>
        {subtitle && (
          <p className="text-xs text-secondary mt-0.5">{subtitle}</p>
        )}
      </div>

      <div className="flex items-center gap-2">
        <ThemeToggle />
        <Button
          variant="ghost"
          size="icon"
          onClick={handleSync}
          disabled={syncing}
          title="Sincronizar ahora"
          aria-label="Sincronizar ahora"
        >
          <RefreshCw className={cn("h-4 w-4", syncing && "animate-spin")} />
        </Button>
      </div>
    </header>
  )
}
