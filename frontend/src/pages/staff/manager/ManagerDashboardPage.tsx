import { addDays, format, startOfDay } from 'date-fns'
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import type { Appointment } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/useAuth'
import { appointmentStatusLabel, useT } from '../../../state/useT'

export function ManagerDashboardPage() {
  const t = useT()
  const { token } = useAuth()
  const [day, setDay] = useState(startOfDay(new Date()))
  const dayStr = useMemo(() => format(day, 'yyyy-MM-dd'), [day])

  const q = useQuery({
    queryKey: ['managerAppointments', dayStr],
    queryFn: () =>
      apiFetch<Appointment[]>(`/api/manager/appointments?date=${dayStr}`, {
        token: token ?? undefined,
      }),
  })

  const scheduled = (q.data ?? []).filter((a) => a.status === 'scheduled').length
  const completed = (q.data ?? []).filter((a) => a.status === 'completed').length
  const canceled = (q.data ?? []).filter((a) => a.status === 'canceled').length

  return (
    <Page title={t('manager.dashboard.title')} subtitle={t('manager.dashboard.subtitle', { date: dayStr })}>
      <div className="mb-3 flex gap-2">
        <button
          type="button"
          className="rounded-xl border border-rose-200 bg-white/90 px-3 py-2 text-xs font-medium text-rose-800 shadow-sm"
          onClick={() => setDay((d) => addDays(d, -1))}
        >
          {t('common.prev')}
        </button>
        <div className="flex-1 rounded-xl border border-rose-200 bg-white/90 px-3 py-2 text-center text-xs font-medium text-rose-900 shadow-sm">
          {dayStr}
        </div>
        <button
          type="button"
          className="rounded-xl border border-rose-200 bg-white/90 px-3 py-2 text-xs font-medium text-rose-800 shadow-sm"
          onClick={() => setDay((d) => addDays(d, 1))}
        >
          {t('common.next')}
        </button>
      </div>

      <Card className="border-amber-100/80 bg-gradient-to-r from-amber-50/80 to-rose-50/70">
        <div className="grid grid-cols-3 gap-3 text-center">
          <div>
            <div className="text-lg font-semibold text-rose-950">{scheduled}</div>
            <div className="text-xs text-rose-900/70">{t('manager.dashboard.scheduled')}</div>
          </div>
          <div>
            <div className="text-lg font-semibold text-rose-950">{completed}</div>
            <div className="text-xs text-rose-900/70">{t('manager.dashboard.completed')}</div>
          </div>
          <div>
            <div className="text-lg font-semibold text-rose-950">{canceled}</div>
            <div className="text-xs text-rose-900/70">{t('manager.dashboard.canceled')}</div>
          </div>
        </div>
      </Card>

      {q.isLoading ? <div className="mt-3 text-sm text-rose-800/80">{t('common.loading')}</div> : null}

      <div className="mt-3 space-y-3">
        {(q.data ?? []).map((a) => (
          <Card key={a.id} className="transition hover:border-rose-200 hover:shadow-studio">
            <div className="flex items-baseline justify-between gap-3">
              <div className="text-sm font-semibold text-rose-950">{a.client_name}</div>
              <div className="text-xs text-rose-900/70">
                {new Date(a.start_time).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>
            <div className="mt-1 text-xs text-rose-900/70">{a.client_phone}</div>
            <div className="mt-1 text-xs text-rose-900/70">
              {t('manager.clients.masterLine', {
                name: String(a.master_name ?? `#${a.master_id}`),
              })}
            </div>
            <div className="mt-1 text-xs text-rose-900/70">
              {(a.procedures ?? []).map((p) => p.name).join(', ') ||
                t('common.procedureFallback', { id: a.procedure_id })}
            </div>
            <div className="mt-1 flex items-center justify-between text-xs text-rose-900/70">
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
        ))}
      </div>
    </Page>
  )
}
