import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { apiFetch } from '../../api/client'
import type { Procedure } from '../../api/types'
import { Card } from '../../components/Card'
import { Page } from '../../components/Page'

export function BookProcedurePage() {
  const [sp] = useSearchParams()
  const branchId = sp.get('branch')
  const masterId = sp.get('master')
  const q = useQuery({
    queryKey: ['procedures', masterId],
    enabled: !!masterId,
    queryFn: () => apiFetch<Procedure[]>(`/api/masters/${masterId}/procedures`),
  })

  return (
    <Page title="Choose a procedure" subtitle="Duration and price may vary by procedure.">
      {!branchId || !masterId ? (
        <div className="text-sm text-rose-700">Branch or master is missing.</div>
      ) : null}
      {q.isLoading ? <div className="text-sm text-slate-600">Loading…</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">Failed to load procedures.</div> : null}
      <div className="space-y-3">
        {(q.data ?? []).map((p) => (
          <Link
            key={p.id}
            to={`/book/time?branch=${branchId}&master=${masterId}&procedure=${p.id}`}
          >
            <Card className="hover:border-slate-300">
              <div className="flex items-baseline justify-between gap-3">
                <div className="text-sm font-semibold">{p.name}</div>
                <div className="text-xs text-slate-600">${p.price}</div>
              </div>
              <div className="mt-1 text-xs text-slate-600">{p.duration_minutes} min</div>
            </Card>
          </Link>
        ))}
      </div>
    </Page>
  )
}

