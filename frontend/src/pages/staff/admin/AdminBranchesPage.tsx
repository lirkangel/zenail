import { useForm } from 'react-hook-form'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Input } from '../../../components/Input'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/useAuth'
import { useT } from '../../../state/useT'

type BranchRow = {
  id: number
  name: string
  address?: string | null
  open_time: string
  close_time: string
}

type NonWorkingDay = {
  id: number
  branch_id: number
  day: string
  reason?: string | null
}

export function AdminBranchesPage() {
  const t = useT()
  const { token } = useAuth()
  const qc = useQueryClient()
  const q = useQuery({
    queryKey: ['adminBranches'],
    queryFn: () => apiFetch<BranchRow[]>('/api/admin/branches', { token: token ?? undefined }),
  })

  const createM = useMutation({
    mutationFn: (body: unknown) =>
      apiFetch('/api/admin/branches', {
        method: 'POST',
        token: token ?? undefined,
        body: JSON.stringify(body),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['adminBranches'] })
    },
  })

  const { register, handleSubmit, reset } = useForm<{
    name: string
    address?: string
    open_time: string
    close_time: string
  }>({ defaultValues: { name: '', address: '', open_time: '09:00:00', close_time: '20:00:00' } })

  return (
    <Page title={t('admin.branches.title')} subtitle={t('admin.branches.subtitle')}>
      <Card className="mb-3">
        <form
          className="space-y-2"
          onSubmit={handleSubmit(async (v) => {
            await createM.mutateAsync(v)
            reset()
          })}
        >
          <div className="text-sm font-semibold text-rose-950">{t('admin.branches.add')}</div>
          <Input placeholder={t('placeholder.name')} {...register('name', { required: true })} />
          <Input placeholder={t('placeholder.address')} {...register('address')} />
          <div className="flex gap-2">
            <Input placeholder={t('placeholder.open')} {...register('open_time', { required: true })} />
            <Input placeholder={t('placeholder.close')} {...register('close_time', { required: true })} />
          </div>
          <Button className="w-full" disabled={createM.isPending} type="submit">
            {createM.isPending ? t('common.saving') : t('admin.branches.create')}
          </Button>
        </form>
      </Card>

      <div className="space-y-3">
        {(q.data ?? []).map((b) => (
          <BranchCard key={b.id} branch={b} token={token} />
        ))}
      </div>
    </Page>
  )
}

function BranchCard({ branch, token }: { branch: BranchRow; token: string | null }) {
  const t = useT()
  const qc = useQueryClient()
  const q = useQuery({
    queryKey: ['nonWorkingDays', branch.id],
    queryFn: () =>
      apiFetch<NonWorkingDay[]>(`/api/admin/branches/${branch.id}/non-working-days`, {
        token: token ?? undefined,
      }),
  })
  const createM = useMutation({
    mutationFn: (body: unknown) =>
      apiFetch(`/api/admin/branches/${branch.id}/non-working-days`, {
        method: 'POST',
        token: token ?? undefined,
        body: JSON.stringify(body),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['nonWorkingDays', branch.id] })
    },
  })
  const deleteM = useMutation({
    mutationFn: (dayId: number) =>
      apiFetch(`/api/admin/branches/${branch.id}/non-working-days/${dayId}`, {
        method: 'DELETE',
        token: token ?? undefined,
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['nonWorkingDays', branch.id] })
    },
  })
  const { register, handleSubmit, reset } = useForm<{ day: string; reason?: string }>({
    defaultValues: { day: '', reason: '' },
  })

  return (
    <Card className="transition hover:border-rose-200 hover:shadow-studio">
      <div className="text-sm font-semibold text-rose-950">{branch.name}</div>
      <div className="mt-1 text-xs text-rose-900/75">
        {t('admin.branches.hours', { open: branch.open_time, close: branch.close_time })}
      </div>
      <form
        className="mt-3 space-y-2"
        onSubmit={handleSubmit(async (v) => {
          await createM.mutateAsync(v)
          reset()
        })}
      >
        <div className="text-xs font-semibold text-rose-900">{t('admin.branches.nonWorking')}</div>
        <div className="flex gap-2">
          <Input type="date" {...register('day', { required: true })} />
          <Input placeholder={t('placeholder.reason')} {...register('reason')} />
        </div>
        <Button className="w-full" disabled={createM.isPending} type="submit">
          {t('admin.branches.addDay')}
        </Button>
      </form>
      <div className="mt-3 space-y-2">
        {(q.data ?? []).map((d) => (
          <div
            key={d.id}
            className="flex items-center justify-between gap-2 rounded-xl border border-rose-100/80 bg-rose-50/40 px-3 py-2 text-xs"
          >
            <div>
              <div className="font-semibold text-rose-950">{d.day}</div>
              <div className="text-rose-900/70">{d.reason ?? t('admin.branches.closedDefault')}</div>
            </div>
            <button
              className="font-medium text-rose-700 hover:text-rose-800"
              disabled={deleteM.isPending}
              onClick={() => deleteM.mutate(d.id)}
              type="button"
            >
              {t('admin.branches.remove')}
            </button>
          </div>
        ))}
      </div>
    </Card>
  )
}
