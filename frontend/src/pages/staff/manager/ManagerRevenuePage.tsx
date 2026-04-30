import { format } from 'date-fns'
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import { Card } from '../../../components/Card'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/useAuth'
import { useT } from '../../../state/useT'

type Revenue = { from_date: string; to_date: string; total: string }

export function ManagerRevenuePage() {
  const t = useT()
  const { token } = useAuth()
  const from = useMemo(() => format(new Date(), 'yyyy-MM-01'), [])
  const to = useMemo(() => format(new Date(), 'yyyy-MM-dd'), [])

  const q = useQuery({
    queryKey: ['managerRevenue', from, to],
    queryFn: () => apiFetch<Revenue>(`/api/manager/revenue?from=${from}&to=${to}`, { token: token ?? undefined }),
  })

  return (
    <Page title={t('manager.revenue.title')} subtitle={t('manager.revenue.subtitle')}>
      <Card className="border-amber-100/80 bg-gradient-to-br from-amber-50/80 to-rose-50/70">
        <div className="text-xs text-rose-900/75">
          {t('common.range')}: {from} → {to}
        </div>
        <div className="mt-2 text-2xl font-semibold text-rose-950">${q.data?.total ?? t('common.emDash')}</div>
      </Card>
    </Page>
  )
}
