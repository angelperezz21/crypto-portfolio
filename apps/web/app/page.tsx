import { AuthGuard } from "@/components/layout/AuthGuard"
import { AppShell }  from "@/components/layout/AppShell"
import { OverviewContent } from "@/components/dashboard/OverviewContent"

export default function OverviewPage() {
  return (
    <AuthGuard>
      <AppShell>
        <OverviewContent />
      </AppShell>
    </AuthGuard>
  )
}
