import { addDays, format } from 'date-fns'
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
  const procedureId = sp.get('procedure')

  const [day, setDay] = useState(() => new Date())
  const dayStr = useMemo(() => format(day, 'yyyy-MM-dd'), [day])

  const q = useQuery({
    queryKey: ['availability', masterId, procedureId, dayStr],
    enabled: !!masterId && !!procedureId,
    queryFn: () =>
      apiFetch<Availability>(
        `/api/availability?master_id=${masterId}&procedure_id=${procedureId}&date=${dayStr}`,
      ),
  })

  return (
    <Page title="Choose a time" subtitle="Pick an available time slot.">
      {!branchId || !masterId || !procedureId ? (
        <div className="text-sm text-rose-700">Missing branch/master/procedure.</div>
      ) : null}

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
      {q.isError ? <div className="text-sm text-rose-700">Failed to load availability.</div> : null}

      <div className="grid grid-cols-2 gap-3">
        {(q.data?.slots ?? []).slice(0, 24).map((slot) => (
          <Link
            key={slot}
            to={`/book/confirm?branch=${branchId}&master=${masterId}&procedure=${procedureId}&start_time=${encodeURIComponent(
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

