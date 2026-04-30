import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { apiFetch } from '../../api/client'
import type { Appointment } from '../../api/types'
import { Card } from '../../components/Card'
import { Page } from '../../components/Page'
import { getLastBooking } from '../../state/booking'

export function BookSuccessPage() {
  const [sp] = useSearchParams()
  const id = sp.get('id')
  const last = getLastBooking()
  const q = useQuery({
    queryKey: ['bookingSuccess', id, last?.client_phone],
    enabled: !!id && !!last?.client_phone,
    queryFn: () =>
      apiFetch<Appointment>(
        `/api/appointments/${id}?client_phone=${encodeURIComponent(last!.client_phone)}`,
      ),
  })
  return (
    <Page title="Booked" subtitle="Your appointment is confirmed.">
      <Card>
        <div className="text-sm">
          Appointment ID: <span className="font-semibold">{id ?? '—'}</span>
        </div>
        {q.data ? (
          <div className="mt-3 space-y-1 text-xs text-slate-700">
            <div>
              Status: <span className="font-semibold">{q.data.status}</span>
            </div>
            <div>Time: {new Date(q.data.start_time).toLocaleString()}</div>
            <div>Total: ${q.data.price} / {q.data.total_duration_minutes} min</div>
            <div>Procedures: {q.data.procedures.map((p) => p.name).join(', ')}</div>
          </div>
        ) : null}
        <div className="mt-2 text-xs text-slate-600">
          Please arrive a few minutes early. If you need to change time, contact the salon.
        </div>
      </Card>
    </Page>
  )
}

