import { addDays, format, startOfDay } from 'date-fns'
import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import type { Appointment, Master } from '../../../api/types'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Input } from '../../../components/Input'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/useAuth'
import { appointmentStatusLabel, useT } from '../../../state/useT'

export function ManagerAppointmentsPage() {
  const t = useT()
  const { token } = useAuth()
  const [day, setDay] = useState(startOfDay(new Date()))
  const dayStr = useMemo(() => format(day, 'yyyy-MM-dd'), [day])
  const qc = useQueryClient()

  const q = useQuery({
    queryKey: ['managerAppointments', dayStr],
    queryFn: () =>
      apiFetch<Appointment[]>(`/api/manager/appointments?date=${dayStr}`, {
        token: token ?? undefined,
      }),
  })
  const mastersQ = useQuery({
    queryKey: ['managerMasters'],
    queryFn: () => apiFetch<Master[]>('/api/manager/masters', { token: token ?? undefined }),
  })

  const patch = useMutation({
    mutationFn: (args: { id: number; body: unknown }) =>
      apiFetch<Appointment>(`/api/manager/appointments/${args.id}`, {
        method: 'PATCH',
        token: token ?? undefined,
        body: JSON.stringify(args.body),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['managerAppointments'] })
    },
  })

  return (
    <Page title={t('manager.clients.title')} subtitle={t('manager.clients.subtitle', { date: dayStr })}>
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

      {q.isLoading ? <div className="text-sm text-rose-800/80">{t('common.loading')}</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">{t('manager.clients.error')}</div> : null}
      {q.data && q.data.length === 0 ? (
        <div className="text-sm text-rose-900/70">{t('manager.clients.empty')}</div>
      ) : null}

      <div className="space-y-3">
        {(q.data ?? []).map((a) => (
          <AppointmentRow
            key={a.id}
            appt={a}
            masters={mastersQ.data ?? []}
            pending={patch.isPending}
            onCancel={() => patch.mutate({ id: a.id, body: { status: 'canceled' } })}
            onSave={(body) => patch.mutate({ id: a.id, body })}
          />
        ))}
      </div>
    </Page>
  )
}

function AppointmentRow({
  appt,
  masters,
  pending,
  onCancel,
  onSave,
}: {
  appt: Appointment
  masters: Master[]
  pending: boolean
  onCancel: () => void
  onSave: (body: { start_time: string; master_id: number }) => void
}) {
  const t = useT()
  const [startValue, setStartValue] = useState(toDateTimeLocal(appt.start_time))
  const [masterId, setMasterId] = useState(appt.master_id.toString())
  return (
    <Card className="transition hover:border-rose-200 hover:shadow-studio">
      <div className="flex items-baseline justify-between gap-3">
        <div className="text-sm font-semibold text-rose-950">{appt.client_name}</div>
        <div className="text-xs text-rose-900/70">
          {new Date(appt.start_time).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      </div>
      <div className="mt-1 text-xs text-rose-900/70">{appt.client_phone}</div>
      <div className="mt-1 text-xs text-rose-900/70">
        {t('manager.clients.masterLine', {
          name: String(appt.master_name ?? `#${appt.master_id}`),
        })}
      </div>
      <div className="mt-1 text-xs text-rose-900/70">
        {(appt.procedures ?? []).map((p) => p.name).join(', ') ||
          t('common.procedureFallback', { id: appt.procedure_id })}
      </div>
      <div className="mt-1 flex items-center justify-between text-xs text-rose-900/70">
        <span>
          ${appt.price} · {appt.total_duration_minutes ?? t('common.emDash')} {t('common.minutes')}
        </span>
        <span
          className={
            appt.status === 'canceled'
              ? 'font-medium text-rose-700'
              : appt.status === 'completed'
                ? 'font-medium text-emerald-700'
                : 'font-medium text-rose-900'
          }
        >
          {appointmentStatusLabel(t, appt.status)}
        </span>
      </div>

      <div className="mt-3 space-y-2">
        <div>
          <label className="mb-1 block text-[11px] font-medium text-rose-900/80">{t('manager.clients.newTime')}</label>
          <Input
            type="datetime-local"
            value={startValue}
            onChange={(e) => setStartValue(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-[11px] font-medium text-rose-900/80">
            {t('manager.clients.assignedMaster')}
          </label>
          <select
            className="w-full rounded-xl border border-rose-200 bg-white/90 px-3 py-2 text-sm text-rose-950 focus:outline-none focus:ring-2 focus:ring-rose-400/40"
            value={masterId}
            onChange={(e) => setMasterId(e.target.value)}
          >
            {masters.map((m) => (
              <option key={m.id} value={m.id}>
                {m.full_name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex gap-2">
          <Button
            className="flex-1"
            disabled={pending}
            type="button"
            onClick={() =>
              onSave({
                start_time: new Date(startValue).toISOString(),
                master_id: Number(masterId),
              })
            }
          >
            {t('manager.clients.saveChanges')}
          </Button>
          <Button
            variant="secondary"
            className="flex-1"
            disabled={pending || appt.status === 'canceled'}
            type="button"
            onClick={onCancel}
          >
            {t('common.cancel')}
          </Button>
        </div>
      </div>
    </Card>
  )
}

function toDateTimeLocal(value: string) {
  const date = new Date(value)
  const offsetMs = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16)
}
