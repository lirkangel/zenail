import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { apiFetch } from '../../api/client'
import type { Procedure } from '../../api/types'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { Page } from '../../components/Page'

export function BookProcedurePage() {
  const [sp] = useSearchParams()
  const branchId = sp.get('branch')
  const masterId = sp.get('master')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const q = useQuery({
    queryKey: ['procedures', masterId],
    enabled: !!masterId,
    queryFn: () => apiFetch<Procedure[]>(`/api/masters/${masterId}/procedures`),
  })
  const selected = useMemo(
    () => (q.data ?? []).filter((p) => selectedIds.includes(p.id)),
    [q.data, selectedIds],
  )
  const totalPrice = selected.reduce((sum, p) => sum + Number(p.price), 0)
  const totalDuration = selected.reduce((sum, p) => sum + p.duration_minutes, 0)

  return (
    <Page title="Choose procedures" subtitle="Select one or more services for your visit.">
      {!branchId || !masterId ? (
        <div className="text-sm text-rose-700">Branch or master is missing.</div>
      ) : null}
      {q.isLoading ? <div className="text-sm text-slate-600">Loading…</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">Failed to load procedures.</div> : null}
      <div className="space-y-3">
        {(q.data ?? []).map((p) => (
          <button
            key={p.id}
            type="button"
            className="block w-full text-left"
            onClick={() =>
              setSelectedIds((current) =>
                current.includes(p.id) ? current.filter((id) => id !== p.id) : [...current, p.id],
              )
            }
          >
            <Card
              className={[
                'hover:border-slate-300',
                selectedIds.includes(p.id) ? 'border-slate-900 ring-1 ring-slate-900' : '',
              ].join(' ')}
            >
              <div className="mb-2 flex items-center justify-between gap-3">
                <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] text-slate-600">
                  {p.category ?? 'Service'}
                </span>
                <span className="text-xs text-slate-500">
                  {selectedIds.includes(p.id) ? 'Selected' : 'Tap to select'}
                </span>
              </div>
              <div className="flex items-baseline justify-between gap-3">
                <div className="text-sm font-semibold">{p.name}</div>
                <div className="text-xs text-slate-600">${p.price}</div>
              </div>
              <div className="mt-1 text-xs text-slate-600">{p.duration_minutes} min</div>
              {p.description ? (
                <div className="mt-2 text-xs leading-5 text-slate-600">{p.description}</div>
              ) : null}
            </Card>
          </button>
        ))}
      </div>

      <div className="sticky bottom-0 mt-4 border-t border-slate-200 bg-slate-50 py-3">
        <Card>
          <div className="mb-3 flex items-center justify-between text-sm">
            <div>
              <div className="font-semibold">{selected.length} selected</div>
              <div className="text-xs text-slate-600">{totalDuration} min total</div>
            </div>
            <div className="font-semibold">${totalPrice.toFixed(2)}</div>
          </div>
          <Link
            className={selected.length ? '' : 'pointer-events-none'}
            to={`/book/time?branch=${branchId}&master=${masterId}&procedures=${selectedIds.join(',')}`}
          >
            <Button className="w-full" disabled={!selected.length} type="button">
              Choose time
            </Button>
          </Link>
        </Card>
      </div>
    </Page>
  )
}

