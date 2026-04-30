import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { apiFetch } from '../../api/client'
import type { Appointment, Branch } from '../../api/types'
import { Card } from '../../components/Card'
import { Page } from '../../components/Page'
import { getLastBooking } from '../../state/booking'

export function BookBranchPage() {
  const lastBooking = getLastBooking()
  const q = useQuery({
    queryKey: ['branches'],
    queryFn: () => apiFetch<Branch[]>('/api/branches'),
  })
  const lastQ = useQuery({
    queryKey: ['lastBooking', lastBooking?.id, lastBooking?.client_phone],
    enabled: !!lastBooking,
    queryFn: () =>
      apiFetch<Appointment>(
        `/api/appointments/${lastBooking!.id}?client_phone=${encodeURIComponent(
          lastBooking!.client_phone,
        )}`,
      ),
  })

  return (
    <Page title="Choose a branch" subtitle="Pick the salon location you want to visit.">
      {lastQ.data ? (
        <Card className="mb-3 border-amber-200 bg-amber-50">
          <div className="text-sm font-semibold">Your booking is still {lastQ.data.status}</div>
          <div className="mt-1 text-xs text-slate-700">
            {new Date(lastQ.data.start_time).toLocaleString()} · ${lastQ.data.price} ·{' '}
            {lastQ.data.total_duration_minutes} min
          </div>
          <div className="mt-1 text-xs text-slate-600">
            {lastQ.data.procedures.map((p) => p.name).join(', ')}
          </div>
        </Card>
      ) : null}

      {q.isLoading ? <div className="text-sm text-slate-600">Loading…</div> : null}
      {q.isError ? (
        <div className="text-sm text-rose-700">Failed to load branches.</div>
      ) : null}
      <div className="space-y-4">
        {(q.data ?? []).map((b) => (
          <Link key={b.id} to={`/book/master?branch=${b.id}`}>
            <Card className="p-5 hover:border-slate-300">
              <div className="text-sm font-semibold">{b.name}</div>
              <div className="mt-1 text-xs text-slate-600">{b.address ?? '—'}</div>
            </Card>
          </Link>
        ))}
      </div>
    </Page>
  )
}

