import { format } from 'date-fns'
import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import type { Appointment } from '../../../api/types'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Input } from '../../../components/Input'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/auth'

export function ManagerAppointmentsPage() {
  const { token } = useAuth()
  const dayStr = useMemo(() => format(new Date(), 'yyyy-MM-dd'), [])
  const qc = useQueryClient()
  const q = useQuery({
    queryKey: ['managerAppointments', dayStr],
    queryFn: () =>
      apiFetch<Appointment[]>(`/api/manager/appointments?date=${dayStr}`, { token: token ?? undefined }),
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
    <Page title="Clients" subtitle={`Appointments (${dayStr})`}>
      {q.isLoading ? <div className="text-sm text-slate-600">Loading…</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">Failed to load appointments.</div> : null}

      <div className="space-y-3">
        {(q.data ?? []).map((a) => (
          <AppointmentRow
            key={a.id}
            appt={a}
            pending={patch.isPending}
            onCancel={() => patch.mutate({ id: a.id, body: { status: 'canceled' } })}
            onReschedule={(start_time) => patch.mutate({ id: a.id, body: { start_time } })}
          />
        ))}
      </div>
    </Page>
  )
}

function AppointmentRow({
  appt,
  pending,
  onCancel,
  onReschedule,
}: {
  appt: Appointment
  pending: boolean
  onCancel: () => void
  onReschedule: (start_time: string) => void
}) {
  const [value, setValue] = useState(appt.start_time)
  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3">
        <div className="text-sm font-semibold">{appt.client_name}</div>
        <div className="text-xs text-slate-600">
          {new Date(appt.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
      <div className="mt-1 text-xs text-slate-600">{appt.status}</div>

      <div className="mt-3 space-y-2">
        <div>
          <label className="mb-1 block text-[11px] font-medium text-slate-700">
            Reschedule (ISO with timezone)
          </label>
          <Input value={value} onChange={(e) => setValue(e.target.value)} />
        </div>
        <div className="flex gap-2">
          <Button className="flex-1" disabled={pending} type="button" onClick={() => onReschedule(value)}>
            Reschedule
          </Button>
          <Button
            className="flex-1 bg-white text-slate-900 border border-slate-200 hover:bg-slate-50"
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

