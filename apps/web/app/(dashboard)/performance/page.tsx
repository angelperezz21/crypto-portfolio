"use client"

import { Topbar } from "@/components/layout/Topbar"
import { PerformanceChart } from "@/components/dashboard/PerformanceChart"

export default function PerformancePage() {
  return (
    <>
      <Topbar title="Rendimiento" subtitle="Evolución temporal del portafolio" />
      <div className="p-4 lg:p-6">
        <PerformanceChart defaultRange="30D" />
      </div>
    </>
  )
}
