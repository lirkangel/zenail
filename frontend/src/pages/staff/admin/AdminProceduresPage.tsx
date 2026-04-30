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
  description?: string | null
  category?: string | null
  duration_minutes: number
  price: string
  is_active: boolean
}

type ProcedureForm = {
  name: string
  description?: string
  category?: string
  duration_minutes: number
  price: string
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
  const updateM = useMutation({
    mutationFn: ({ id, body }: { id: number; body: unknown }) =>
      apiFetch(`/api/admin/procedures/${id}`, {
        method: 'PATCH',
        token: token ?? undefined,
        body: JSON.stringify(body),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['adminProcedures'] })
    },
  })
  const deleteM = useMutation({
    mutationFn: (id: number) =>
      apiFetch(`/api/admin/procedures/${id}`, {
        method: 'DELETE',
        token: token ?? undefined,
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['adminProcedures'] })
    },
  })

  const { register, handleSubmit, reset } = useForm<ProcedureForm>({
    defaultValues: { name: '', description: '', category: '', duration_minutes: 60, price: '0.00' },
  })

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
          <Input placeholder="Category (Hands, Feet, Add-ons)" {...register('category')} />
          <Input placeholder="Description" {...register('description')} />
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
          <ProcedureEditor
            key={p.id}
            procedure={p}
            pending={updateM.isPending || deleteM.isPending}
            onSave={(body) => updateM.mutate({ id: p.id, body })}
            onRemove={() => deleteM.mutate(p.id)}
          />
        ))}
      </div>
    </Page>
  )
}

function ProcedureEditor({
  procedure,
  pending,
  onSave,
  onRemove,
}: {
  procedure: ProcRow
  pending: boolean
  onSave: (body: ProcedureForm & { is_active: boolean }) => void
  onRemove: () => void
}) {
  const { register, handleSubmit } = useForm<ProcedureForm>({
    defaultValues: {
      name: procedure.name,
      category: procedure.category ?? '',
      description: procedure.description ?? '',
      duration_minutes: procedure.duration_minutes,
      price: procedure.price,
    },
  })

  return (
    <Card className={!procedure.is_active ? 'opacity-60' : ''}>
      <form className="space-y-2" onSubmit={handleSubmit((v) => onSave({ ...v, is_active: true }))}>
        <div className="flex items-center justify-between gap-3">
          <div className="text-sm font-semibold">Procedure #{procedure.id}</div>
          <div className="text-xs text-slate-500">{procedure.is_active ? 'active' : 'removed'}</div>
        </div>
        <Input placeholder="Name" {...register('name', { required: true })} />
        <Input placeholder="Category" {...register('category')} />
        <Input placeholder="Description" {...register('description')} />
        <div className="flex gap-2">
          <Input
            placeholder="Duration"
            type="number"
            {...register('duration_minutes', { valueAsNumber: true, required: true })}
          />
          <Input placeholder="Price" {...register('price', { required: true })} />
        </div>
        <div className="flex gap-2">
          <Button className="flex-1" disabled={pending} type="submit">
            Save
          </Button>
          <Button
            className="flex-1 border border-slate-200 bg-white text-slate-900 hover:bg-slate-50"
            disabled={pending || !procedure.is_active}
            onClick={onRemove}
            type="button"
          >
            Remove
          </Button>
        </div>
      </form>
    </Card>
  )
}

