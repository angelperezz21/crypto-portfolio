"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  Bitcoin,
  Zap,
  ArrowLeftRight,
  FileText,
  Settings,
} from "lucide-react"
import { cn } from "@/lib/utils"

const NAV_ITEMS = [
  { href: "/",             icon: LayoutDashboard, label: "Overview"       },
  { href: "/dca",          icon: Bitcoin,         label: "DCA Bitcoin"    },
  { href: "/btc",          icon: Zap,             label: "Análisis BTC"   },
  { href: "/transactions", icon: ArrowLeftRight,  label: "Transacciones"  },
  { href: "/fiscal",       icon: FileText,        label: "Fiscal"         },
  { href: "/settings",     icon: Settings,        label: "Ajustes"        },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="hidden lg:flex flex-col w-[240px] flex-shrink-0 h-screen
                      bg-surface border-r border-[var(--border-subtle)]">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 h-14 border-b border-[var(--border-subtle)]">
        <div className="w-7 h-7 rounded-lg bg-[#f97316]/15 flex items-center justify-center">
          <Bitcoin className="w-4 h-4 text-[#f97316]" />
        </div>
        <span className="text-sm font-semibold text-primary">Portfolio</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href)

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                isActive
                  ? "bg-elevated text-primary font-medium"
                  : "text-secondary hover:text-primary hover:bg-elevated",
              )}
            >
              <item.icon className="w-4 h-4 flex-shrink-0" />
              {item.label}
            </Link>
          )
        })}
      </nav>

    </aside>
  )
}
