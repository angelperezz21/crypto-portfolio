import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface MetricCardProps {
  label:       string
  value:       string
  subValue?:   string   // valor secundario (ej: equivalente en USD) en gris pequeño
  delta?:      string
  deltaLabel?: string
  isPositive?: boolean
  icon?:       LucideIcon
  className?:  string
}

export function MetricCard({
  label,
  value,
  subValue,
  delta,
  deltaLabel,
  isPositive,
  icon: Icon,
  className,
}: MetricCardProps) {
  return (
    <div className={cn(
      "bg-surface border border-[var(--border)] rounded-xl p-6",
      "hover:border-[var(--border-subtle)] transition-colors",
      className,
    )}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs font-medium uppercase tracking-wider text-secondary">
          {label}
        </span>
        {Icon && <Icon className="w-4 h-4 text-tertiary" />}
      </div>

      {/* Value principal (EUR) */}
      <div className="text-3xl font-bold tabular-nums tracking-tight text-primary mb-1">
        {value}
      </div>

      {/* Valor secundario (USD) */}
      {subValue && (
        <div className="text-xs tabular-nums text-tertiary mb-2">
          {subValue}
        </div>
      )}

      {/* Delta */}
      {delta !== undefined && (
        <div className={cn(
          "text-sm font-semibold tabular-nums",
          !subValue && "mt-1",
          isPositive === true  && "text-positive",
          isPositive === false && "text-negative",
          isPositive === undefined && "text-secondary",
        )}>
          {delta}
          {deltaLabel && (
            <span className="ml-1 text-xs font-normal text-tertiary">
              {deltaLabel}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

export function MetricCardSkeleton() {
  return (
    <div className="bg-surface border border-[var(--border)] rounded-xl p-6 animate-pulse">
      <div className="flex items-center justify-between mb-4">
        <div className="h-3 bg-elevated rounded w-28" />
        <div className="h-4 w-4 bg-elevated rounded" />
      </div>
      <div className="h-9 bg-elevated rounded w-40 mb-2" />
      <div className="h-3 bg-elevated rounded w-20" />
    </div>
  )
}
