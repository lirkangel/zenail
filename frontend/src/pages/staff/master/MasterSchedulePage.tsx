import { addDays, format, startOfDay } from 'date-fns'
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { apiFetch } from '../../../api/client'
import type { Appointment } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/useAuth'
import { appointmentStatusLabel, useT } from '../../../state/useT'

export function MasterSchedulePage() {
  const t = useT()
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
    <Page title={t('master.schedule.title')} subtitle={t('master.schedule.subtitle', { date: dayStr })}>
      <div className="mb-3 flex gap-2">
        <button
          type="button"
          className="rounded-xl border border-rose-200/80 bg-white/90 px-3 py-2 text-xs font-medium text-rose-900 shadow-sm transition hover:border-rose-300 hover:bg-white"
          onClick={() => setDay((d) => addDays(d, -1))}
        >
          {t('common.prev')}
        </button>
        <div className="flex-1 rounded-xl border border-rose-200/80 bg-white/90 px-3 py-2 text-center text-xs font-medium text-rose-950 shadow-sm">
          {dayStr}
        </div>
        <button
          type="button"
          className="rounded-xl border border-rose-200/80 bg-white/90 px-3 py-2 text-xs font-medium text-rose-900 shadow-sm transition hover:border-rose-300 hover:bg-white"
          onClick={() => setDay((d) => addDays(d, 1))}
        >
          {t('common.next')}
        </button>
      </div>

      {q.isLoading ? <div className="text-sm text-rose-800/80">{t('common.loading')}</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">{t('master.schedule.error')}</div> : null}
      {q.data && q.data.length === 0 ? (
        <div className="text-sm text-rose-900/75">{t('master.schedule.empty')}</div>
      ) : null}

      <div className="space-y-3">
        {(q.data ?? []).map((a) => (
          <Link key={a.id} to={`/staff/appointments/${a.id}`}>
            <Card className="transition hover:border-rose-200 hover:shadow-studio">
              <div className="flex items-baseline justify-between gap-3">
                <div className="text-sm font-semibold text-rose-950">{a.client_name}</div>
                <div className="text-xs text-rose-900/70">
                  {new Date(a.start_time).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              </div>
              <div className="mt-1 text-xs text-rose-900/75">{a.client_phone}</div>
              <div className="mt-1 text-xs text-rose-900/75">
                {(a.procedures ?? []).map((p) => p.name).join(', ') ||
                  t('common.procedureFallback', { id: a.procedure_id })}
              </div>
              <div className="mt-1 flex items-center justify-between text-xs text-rose-900/75">
                <span>
                  ${a.price} · {a.total_duration_minutes ?? t('common.emDash')} {t('common.minutes')}
                </span>
                <span
                  className={
                    a.status === 'canceled'
                      ? 'font-medium text-rose-700'
                      : a.status === 'completed'
                        ? 'font-medium text-emerald-700'
                        : 'font-medium text-rose-900'
                  }
                >
                  {appointmentStatusLabel(t, a.status)}
                </span>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </Page>
  )
}
