"use client"

import { useEffect, useState } from "react"
import {
  Key, RefreshCw, Save, Eye, EyeOff,
  CheckCircle2, AlertCircle, Clock, Loader2,
} from "lucide-react"
import { Topbar } from "@/components/layout/Topbar"
import { Button } from "@/components/ui/button"
import { fetchSettings, saveSettings, triggerSync, fetchSyncStatus } from "@/lib/api"
import { cn } from "@/lib/utils"
import { formatRelativeTime } from "@/lib/formatters"
import type { AccountSettings, SyncStatus } from "@/lib/types"

// ─── Helpers ──────────────────────────────────────────────────────────────────

function SectionCard({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-[var(--border-subtle)]">
        <h2 className="text-sm font-semibold text-primary">{title}</h2>
        {description && (
          <p className="text-xs text-secondary mt-0.5">{description}</p>
        )}
      </div>
      <div className="p-6">{children}</div>
    </div>
  )
}

function PasswordInput({
  label,
  value,
  onChange,
  placeholder,
  hint,
  hasExisting,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  hint?: string
  hasExisting?: boolean
}) {
  const [visible, setVisible] = useState(false)
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <label className="text-xs font-medium text-secondary">{label}</label>
        {hasExisting && (
          <span className="text-xs text-positive flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Guardada
          </span>
        )}
      </div>
      <div className="relative">
        <input
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={hasExisting ? "••••••••  (dejar vacío para no cambiar)" : placeholder}
          className="w-full px-3 py-2.5 pr-10 text-sm rounded-lg
                     bg-elevated border border-[var(--border)]
                     text-primary placeholder:text-tertiary
                     focus:outline-none focus:ring-2 focus:ring-accent/50
                     transition-all font-mono"
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-tertiary
                     hover:text-secondary transition-colors"
        >
          {visible
            ? <EyeOff className="w-4 h-4" />
            : <Eye    className="w-4 h-4" />}
        </button>
      </div>
      {hint && <p className="text-xs text-tertiary mt-1">{hint}</p>}
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export function SettingsContent() {
  const [settings,    setSettings]    = useState<AccountSettings | null>(null)
  const [loading,     setLoading]     = useState(true)

  // form
  const [name,      setName]      = useState("")
  const [apiKey,    setApiKey]    = useState("")
  const [apiSecret, setApiSecret] = useState("")
  const [saving,    setSaving]    = useState(false)
  const [saveMsg,   setSaveMsg]   = useState<{ ok: boolean; text: string } | null>(null)

  // sync
  const [syncStatus,  setSyncStatus]  = useState<SyncStatus>("idle")
  const [lastSync,    setLastSync]    = useState<string | null>(null)
  const [triggering,  setTriggering]  = useState(false)
  const [syncMsg,     setSyncMsg]     = useState<string | null>(null)

  // ── Load settings ──────────────────────────────────────────────────────────
  useEffect(() => {
    const load = async () => {
      try {
        const [settRes, syncRes] = await Promise.all([
          fetchSettings(),
          fetchSyncStatus(),
        ])
        if (settRes.data) {
          setSettings(settRes.data)
          setName(settRes.data.name)
        }
        setSyncStatus(syncRes.data.sync_status)
        setLastSync(syncRes.data.last_sync_at)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Poll sync status every 5s while syncing
  useEffect(() => {
    if (syncStatus !== "syncing") return
    const id = setInterval(async () => {
      try {
        const res = await fetchSyncStatus()
        setSyncStatus(res.data.sync_status)
        setLastSync(res.data.last_sync_at)
      } catch { /* ignore */ }
    }, 5_000)
    return () => clearInterval(id)
  }, [syncStatus])

  // ── Save settings ──────────────────────────────────────────────────────────
  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setSaveMsg(null)
    try {
      const body: Record<string, string> = {}
      if (name.trim())      body.name       = name.trim()
      if (apiKey.trim())    body.api_key    = apiKey.trim()
      if (apiSecret.trim()) body.api_secret = apiSecret.trim()

      const res = await saveSettings(body)
      setSettings(res.data)
      setApiKey("")
      setApiSecret("")
      setSaveMsg({ ok: true, text: "Configuración guardada correctamente" })
    } catch (err: unknown) {
      setSaveMsg({
        ok: false,
        text: err instanceof Error ? err.message : "Error al guardar",
      })
    } finally {
      setSaving(false)
    }
  }

  // ── Trigger sync ───────────────────────────────────────────────────────────
  async function handleSync() {
    setTriggering(true)
    setSyncMsg(null)
    try {
      await triggerSync()
      setSyncStatus("syncing")
      setSyncMsg("Sincronización iniciada. Puede tardar varios minutos la primera vez.")
    } catch (err: unknown) {
      setSyncMsg(err instanceof Error ? err.message : "Error al iniciar sync")
    } finally {
      setTriggering(false)
    }
  }

  // ── Skeleton ───────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <>
        <Topbar title="Ajustes" />
        <div className="p-4 lg:p-6 space-y-4 max-w-2xl">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-surface border border-[var(--border)] rounded-xl
                                    overflow-hidden animate-pulse">
              <div className="px-6 py-4 border-b border-[var(--border-subtle)]">
                <div className="h-4 bg-elevated rounded w-32" />
              </div>
              <div className="p-6 space-y-3">
                <div className="h-10 bg-elevated rounded" />
                <div className="h-10 bg-elevated rounded" />
              </div>
            </div>
          ))}
        </div>
      </>
    )
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <>
      <Topbar title="Ajustes" subtitle="Configuración de cuenta y API Keys" />

      <div className="p-4 lg:p-6 space-y-4 max-w-2xl">

        {/* ── 1. Cuenta ──────────────────────────────────────────────────── */}
        <form onSubmit={handleSave} className="space-y-4">
          <SectionCard
            title="Cuenta"
            description="Nombre identificativo de tu cuenta de Binance"
          >
            <div>
              <label className="block text-xs font-medium text-secondary mb-1.5">
                Nombre de la cuenta
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Mi cuenta Binance"
                className="w-full px-3 py-2.5 text-sm rounded-lg
                           bg-elevated border border-[var(--border)]
                           text-primary placeholder:text-tertiary
                           focus:outline-none focus:ring-2 focus:ring-accent/50
                           transition-all"
              />
            </div>
          </SectionCard>

          {/* ── 2. API Keys ──────────────────────────────────────────────── */}
          <SectionCard
            title="API Keys de Binance"
            description="Necesitas permisos de solo lectura — nunca de trading ni retiro"
          >
            <div className="space-y-4">
              {/* Aviso de seguridad */}
              <div className="flex gap-3 p-3 rounded-lg bg-amber-500/5 border border-amber-500/20">
                <Key className="w-4 h-4 text-warning flex-shrink-0 mt-0.5" />
                <p className="text-xs text-secondary leading-relaxed">
                  Las claves se cifran con <strong className="text-primary">AES-256-GCM</strong> antes
                  de guardarse. Nunca se muestran en texto plano ni en logs.
                  Usa una API Key de <strong className="text-primary">solo lectura</strong> de Binance.
                </p>
              </div>

              <PasswordInput
                label="API Key"
                value={apiKey}
                onChange={setApiKey}
                placeholder="Pega tu API Key aquí"
                hasExisting={settings?.has_api_key}
              />

              <PasswordInput
                label="API Secret"
                value={apiSecret}
                onChange={setApiSecret}
                placeholder="Pega tu API Secret aquí"
                hasExisting={settings?.has_api_secret}
              />
            </div>
          </SectionCard>

          {/* ── Feedback y botón guardar ─────────────────────────────────── */}
          {saveMsg && (
            <div className={cn(
              "flex items-center gap-2 px-4 py-3 rounded-lg text-sm",
              saveMsg.ok
                ? "bg-positive/10 border border-positive/20 text-positive"
                : "bg-negative/10 border border-negative/20 text-negative",
            )}>
              {saveMsg.ok
                ? <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                : <AlertCircle  className="w-4 h-4 flex-shrink-0" />}
              {saveMsg.text}
            </div>
          )}

          <div className="flex justify-end">
            <Button type="submit" disabled={saving} className="gap-2">
              {saving
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <Save    className="w-4 h-4" />}
              {saving ? "Guardando…" : "Guardar cambios"}
            </Button>
          </div>
        </form>

        {/* ── 3. Sincronización ────────────────────────────────────────────── */}
        <SectionCard
          title="Sincronización"
          description="Descarga tu historial completo de Binance"
        >
          <div className="space-y-4">
            {/* Estado actual */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-elevated">
              <div className="flex items-center gap-2.5">
                <div className={cn(
                  "w-2 h-2 rounded-full",
                  syncStatus === "syncing" && "bg-warning animate-pulse",
                  syncStatus === "error"   && "bg-negative",
                  syncStatus === "idle"    && "bg-positive",
                )} />
                <div>
                  <p className="text-sm font-medium text-primary">
                    {syncStatus === "syncing" ? "Sincronizando…" :
                     syncStatus === "error"   ? "Error en último sync" :
                     "En reposo"}
                  </p>
                  {lastSync && (
                    <p className="text-xs text-tertiary flex items-center gap-1 mt-0.5">
                      <Clock className="w-3 h-3" />
                      Último sync: {formatRelativeTime(lastSync)}
                      {" · "}{new Date(lastSync).toLocaleString("es-ES")}
                    </p>
                  )}
                  {!lastSync && (
                    <p className="text-xs text-tertiary mt-0.5">Nunca sincronizado</p>
                  )}
                </div>
              </div>
            </div>

            {/* Descripción */}
            <p className="text-xs text-secondary leading-relaxed">
              La primera sincronización importa todo el historial (trades, depósitos,
              retiros). Las siguientes son incrementales y solo descargan datos nuevos.
              Puede tardar varios minutos la primera vez.
            </p>

            {syncMsg && (
              <div className="flex items-center gap-2 px-4 py-3 rounded-lg text-sm
                              bg-accent/10 border border-accent/20 text-accent">
                <RefreshCw className="w-4 h-4 flex-shrink-0" />
                {syncMsg}
              </div>
            )}

            <Button
              onClick={handleSync}
              disabled={triggering || syncStatus === "syncing" || !settings?.has_api_key}
              variant="outline"
              className="w-full gap-2"
            >
              {(triggering || syncStatus === "syncing")
                ? <Loader2    className="w-4 h-4 animate-spin" />
                : <RefreshCw  className="w-4 h-4" />}
              {syncStatus === "syncing"
                ? "Sincronizando…"
                : triggering
                ? "Iniciando…"
                : "Sincronizar ahora"}
            </Button>

            {!settings?.has_api_key && (
              <p className="text-xs text-warning text-center">
                Guarda primero tus API Keys para poder sincronizar
              </p>
            )}
          </div>
        </SectionCard>

      </div>
    </>
  )
}
