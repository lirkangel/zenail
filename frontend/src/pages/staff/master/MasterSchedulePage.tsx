import { addDays, format, startOfDay } from 'date-fns'
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { apiFetch } from '../../../api/client'
import type { Appointment } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/auth'

export function MasterSchedulePage() {
  const { token } = useAuth()
  const [day, setDay] = useState(startOfDay(new Date()))
  const dayStr = useMemo(() => format(day, 'yyyy-MM-dd'), [day])

  const q = useQuery({
    queryKey: ['masterAppointments', dayStr],
    queryFn: () =>
      apiFetch<Appointment[]>(`/api/master/appointments?date=${dayStr}`, {
        token: token ?? undefined,
      }),
  })

  return (
    <Page title="My schedule" subtitle={`Appointments for ${dayStr}`}>
      <div className="mb-3 flex gap-2">
        <button
          type="button"
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs"
          onClick={() => setDay((d) => addDays(d, -1))}
        >
          Prev
        </button>
        <div className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-center text-xs">
          {dayStr}
        </div>
        <button
          type="button"
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs"
          onClick={() => setDay((d) => addDays(d, 1))}
        >
          Next
        </button>
      </div>

      {q.isLoading ? <div className="text-sm text-slate-600">Loading…</div> : null}
      {q.isError ? (
        <div className="text-sm text-rose-700">Failed to load schedule.</div>
      ) : null}
      {q.data && q.data.length === 0 ? (
        <div className="text-sm text-slate-600">No appointments for this day.</div>
      ) : null}

      <div className="space-y-3">
        {(q.data ?? []).map((a) => (
          <Link key={a.id} to={`/staff/appointments/${a.id}`}>
            <Card className="hover:border-slate-300">
              <div className="flex items-baseline justify-between gap-3">
                <div className="text-sm font-semibold">{a.client_name}</div>
                <div className="text-xs text-slate-600">
                  {new Date(a.start_time).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              </div>
              <div className="mt-1 text-xs text-slate-600">{a.client_phone}</div>
              <div className="mt-1 text-xs text-slate-600">
                {(a.procedures ?? []).map((p) => p.name).join(', ') ||
                  `Procedure #${a.procedure_id}`}
              </div>
              <div className="mt-1 flex items-center justify-between text-xs text-slate-600">
                <span>
                  ${a.price} · {a.total_duration_minutes ?? '—'} min
                </span>
                <span
                  className={
                    a.status === 'canceled'
                      ? 'text-rose-700'
                      : a.status === 'completed'
                        ? 'text-emerald-700'
                        : ''
                  }
                >
                  {a.status}
                </span>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </Page>
  )
}
