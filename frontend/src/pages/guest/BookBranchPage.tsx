import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { apiFetch } from '../../api/client'
import type { Branch } from '../../api/types'
import { Card } from '../../components/Card'
import { Page } from '../../components/Page'

export function BookBranchPage() {
  const q = useQuery({
    queryKey: ['branches'],
    queryFn: () => apiFetch<Branch[]>('/api/branches'),
  })

  return (
    <Page title="Choose a branch" subtitle="Pick the salon location you want to visit.">
      {q.isLoading ? <div className="text-sm text-slate-600">Loading…</div> : null}
      {q.isError ? (
        <div className="text-sm text-rose-700">Failed to load branches.</div>
      ) : null}
      <div className="space-y-3">
        {(q.data ?? []).map((b) => (
          <Link key={b.id} to={`/book/master?branch=${b.id}`}>
            <Card className="hover:border-slate-300">
              <div className="text-sm font-semibold">{b.name}</div>
              <div className="mt-1 text-xs text-slate-600">{b.address ?? '—'}</div>
            </Card>
          </Link>
        ))}
      </div>
    </Page>
  )
}

