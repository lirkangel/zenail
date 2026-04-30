import { addDays, format, startOfDay } from 'date-fns'
import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import type { Appointment, Master } from '../../../api/types'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Input } from '../../../components/Input'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/auth'

export function ManagerAppointmentsPage() {
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
    <Page title="Clients" subtitle={`Appointments for ${dayStr}`}>
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
        <div className="text-sm text-rose-700">Failed to load appointments.</div>
      ) : null}
      {q.data && q.data.length === 0 ? (
        <div className="text-sm text-slate-600">No appointments for this day.</div>
      ) : null}

      <div className="space-y-3">
        {(q.data ?? []).map((a) => (
          <AppointmentRow
            key={a.id}
            appt={a}
            masters={mastersQ.data ?? []}
            pending={patch.isPending}
            onCancel={() => patch.mutate({ id: a.id, body: { status: 'canceled' } })}
            onSave={(body) =>
              patch.mutate({ id: a.id, body })
            }
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
  const [startValue, setStartValue] = useState(toDateTimeLocal(appt.start_time))
  const [masterId, setMasterId] = useState(appt.master_id.toString())
  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3">
        <div className="text-sm font-semibold">{appt.client_name}</div>
        <div className="text-xs text-slate-600">
          {new Date(appt.start_time).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      </div>
      <div className="mt-1 text-xs text-slate-600">{appt.client_phone}</div>
      <div className="mt-1 text-xs text-slate-600">
        Master: {appt.master_name ?? `#${appt.master_id}`}
      </div>
      <div className="mt-1 text-xs text-slate-600">
        {(appt.procedures ?? []).map((p) => p.name).join(', ') ||
          `Procedure #${appt.procedure_id}`}
      </div>
      <div className="mt-1 flex items-center justify-between text-xs text-slate-600">
        <span>
          ${appt.price} · {appt.total_duration_minutes ?? '—'} min
        </span>
        <span
          className={
            appt.status === 'canceled'
              ? 'text-rose-700'
              : appt.status === 'completed'
                ? 'text-emerald-700'
                : ''
          }
        >
          {appt.status}
        </span>
      </div>

      <div className="mt-3 space-y-2">
        <div>
          <label className="mb-1 block text-[11px] font-medium text-slate-700">
            New time
          </label>
          <Input
            type="datetime-local"
            value={startValue}
            onChange={(e) => setStartValue(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-[11px] font-medium text-slate-700">
            Assigned master
          </label>
          <select
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900/20"
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
            Save changes
          </Button>
          <Button
            variant="secondary"
            className="flex-1"
            disabled={pending || appt.status === 'canceled'}
            type="button"
            onClick={onCancel}
          >
            Cancel
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
