import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Input } from '../../../components/Input'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/auth'

type MasterRow = { id: number; full_name: string; branch_id: number | null }

export function ManagerMastersPage() {
  const { token } = useAuth()
  const qc = useQueryClient()
  const q = useQuery({
    queryKey: ['managerMasters'],
    queryFn: () => apiFetch<MasterRow[]>('/api/manager/masters', { token: token ?? undefined }),
  })

  const m = useMutation({
    mutationFn: (args: { id: number; branch_id: number | null }) =>
      apiFetch(`/api/manager/masters/${args.id}`, {
        method: 'PATCH',
        token: token ?? undefined,
        body: JSON.stringify({ branch_id: args.branch_id }),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['managerMasters'] })
    },
  })

  return (
    <Page title="Masters" subtitle="Masters assigned to this branch.">
      {q.isLoading ? <div className="text-sm text-slate-600">Loading…</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">Failed to load masters.</div> : null}
      <div className="space-y-3">
        {(q.data ?? []).map((row) => (
          <MasterRowCard
            key={row.id}
            row={row}
            pending={m.isPending}
            onSave={(branchId) => m.mutate({ id: row.id, branch_id: branchId })}
          />
        ))}
      </div>
    </Page>
  )
}

function MasterRowCard({
  row,
  pending,
  onSave,
}: {
  row: MasterRow
  pending: boolean
  onSave: (branchId: number | null) => void
}) {
  const [value, setValue] = useState(row.branch_id?.toString() ?? '')
  return (
    <Card>
      <div className="text-sm font-semibold">{row.full_name}</div>
      <div className="mt-3 space-y-2">
        <div>
          <label className="mb-1 block text-[11px] font-medium text-slate-700">
            Reassign to branch id (blank to unassign)
          </label>
          <Input value={value} onChange={(e) => setValue(e.target.value)} />
        </div>
        <Button
          className="w-full"
          disabled={pending}
          type="button"
          onClick={() => onSave(value.trim() ? Number(value.trim()) : null)}
        >
          Save assignment
        </Button>
      </div>
    </Card>
  )
}

