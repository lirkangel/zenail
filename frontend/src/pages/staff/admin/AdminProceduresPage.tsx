import { useForm } from 'react-hook-form'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Input } from '../../../components/Input'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/useAuth'
import { useT } from '../../../state/useT'

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
  const t = useT()
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
    <Page title={t('admin.procedures.title')} subtitle={t('admin.procedures.subtitle')}>
      <Card className="mb-3">
        <form
          className="space-y-2"
          onSubmit={handleSubmit(async (v) => {
            await createM.mutateAsync(v)
            reset()
          })}
        >
          <div className="text-sm font-semibold text-rose-950">{t('admin.procedures.add')}</div>
          <Input placeholder={t('placeholder.name')} {...register('name', { required: true })} />
          <Input placeholder={t('placeholder.category')} {...register('category')} />
          <Input placeholder={t('placeholder.description')} {...register('description')} />
          <div className="flex gap-2">
            <Input
              placeholder={t('placeholder.duration')}
              type="number"
              {...register('duration_minutes', { valueAsNumber: true, required: true })}
            />
            <Input placeholder={t('placeholder.price')} {...register('price', { required: true })} />
          </div>
          <Button className="w-full" disabled={createM.isPending} type="submit">
            {createM.isPending ? t('common.saving') : t('admin.procedures.create')}
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
  const t = useT()
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
    <Card className={!procedure.is_active ? 'opacity-60' : 'transition hover:border-rose-200 hover:shadow-studio'}>
      <form className="space-y-2" onSubmit={handleSubmit((v) => onSave({ ...v, is_active: true }))}>
        <div className="flex items-center justify-between gap-3">
          <div className="text-sm font-semibold text-rose-950">
            {t('admin.procedures.procedure', { id: procedure.id })}
          </div>
          <div className="text-xs text-rose-900/60">
            {procedure.is_active ? t('admin.procedures.active') : t('admin.procedures.removed')}
          </div>
        </div>
        <Input placeholder={t('placeholder.name')} {...register('name', { required: true })} />
        <Input placeholder={t('placeholder.category')} {...register('category')} />
        <Input placeholder={t('placeholder.description')} {...register('description')} />
        <div className="flex gap-2">
          <Input
            placeholder={t('placeholder.duration')}
            type="number"
            {...register('duration_minutes', { valueAsNumber: true, required: true })}
          />
          <Input placeholder={t('placeholder.price')} {...register('price', { required: true })} />
        </div>
        <div className="flex gap-2">
          <Button className="flex-1" disabled={pending} type="submit">
            {t('common.save')}
          </Button>
          <Button
            variant="secondary"
            className="flex-1"
            disabled={pending || !procedure.is_active}
            onClick={onRemove}
            type="button"
          >
            {t('admin.procedures.remove')}
          </Button>
        </div>
      </form>
    </Card>
  )
}
