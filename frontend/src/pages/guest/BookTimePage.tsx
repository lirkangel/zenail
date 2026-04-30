import { addDays, format, startOfDay } from 'date-fns'
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { apiFetch } from '../../api/client'
import type { Availability } from '../../api/types'
import { Card } from '../../components/Card'
import { Page } from '../../components/Page'
import { useT } from '../../state/useT'

export function BookTimePage() {
  const t = useT()
  const [sp] = useSearchParams()
  const branchId = sp.get('branch')
  const masterId = sp.get('master')
  const procedureIds = sp.get('procedures') ?? sp.get('procedure')

  const today = startOfDay(new Date())
  const [day, setDay] = useState(() => today)
  const dayStr = useMemo(() => format(day, 'yyyy-MM-dd'), [day])
  const isToday = format(day, 'yyyy-MM-dd') <= format(today, 'yyyy-MM-dd')

  const q = useQuery({
    queryKey: ['availability', masterId, procedureIds, dayStr],
    enabled: !!masterId && !!procedureIds,
    queryFn: () =>
      apiFetch<Availability>(
        `/api/availability?master_id=${masterId}&procedure_ids=${procedureIds}&date=${dayStr}`,
      ),
  })

  return (
    <Page title={t('guest.time.title')} subtitle={t('guest.time.subtitle')}>
      {!branchId || !masterId || !procedureIds ? (
        <div className="text-sm text-rose-700">{t('guest.time.missing')}</div>
      ) : null}

      <div className="mb-3 flex gap-2">
        <button
          type="button"
          disabled={isToday}
          className="rounded-xl border border-rose-200 bg-white/90 px-3 py-2 text-xs font-medium text-rose-800 shadow-sm disabled:opacity-40"
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

      {q.isLoading ? <div className="text-sm text-rose-800/80">{t('guest.time.loading')}</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">{t('guest.time.error')}</div> : null}
      {q.data ? (
        <Card className="mb-3 border-amber-100/80 bg-gradient-to-r from-amber-50/90 to-rose-50/80">
          <div className="flex items-center justify-between text-sm">
            <span className="text-rose-900/80">{t('guest.time.selectedTotal')}</span>
            <span className="font-semibold text-rose-900">${q.data.total_price}</span>
          </div>
          <div className="mt-1 text-xs text-rose-900/70">
            {t('guest.time.minutesTotal', { minutes: q.data.total_duration_minutes })}
          </div>
        </Card>
      ) : null}
      {q.data && q.data.slots.length === 0 ? (
        <div className="mb-3 text-sm text-rose-900/75">{t('guest.time.noSlots')}</div>
      ) : null}

      <div className="grid grid-cols-2 gap-3">
        {(q.data?.slots ?? []).slice(0, 24).map((slot) => (
          <Link
            key={slot}
            to={`/book/confirm?branch=${branchId}&master=${masterId}&procedures=${procedureIds}&start_time=${encodeURIComponent(
              slot,
            )}`}
          >
            <Card className="py-3 text-center transition hover:border-rose-300 hover:shadow-studio">
              <div className="text-sm font-semibold text-rose-950">
                {new Date(slot).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </Page>
  )
}
