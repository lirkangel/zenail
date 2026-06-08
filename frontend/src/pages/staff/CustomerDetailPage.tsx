import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { apiFetch } from '../../api/client'
import type { CustomerDetail } from '../../api/types'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { Page } from '../../components/Page'
import { useAuth } from '../../state/useAuth'
import { appointmentStatusLabel, useT } from '../../state/useT'

export function CustomerDetailPage() {
  const t = useT()
  const { id } = useParams()
  const { me, token } = useAuth()
  const qc = useQueryClient()
  const prefix = me?.role === 'admin' ? '/api/admin' : '/api/manager'

  const q = useQuery({
    queryKey: ['customerDetail', prefix, id],
    queryFn: () => apiFetch<CustomerDetail>(`${prefix}/customers/${id}`, { token: token ?? undefined }),
    enabled: Boolean(token && id && me && me.role !== 'master'),
  })

  const customer = q.data
  return (
    <Page title={customer?.full_name ?? t('customers.detailTitle')} subtitle={t('customers.detailSubtitle')}>
      {q.isLoading ? <div className="text-sm text-rose-800/80">{t('common.loading')}</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">{t('customers.error')}</div> : null}

      {customer ? (
        <div className="space-y-3">
          <Card>
            <div className="text-sm font-semibold text-rose-950">{customer.full_name}</div>
            <div className="mt-1 text-xs text-rose-900/70">{customer.phone}</div>
            {customer.email ? <div className="mt-1 text-xs text-rose-900/70">{customer.email}</div> : null}
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-rose-900/70">
              <Metric label={t('customers.visitsLabel')} value={String(customer.visit_count)} />
              <Metric label={t('customers.completedSpend')} value={customer.completed_spend} />
              <Metric
                label={t('customers.latestVisit')}
                value={customer.latest_visit ? new Date(customer.latest_visit).toLocaleDateString() : t('common.emDash')}
              />
              <Metric
                label={t('customers.upcoming')}
                value={
                  customer.upcoming_appointment
                    ? new Date(customer.upcoming_appointment).toLocaleDateString()
                    : t('common.emDash')
                }
              />
            </div>
          </Card>

          <NotesEditor
            key={customer.id}
            initialNotes={customer.notes ?? ''}
            endpoint={`${prefix}/customers/${id}`}
            token={token ?? undefined}
            onSaved={async () => {
              await qc.invalidateQueries({ queryKey: ['customerDetail', prefix, id] })
              await qc.invalidateQueries({ queryKey: ['customers'] })
            }}
          />

          <div className="space-y-3">
            <div className="text-sm font-semibold text-rose-950">{t('customers.history')}</div>
            {customer.appointments.length === 0 ? (
              <div className="text-sm text-rose-900/70">{t('customers.noHistory')}</div>
            ) : null}
            {customer.appointments.map((appt) => (
              <Card key={appt.id}>
                <div className="flex items-baseline justify-between gap-3">
                  <div className="text-sm font-semibold text-rose-950">
                    {new Date(appt.start_time).toLocaleString()}
                  </div>
                  <div className="text-xs font-medium text-rose-900/70">
                    {appointmentStatusLabel(t, appt.status)}
                  </div>
                </div>
                <div className="mt-1 text-xs text-rose-900/70">
                  {appt.master_name ?? `#${appt.master_id}`}
                </div>
                <div className="mt-1 text-xs text-rose-900/70">
                  {appt.procedures.join(', ') || t('common.procedureFallback', { id: appt.id })}
                </div>
                <div className="mt-1 text-xs font-medium text-rose-950">{appt.price}</div>
              </Card>
            ))}
          </div>
        </div>
      ) : null}
    </Page>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="font-medium text-rose-950">{value}</div>
      <div>{label}</div>
    </div>
  )
}

function NotesEditor({
  initialNotes,
  endpoint,
  token,
  onSaved,
}: {
  initialNotes: string
  endpoint: string
  token?: string
  onSaved: () => Promise<void>
}) {
  const t = useT()
  const [notes, setNotes] = useState(initialNotes)
  const saveNotes = useMutation({
    mutationFn: () =>
      apiFetch<CustomerDetail>(endpoint, {
        method: 'PATCH',
        token,
        body: JSON.stringify({ notes: notes.trim() || null }),
      }),
    onSuccess: onSaved,
  })

  return (
    <Card>
      <div className="mb-2 text-sm font-semibold text-rose-950">{t('customers.notes')}</div>
      <textarea
        className="min-h-24 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-rose-950 focus:outline-none focus:ring-2 focus:ring-rose-400/40"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
      <Button className="mt-2 w-full" disabled={saveNotes.isPending} type="button" onClick={() => saveNotes.mutate()}>
        {saveNotes.isPending ? t('common.saving') : t('common.save')}
      </Button>
    </Card>
  )
}
