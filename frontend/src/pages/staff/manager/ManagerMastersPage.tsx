import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import { Card } from '../../../components/Card'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/useAuth'
import { useT } from '../../../state/useT'

type MasterRow = { id: number; full_name: string; branch_id: number | null }
type BranchRow = { id: number; name: string }

export function ManagerMastersPage() {
  const t = useT()
  const { token } = useAuth()
  const q = useQuery({
    queryKey: ['managerMasters'],
    queryFn: () => apiFetch<MasterRow[]>('/api/manager/masters', { token: token ?? undefined }),
  })
  const branchesQ = useQuery({
    queryKey: ['managerBranches'],
    queryFn: () => apiFetch<BranchRow[]>('/api/branches'),
  })
  const branchNameById = new Map((branchesQ.data ?? []).map((branch) => [branch.id, branch.name]))

  return (
    <Page title={t('manager.masters.title')} subtitle={t('manager.masters.subtitle')}>
      {q.isLoading ? <div className="text-sm text-rose-800/80">{t('common.loading')}</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">{t('manager.masters.error')}</div> : null}
      <div className="space-y-3">
        {(q.data ?? []).map((row) => (
          <MasterRowCard
            key={row.id}
            row={row}
            branchName={row.branch_id ? (branchNameById.get(row.branch_id) ?? t('common.emDash')) : t('common.emDash')}
          />
        ))}
      </div>
    </Page>
  )
}

function MasterRowCard({
  row,
  branchName,
}: {
  row: MasterRow
  branchName: string
}) {
  const t = useT()
  return (
    <Card className="transition hover:border-rose-200 hover:shadow-studio">
      <div className="text-sm font-semibold text-rose-950">{row.full_name}</div>
      <div className="mt-2 text-xs text-rose-900/75">
        {t('manager.masters.branchLabel', { branch: branchName })}
      </div>
      <div className="mt-3 text-xs text-rose-900/65">{t('manager.masters.branchLocked')}</div>
    </Card>
  )
}
