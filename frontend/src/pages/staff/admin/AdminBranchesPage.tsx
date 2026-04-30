import { useForm } from 'react-hook-form'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Input } from '../../../components/Input'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/auth'

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
    <Page title="Branches" subtitle="Manage branch locations.">
      <Card className="mb-3">
        <form
          className="space-y-2"
          onSubmit={handleSubmit(async (v) => {
            await createM.mutateAsync(v)
            reset()
          })}
        >
          <div className="text-sm font-semibold">Add branch</div>
          <Input placeholder="Name" {...register('name', { required: true })} />
          <Input placeholder="Address" {...register('address')} />
          <div className="flex gap-2">
            <Input placeholder="Open (HH:MM:SS)" {...register('open_time', { required: true })} />
            <Input placeholder="Close (HH:MM:SS)" {...register('close_time', { required: true })} />
          </div>
          <Button className="w-full" disabled={createM.isPending} type="submit">
            {createM.isPending ? 'Saving…' : 'Create branch'}
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
    <Card>
      <div className="text-sm font-semibold">{branch.name}</div>
      <div className="mt-1 text-xs text-slate-600">
        Hours: {branch.open_time} – {branch.close_time}
      </div>
      <form
        className="mt-3 space-y-2"
        onSubmit={handleSubmit(async (v) => {
          await createM.mutateAsync(v)
          reset()
        })}
      >
        <div className="text-xs font-semibold text-slate-700">Not working day</div>
        <div className="flex gap-2">
          <Input type="date" {...register('day', { required: true })} />
          <Input placeholder="Reason" {...register('reason')} />
        </div>
        <Button className="w-full" disabled={createM.isPending} type="submit">
          Add / update closed day
        </Button>
      </form>
      <div className="mt-3 space-y-2">
        {(q.data ?? []).map((d) => (
          <div
            key={d.id}
            className="flex items-center justify-between gap-2 rounded-xl bg-slate-50 px-3 py-2 text-xs"
          >
            <div>
              <div className="font-semibold">{d.day}</div>
              <div className="text-slate-600">{d.reason ?? 'Closed'}</div>
            </div>
            <button
              className="text-rose-700"
              disabled={deleteM.isPending}
              onClick={() => deleteM.mutate(d.id)}
              type="button"
            >
              Remove
            </button>
          </div>
        ))}
      </div>
    </Card>
  )
}

