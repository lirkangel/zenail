import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { apiFetch } from '../../api/client'
import type { Master } from '../../api/types'
import { Card } from '../../components/Card'
import { Page } from '../../components/Page'
import { useT } from '../../state/useT'

export function BookMasterPage() {
  const t = useT()
  const [sp] = useSearchParams()
  const branchId = sp.get('branch')
  const q = useQuery({
    queryKey: ['masters', branchId],
    enabled: !!branchId,
    queryFn: () => apiFetch<Master[]>(`/api/branches/${branchId}/masters`),
  })

  return (
    <Page title={t('guest.master.title')} subtitle={t('guest.master.subtitle')}>
      {!branchId ? <div className="text-sm text-rose-700">{t('guest.master.missingBranch')}</div> : null}
      {q.isLoading ? <div className="text-sm text-rose-800/80">{t('guest.master.loading')}</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">{t('guest.master.error')}</div> : null}
      <div className="space-y-4">
        {(q.data ?? []).map((m) => (
          <Link key={m.id} to={`/book/procedure?branch=${branchId}&master=${m.id}`}>
            <Card className="p-5 transition hover:border-rose-300 hover:shadow-studio">
              <div className="text-sm font-semibold text-rose-950">{m.full_name}</div>
            </Card>
          </Link>
        ))}
      </div>
    </Page>
  )
}
