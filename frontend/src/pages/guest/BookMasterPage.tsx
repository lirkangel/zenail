import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { apiFetch } from '../../api/client'
import type { Master } from '../../api/types'
import { Card } from '../../components/Card'
import { Page } from '../../components/Page'

export function BookMasterPage() {
  const [sp] = useSearchParams()
  const branchId = sp.get('branch')
  const q = useQuery({
    queryKey: ['masters', branchId],
    enabled: !!branchId,
    queryFn: () => apiFetch<Master[]>(`/api/branches/${branchId}/masters`),
  })

  return (
    <Page title="Choose a master" subtitle="Select the nail master you prefer.">
      {!branchId ? <div className="text-sm text-rose-700">Branch is missing.</div> : null}
      {q.isLoading ? <div className="text-sm text-slate-600">Loading…</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">Failed to load masters.</div> : null}
      <div className="space-y-4">
        {(q.data ?? []).map((m) => (
          <Link key={m.id} to={`/book/procedure?branch=${branchId}&master=${m.id}`}>
            <Card className="p-5 hover:border-slate-300">
              <div className="text-sm font-semibold">{m.full_name}</div>
            </Card>
          </Link>
        ))}
      </div>
    </Page>
  )
}

