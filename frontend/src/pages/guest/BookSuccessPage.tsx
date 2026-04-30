import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { apiFetch } from '../../api/client'
import type { Appointment } from '../../api/types'
import { Card } from '../../components/Card'
import { Page } from '../../components/Page'
import { appointmentStatusLabel, useT } from '../../state/useT'
import { getLastBooking } from '../../state/booking'

export function BookSuccessPage() {
  const t = useT()
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
    <Page title={t('guest.success.title')} subtitle={t('guest.success.subtitle')}>
      <Card className="border-emerald-100/90 bg-gradient-to-br from-emerald-50/90 to-rose-50/60">
        <div className="text-sm text-rose-950">
          {t('guest.success.appointmentId')}: <span className="font-semibold">{id ?? t('common.emDash')}</span>
        </div>
        {q.data ? (
          <div className="mt-3 space-y-1 text-xs text-rose-900/85">
            <div>
              {t('guest.success.status')}:{' '}
              <span className="font-semibold">{appointmentStatusLabel(t, q.data.status)}</span>
            </div>
            <div>
              {t('guest.success.time')}: {new Date(q.data.start_time).toLocaleString()}
            </div>
            <div>
              {t('guest.success.total')}: ${q.data.price} / {q.data.total_duration_minutes} {t('common.minutes')}
            </div>
            <div>
              {t('guest.success.procedures')}: {q.data.procedures.map((p) => p.name).join(', ')}
            </div>
          </div>
        ) : null}
        <div className="mt-2 text-xs text-rose-900/70">{t('guest.success.footer')}</div>
      </Card>
    </Page>
  )
}
