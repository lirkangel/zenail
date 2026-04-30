import { addDays, format, startOfDay } from 'date-fns'
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { apiFetch } from '../../api/client'
import type { Availability } from '../../api/types'
import { Card } from '../../components/Card'
import { Page } from '../../components/Page'

export function BookTimePage() {
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
    <Page title="Choose a time" subtitle="Pick an available time slot.">
      {!branchId || !masterId || !procedureIds ? (
        <div className="text-sm text-rose-700">Missing branch/master/procedure.</div>
      ) : null}

      <div className="mb-3 flex gap-2">
        <button
          type="button"
          disabled={isToday}
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs disabled:opacity-40"
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
      {q.isError ? <div className="text-sm text-rose-700">Failed to load availability.</div> : null}
      {q.data ? (
        <Card className="mb-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-600">Selected total</span>
            <span className="font-semibold">${q.data.total_price}</span>
          </div>
          <div className="mt-1 text-xs text-slate-600">{q.data.total_duration_minutes} minutes</div>
        </Card>
      ) : null}
      {q.data && q.data.slots.length === 0 ? (
        <div className="mb-3 text-sm text-slate-600">
          No available slots for this day. Try another date.
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-3">
        {(q.data?.slots ?? []).slice(0, 24).map((slot) => (
          <Link
            key={slot}
            to={`/book/confirm?branch=${branchId}&master=${masterId}&procedures=${procedureIds}&start_time=${encodeURIComponent(
              slot,
            )}`}
          >
            <Card className="py-3 text-center hover:border-slate-300">
              <div className="text-sm font-semibold">
                {new Date(slot).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </Page>
  )
}

