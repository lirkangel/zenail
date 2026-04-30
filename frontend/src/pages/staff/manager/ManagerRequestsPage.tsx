import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/auth'

type ReqRow = {
  id: number
  appointment_id: number
  master_id: number
  proposed_start_time: string
  reason?: string | null
  status: 'pending' | 'approved' | 'rejected'
}

export function ManagerRequestsPage() {
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
    <Page title="Requests" subtitle="Time change requests from masters.">
      {q.isLoading ? <div className="text-sm text-slate-600">Loading…</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">Failed to load requests.</div> : null}
      <div className="space-y-3">
        {(q.data ?? []).map((r) => (
          <Card key={r.id}>
            <div className="text-sm font-semibold">Appointment #{r.appointment_id}</div>
            <div className="mt-1 text-xs text-slate-600">Proposed: {r.proposed_start_time}</div>
            {r.reason ? <div className="mt-1 text-xs text-slate-600">Reason: {r.reason}</div> : null}
            <div className="mt-2 flex gap-2">
              <Button
                className="flex-1"
                disabled={decide.isPending || r.status !== 'pending'}
                onClick={() => decide.mutate({ id: r.id, status: 'approved' })}
                type="button"
              >
                Approve
              </Button>
              <Button
                className="flex-1 bg-white text-slate-900 border border-slate-200 hover:bg-slate-50"
                disabled={decide.isPending || r.status !== 'pending'}
                onClick={() => decide.mutate({ id: r.id, status: 'rejected' })}
                type="button"
              >
                Reject
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </Page>
  )
}

