import { useForm } from 'react-hook-form'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Input } from '../../../components/Input'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/auth'

type ProcRow = {
  id: number
  name: string
  duration_minutes: number
  price: string
  is_active: boolean
}

export function AdminProceduresPage() {
  const { token } = useAuth()
  const qc = useQueryClient()
  const q = useQuery({
    queryKey: ['adminProcedures'],
    queryFn: () => apiFetch<ProcRow[]>('/api/admin/procedures', { token: token ?? undefined }),
  })

  const createM = useMutation({
    mutationFn: (body: unknown) =>
      apiFetch('/api/admin/procedures', {
        method: 'POST',
        token: token ?? undefined,
        body: JSON.stringify(body),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['adminProcedures'] })
    },
  })

  const { register, handleSubmit, reset } = useForm<{
    name: string
    duration_minutes: number
    price: string
  }>({ defaultValues: { name: '', duration_minutes: 60, price: '0.00' } })

  return (
    <Page title="Procedures" subtitle="Manage procedure catalog.">
      <Card className="mb-3">
        <form
          className="space-y-2"
          onSubmit={handleSubmit(async (v) => {
            await createM.mutateAsync(v)
            reset()
          })}
        >
          <div className="text-sm font-semibold">Add procedure</div>
          <Input placeholder="Name" {...register('name', { required: true })} />
          <div className="flex gap-2">
            <Input
              placeholder="Duration (minutes)"
              type="number"
              {...register('duration_minutes', { valueAsNumber: true, required: true })}
            />
            <Input placeholder="Price" {...register('price', { required: true })} />
          </div>
          <Button className="w-full" disabled={createM.isPending} type="submit">
            {createM.isPending ? 'Saving…' : 'Create procedure'}
          </Button>
        </form>
      </Card>

      <div className="space-y-3">
        {(q.data ?? []).map((p) => (
          <Card key={p.id}>
            <div className="flex items-baseline justify-between gap-3">
              <div className="text-sm font-semibold">{p.name}</div>
              <div className="text-xs text-slate-600">${p.price}</div>
            </div>
            <div className="mt-1 text-xs text-slate-600">{p.duration_minutes} min</div>
          </Card>
        ))}
      </div>
    </Page>
  )
}

