import { useForm } from 'react-hook-form'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Input } from '../../../components/Input'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/auth'

type StaffRow = {
  id: number
  full_name: string
  email: string
  role: 'master' | 'manager' | 'admin'
  branch_id: number | null
  is_active: boolean
}

export function AdminStaffPage() {
  const { token } = useAuth()
  const qc = useQueryClient()
  const q = useQuery({
    queryKey: ['adminStaff'],
    queryFn: () => apiFetch<StaffRow[]>('/api/admin/staff', { token: token ?? undefined }),
  })

  const createM = useMutation({
    mutationFn: (body: unknown) =>
      apiFetch('/api/admin/staff', {
        method: 'POST',
        token: token ?? undefined,
        body: JSON.stringify(body),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['adminStaff'] })
    },
  })

  const { register, handleSubmit, reset } = useForm<{
    full_name: string
    email: string
    role: 'master' | 'manager' | 'admin'
    branch_id?: string
    password: string
  }>({
    defaultValues: { full_name: '', email: '', role: 'master', branch_id: '', password: '' },
  })

  return (
    <Page title="Staff" subtitle="Manage staff accounts and roles.">
      <Card className="mb-3">
        <form
          className="space-y-2"
          onSubmit={handleSubmit(async (v) => {
            await createM.mutateAsync({
              full_name: v.full_name,
              email: v.email,
              role: v.role,
              branch_id: v.branch_id?.trim() ? Number(v.branch_id.trim()) : null,
              password: v.password,
              is_active: true,
            })
            reset()
          })}
        >
          <div className="text-sm font-semibold">Add staff</div>
          <Input placeholder="Full name" {...register('full_name', { required: true })} />
          <Input placeholder="Email" type="email" {...register('email', { required: true })} />
          <div className="flex gap-2">
            <select
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
              {...register('role', { required: true })}
            >
              <option value="master">master</option>
              <option value="manager">manager</option>
              <option value="admin">admin</option>
            </select>
            <Input placeholder="Branch id (optional)" {...register('branch_id')} />
          </div>
          <Input placeholder="Password" type="password" {...register('password', { required: true })} />
          <Button className="w-full" disabled={createM.isPending} type="submit">
            {createM.isPending ? 'Saving…' : 'Create staff'}
          </Button>
        </form>
      </Card>

      <div className="space-y-3">
        {(q.data ?? []).map((s) => (
          <Card key={s.id}>
            <div className="flex items-baseline justify-between gap-3">
              <div className="text-sm font-semibold">{s.full_name}</div>
              <div className="text-xs text-slate-600">{s.role}</div>
            </div>
            <div className="mt-1 text-xs text-slate-600">{s.email}</div>
          </Card>
        ))}
      </div>
    </Page>
  )
}

