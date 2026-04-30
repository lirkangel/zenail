import { format } from 'date-fns'
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { apiFetch } from '../../../api/client'
import type { Appointment } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/auth'

export function MasterSchedulePage() {
  const { token } = useAuth()
  const dayStr = useMemo(() => format(new Date(), 'yyyy-MM-dd'), [])

  const q = useQuery({
    queryKey: ['masterAppointments', dayStr],
    queryFn: () => apiFetch<Appointment[]>(`/api/master/appointments?date=${dayStr}`, { token: token ?? undefined }),
  })

  return (
    <Page title="My schedule" subtitle={`Today (${dayStr})`}>
      {q.isLoading ? <div className="text-sm text-slate-600">Loading…</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">Failed to load schedule.</div> : null}

      <div className="space-y-3">
        {(q.data ?? []).map((a) => (
          <Link key={a.id} to={`/staff/appointments/${a.id}`}>
            <Card className="hover:border-slate-300">
              <div className="flex items-baseline justify-between gap-3">
                <div className="text-sm font-semibold">{a.client_name}</div>
                <div className="text-xs text-slate-600">
                  {new Date(a.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
              <div className="mt-1 text-xs text-slate-600">{a.status}</div>
            </Card>
          </Link>
        ))}
      </div>
    </Page>
  )
}

