import { format } from 'date-fns'
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import { Card } from '../../../components/Card'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/useAuth'
import { useT } from '../../../state/useT'

type RevenueRow = { branch_id: number; total: string }
type Revenue = { from_date: string; to_date: string; total: string; by_branch: RevenueRow[] }

export function AdminRevenuePage() {
  const t = useT()
  const { token } = useAuth()
  const from = useMemo(() => format(new Date(), 'yyyy-MM-01'), [])
  const to = useMemo(() => format(new Date(), 'yyyy-MM-dd'), [])

  const q = useQuery({
    queryKey: ['adminRevenue', from, to],
    queryFn: () => apiFetch<Revenue>(`/api/admin/revenue?from=${from}&to=${to}`, { token: token ?? undefined }),
  })

  return (
    <Page title={t('admin.revenue.title')} subtitle={t('admin.revenue.subtitle')}>
      <Card className="mb-3 border-amber-100/80 bg-gradient-to-br from-amber-50/80 to-rose-50/70">
        <div className="text-xs text-rose-900/75">
          {t('common.range')}: {from} → {to}
        </div>
        <div className="mt-2 text-2xl font-semibold text-rose-950">${q.data?.total ?? t('common.emDash')}</div>
      </Card>

      <div className="space-y-3">
        {(q.data?.by_branch ?? []).map((r) => (
          <Card key={r.branch_id} className="transition hover:border-rose-200 hover:shadow-studio">
            <div className="flex items-baseline justify-between">
              <div className="text-sm font-semibold text-rose-950">{t('admin.revenue.branch', { id: r.branch_id })}</div>
              <div className="text-sm font-semibold text-rose-950">${r.total}</div>
            </div>
          </Card>
        ))}
      </div>
    </Page>
  )
}
