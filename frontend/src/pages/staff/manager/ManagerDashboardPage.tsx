import { format } from 'date-fns'
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import type { Appointment } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/auth'

export function ManagerDashboardPage() {
  const { token } = useAuth()
  const dayStr = useMemo(() => format(new Date(), 'yyyy-MM-dd'), [])
  const q = useQuery({
    queryKey: ['managerAppointments', dayStr],
    queryFn: () =>
      apiFetch<Appointment[]>(`/api/manager/appointments?date=${dayStr}`, { token: token ?? undefined }),
  })

  const scheduled = (q.data ?? []).filter((a) => a.status === 'scheduled').length

  return (
    <Page title="Today" subtitle={`Clients coming today (${dayStr})`}>
      <Card>
        <div className="text-sm font-semibold">{scheduled} scheduled</div>
        <div className="mt-1 text-xs text-slate-600">
          Use the Clients tab to reschedule or cancel.
        </div>
      </Card>
    </Page>
  )
}

