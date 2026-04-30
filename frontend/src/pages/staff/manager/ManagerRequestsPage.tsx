import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/auth'
import { useT } from '../../../state/i18n'

type ReqRow = {
  id: number
  appointment_id: number
  master_id: number
  proposed_start_time: string
  reason?: string | null
  status: 'pending' | 'approved' | 'rejected'
}

export function ManagerRequestsPage() {
  const t = useT()
  const { token } = useAuth()
  const qc = useQueryClient()

  const q = useQuery({
    queryKey: ['managerRequests'],
    queryFn: () => apiFetch<ReqRow[]>('/api/manager/reschedule-requests', { token: token ?? undefined }),
  })

  const decide = useMutation({
    mutationFn: ({ id, status }: { id: number; status: 'approved' | 'rejected' }) =>
      apiFetch(`/api/manager/reschedule-requests/${id}`, {
        method: 'PATCH',
        token: token ?? undefined,
        body: JSON.stringify({ status }),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['managerRequests'] })
      await qc.invalidateQueries({ queryKey: ['managerAppointments'] })
    },
  })

  return (
    <Page title={t('manager.requests.title')} subtitle={t('manager.requests.subtitle')}>
      {q.isLoading ? <div className="text-sm text-rose-800/80">{t('common.loading')}</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">{t('manager.requests.error')}</div> : null}
      <div className="space-y-3">
        {(q.data ?? []).map((r) => (
          <Card key={r.id} className="transition hover:border-rose-200 hover:shadow-studio">
            <div className="text-sm font-semibold text-rose-950">
              {t('manager.requests.appointment', { id: r.appointment_id })}
            </div>
            <div className="mt-1 text-xs text-rose-900/75">
              {t('manager.requests.proposed')}: {r.proposed_start_time}
            </div>
            {r.reason ? (
              <div className="mt-1 text-xs text-rose-900/75">
                {t('manager.requests.reason')}: {r.reason}
              </div>
            ) : null}
            <div className="mt-2 flex gap-2">
              <Button
                className="flex-1"
                disabled={decide.isPending || r.status !== 'pending'}
                onClick={() => decide.mutate({ id: r.id, status: 'approved' })}
                type="button"
              >
                {t('manager.requests.approve')}
              </Button>
              <Button
                variant="secondary"
                className="flex-1"
                disabled={decide.isPending || r.status !== 'pending'}
                onClick={() => decide.mutate({ id: r.id, status: 'rejected' })}
                type="button"
              >
                {t('manager.requests.reject')}
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </Page>
  )
}
