import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Input } from '../../../components/Input'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/useAuth'
import { useT } from '../../../state/useT'

type MasterRow = { id: number; full_name: string; branch_id: number | null }

export function ManagerMastersPage() {
  const t = useT()
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
    <Page title={t('manager.masters.title')} subtitle={t('manager.masters.subtitle')}>
      {q.isLoading ? <div className="text-sm text-rose-800/80">{t('common.loading')}</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">{t('manager.masters.error')}</div> : null}
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
  const t = useT()
  const [value, setValue] = useState(row.branch_id?.toString() ?? '')
  return (
    <Card className="transition hover:border-rose-200 hover:shadow-studio">
      <div className="text-sm font-semibold text-rose-950">{row.full_name}</div>
      <div className="mt-3 space-y-2">
        <div>
          <label className="mb-1 block text-[11px] font-medium text-rose-900/80">
            {t('manager.masters.reassignLabel')}
          </label>
          <Input value={value} onChange={(e) => setValue(e.target.value)} />
        </div>
        <Button
          className="w-full"
          disabled={pending}
          type="button"
          onClick={() => onSave(value.trim() ? Number(value.trim()) : null)}
        >
          {t('manager.masters.saveAssignment')}
        </Button>
      </div>
    </Card>
  )
}
