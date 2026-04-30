import { format } from 'date-fns'
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import { Card } from '../../../components/Card'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/auth'

type RevenueRow = { branch_id: number; total: string }
type Revenue = { from_date: string; to_date: string; total: string; by_branch: RevenueRow[] }

export function AdminRevenuePage() {
  const { token } = useAuth()
  const from = useMemo(() => format(new Date(), 'yyyy-MM-01'), [])
  const to = useMemo(() => format(new Date(), 'yyyy-MM-dd'), [])

  const q = useQuery({
    queryKey: ['adminRevenue', from, to],
    queryFn: () => apiFetch<Revenue>(`/api/admin/revenue?from=${from}&to=${to}`, { token: token ?? undefined }),
  })

  return (
    <Page title="Revenue" subtitle="Total + by-branch completed revenue.">
      <Card className="mb-3">
        <div className="text-xs text-slate-600">
          Range: {from} → {to}
        </div>
        <div className="mt-2 text-2xl font-semibold">${q.data?.total ?? '—'}</div>
      </Card>

      <div className="space-y-3">
        {(q.data?.by_branch ?? []).map((r) => (
          <Card key={r.branch_id}>
            <div className="flex items-baseline justify-between">
              <div className="text-sm font-semibold">Branch #{r.branch_id}</div>
              <div className="text-sm font-semibold">${r.total}</div>
            </div>
          </Card>
        ))}
      </div>
    </Page>
  )
}

