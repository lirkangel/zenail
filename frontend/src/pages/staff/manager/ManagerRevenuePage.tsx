import { format } from 'date-fns'
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import { Card } from '../../../components/Card'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/auth'

type Revenue = { from_date: string; to_date: string; total: string }

export function ManagerRevenuePage() {
  const { token } = useAuth()
  const from = useMemo(() => format(new Date(), 'yyyy-MM-01'), [])
  const to = useMemo(() => format(new Date(), 'yyyy-MM-dd'), [])

  const q = useQuery({
    queryKey: ['managerRevenue', from, to],
    queryFn: () => apiFetch<Revenue>(`/api/manager/revenue?from=${from}&to=${to}`, { token: token ?? undefined }),
  })

  return (
    <Page title="Revenue" subtitle="Completed appointments total.">
      <Card>
        <div className="text-xs text-slate-600">
          Range: {from} → {to}
        </div>
        <div className="mt-2 text-2xl font-semibold">${q.data?.total ?? '—'}</div>
      </Card>
    </Page>
  )
}

