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
          <Card key={b.id}>
            <div className="text-sm font-semibold">{b.name}</div>
            <div className="mt-1 text-xs text-slate-600">
              Hours: {b.open_time} – {b.close_time}
            </div>
          </Card>
        ))}
      </div>
    </Page>
  )
}

