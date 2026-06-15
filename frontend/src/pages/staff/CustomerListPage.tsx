import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { apiFetch } from '../../api/client'
import type { CustomerList, CustomerSummary } from '../../api/types'
import { Card } from '../../components/Card'
import { Input } from '../../components/Input'
import { Page } from '../../components/Page'
import { CustomerCrmSummary } from '../../components/CustomerCrmSummary'
import { useAuth } from '../../state/useAuth'
import { useT } from '../../state/useT'

export function CustomerListPage() {
  const t = useT()
  const { me, token } = useAuth()
  const [search, setSearch] = useState('')
  const prefix = me?.role === 'admin' ? '/api/admin' : '/api/manager'
  const query = useMemo(() => search.trim(), [search])

  const q = useQuery({
    queryKey: ['customers', prefix, query],
    queryFn: () =>
      apiFetch<CustomerList>(`${prefix}/customers${query ? `?q=${encodeURIComponent(query)}` : ''}`, {
        token: token ?? undefined,
      }),
    enabled: Boolean(token && me && me.role !== 'master'),
  })

  return (
    <Page title={t('customers.title')} subtitle={t('customers.subtitle')}>
      <div className="mb-3">
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('customers.searchPlaceholder')}
        />
      </div>

      {q.isLoading ? <div className="text-sm text-rose-800/80">{t('common.loading')}</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">{t('customers.error')}</div> : null}
      {q.data && q.data.items.length === 0 ? (
        <div className="text-sm text-rose-900/70">{t('customers.empty')}</div>
      ) : null}

      <div className="space-y-3">
        {(q.data?.items ?? []).map((customer) => (
          <CustomerCard key={customer.id} customer={customer} detailPath={me?.role === 'admin' ? `/staff/customers/${customer.id}` : `/staff/customers/${customer.id}`} />
        ))}
      </div>
    </Page>
  )
}

function CustomerCard({ customer, detailPath }: { customer: CustomerSummary; detailPath: string }) {
  const t = useT()
  return (
    <Link to={detailPath} className="block">
      <Card className="transition hover:border-rose-200 hover:shadow-studio">
        <div className="flex items-baseline justify-between gap-3">
          <div className="min-w-0 truncate text-sm font-semibold text-rose-950">{customer.full_name}</div>
          <div className="shrink-0 text-xs font-medium text-rose-900/70">
            {t('customers.visits', { count: customer.visit_count })}
          </div>
        </div>
        <div className="mt-1 text-xs text-rose-900/75">{customer.phone}</div>
        {customer.email ? <div className="mt-1 text-xs text-rose-900/65">{customer.email}</div> : null}
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-rose-900/70">
          <div>
            <div className="font-medium text-rose-950">{customer.completed_spend}</div>
            <div>{t('customers.completedSpend')}</div>
          </div>
          <div>
            <div className="font-medium text-rose-950">
              {customer.latest_visit ? new Date(customer.latest_visit).toLocaleDateString() : t('common.emDash')}
            </div>
            <div>{t('customers.latestVisit')}</div>
          </div>
        </div>
        <CustomerCrmSummary
          compact
          customer={{
            id: customer.id,
            full_name: customer.full_name,
            phone: customer.phone,
            email: customer.email,
            notes: customer.notes,
          }}
          tags={customer.tags}
          preferences={customer.preferences}
        />
      </Card>
    </Link>
  )
}
