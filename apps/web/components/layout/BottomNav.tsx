"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  TrendingUp,
  Bitcoin,
  ArrowLeftRight,
  Settings,
} from "lucide-react"
import { cn } from "@/lib/utils"

const MOBILE_ITEMS = [
  { href: "/",             icon: LayoutDashboard, label: "Overview"  },
  { href: "/performance",  icon: TrendingUp,      label: "Charts"    },
  { href: "/dca",          icon: Bitcoin,         label: "DCA"       },
  { href: "/transactions", icon: ArrowLeftRight,  label: "Historial" },
  { href: "/settings",     icon: Settings,        label: "Ajustes"   },
]

export function BottomNav() {
  const pathname = usePathname()

  return (
    <nav className="lg:hidden fixed bottom-0 inset-x-0 z-50
                    bg-surface border-t border-[var(--border-subtle)]
                    flex items-center justify-around px-2 py-1 safe-area-pb">
      {MOBILE_ITEMS.map((item) => {
        const isActive =
          item.href === "/" ? pathname === "/" : pathname.startsWith(item.href)
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex flex-col items-center gap-0.5 px-3 py-2 rounded-lg transition-colors",
              isActive ? "text-primary" : "text-tertiary hover:text-secondary",
            )}
          >
            <item.icon className="w-5 h-5" />
            <span className="text-[10px] font-medium">{item.label}</span>
          </Link>
        )
      })}
    </nav>
  )
}
