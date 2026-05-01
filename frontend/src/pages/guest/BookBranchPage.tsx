import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { apiFetch } from '../../api/client'
import type { Appointment, Branch } from '../../api/types'
import { Card } from '../../components/Card'
import { Page } from '../../components/Page'
import { appointmentStatusLabel, useT } from '../../state/useT'
import { getLastBooking } from '../../state/booking'

export function BookBranchPage() {
  const t = useT()
  const lastBooking = getLastBooking()
  const q = useQuery({
    queryKey: ['branches'],
    queryFn: () => apiFetch<Branch[]>('/api/branches'),
  })
  const lastQ = useQuery({
    queryKey: ['lastBooking', lastBooking?.booking_reference],
    enabled: !!lastBooking,
    queryFn: () =>
      apiFetch<Appointment>(
        `/api/appointments/by-reference/${encodeURIComponent(lastBooking!.booking_reference)}`,
      ),
  })

  return (
    <Page title={t('guest.branch.title')} subtitle={t('guest.branch.subtitle')}>
      {lastQ.data ? (
        <Card className="mb-6 border-amber-200/80 bg-gradient-to-br from-amber-50 to-rose-50/80">
          <div className="text-sm font-semibold">
            {t('guest.branch.lastBooking', {
              status: appointmentStatusLabel(t, lastQ.data.status),
            })}
          </div>
          <div className="mt-1 text-xs text-slate-700">
            {new Date(lastQ.data.start_time).toLocaleString()} · ${lastQ.data.price} ·{' '}
            {lastQ.data.total_duration_minutes} {t('common.minutes')}
          </div>
          <div className="mt-1 text-xs text-slate-600">
            {lastQ.data.procedures.map((p) => p.name).join(', ')}
          </div>
        </Card>
      ) : null}

      {q.isLoading ? <div className="text-sm text-rose-800/80">{t('guest.branch.loading')}</div> : null}
      {q.isError ? (
        <div className="text-sm text-rose-700">{t('guest.branch.error')}</div>
      ) : null}
      <div className="space-y-5">
        {(q.data ?? []).map((b) => (
          <Link key={b.id} to={`/book/master?branch=${b.id}`} className="block">
            <Card className="p-6 transition hover:-translate-y-0.5 hover:border-rose-300 hover:shadow-studio">
              <div className="text-sm font-semibold text-rose-950">{b.name}</div>
              <div className="mt-1 text-xs text-rose-900/70">{b.address ?? t('common.emDash')}</div>
            </Card>
          </Link>
        ))}
      </div>
    </Page>
  )
}
