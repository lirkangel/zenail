import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Input } from '../../../components/Input'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/useAuth'
import { useT } from '../../../state/useT'

type StaffRow = {
  id: number
  full_name: string
  email: string
  role: 'master' | 'manager' | 'admin'
  branch_id: number | null
  is_active: boolean
}

type BranchRow = {
  id: number
  name: string
}

export function AdminStaffPage() {
  const t = useT()
  const { token } = useAuth()
  const qc = useQueryClient()
  const q = useQuery({
    queryKey: ['adminStaff'],
    queryFn: () => apiFetch<StaffRow[]>('/api/admin/staff', { token: token ?? undefined }),
  })
  const branchesQ = useQuery({
    queryKey: ['adminBranchesForStaff'],
    queryFn: () => apiFetch<BranchRow[]>('/api/admin/branches', { token: token ?? undefined }),
  })
  const branchNameById = new Map((branchesQ.data ?? []).map((branch) => [branch.id, branch.name]))

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
  const updateM = useMutation({
    mutationFn: (args: { id: number; branch_id: number | null }) =>
      apiFetch(`/api/admin/staff/${args.id}`, {
        method: 'PATCH',
        token: token ?? undefined,
        body: JSON.stringify({ branch_id: args.branch_id }),
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
    <Page title={t('admin.staff.title')} subtitle={t('admin.staff.subtitle')}>
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
          <div className="text-sm font-semibold text-rose-950">{t('admin.staff.add')}</div>
          <Input placeholder={t('placeholder.fullName')} {...register('full_name', { required: true })} />
          <Input placeholder={t('placeholder.email')} type="email" {...register('email', { required: true })} />
          <div className="flex gap-2">
            <select
              className="w-full rounded-xl border border-rose-200/80 bg-white/90 px-3 py-2 text-sm text-rose-950 shadow-sm"
              {...register('role', { required: true })}
            >
              <option value="master">{t('role.master')}</option>
              <option value="manager">{t('role.manager')}</option>
              <option value="admin">{t('role.admin')}</option>
            </select>
            <select
              className="w-full rounded-xl border border-rose-200/80 bg-white/90 px-3 py-2 text-sm text-rose-950 shadow-sm"
              {...register('branch_id')}
            >
              <option value="">{t('admin.staff.noBranch')}</option>
              {(branchesQ.data ?? []).map((branch) => (
                <option key={branch.id} value={branch.id.toString()}>
                  {branch.name}
                </option>
              ))}
            </select>
          </div>
          <Input placeholder={t('placeholder.password')} type="password" {...register('password', { required: true })} />
          <Button className="w-full" disabled={createM.isPending} type="submit">
            {createM.isPending ? t('common.saving') : t('admin.staff.create')}
          </Button>
        </form>
      </Card>

      <div className="space-y-3">
        {(q.data ?? []).map((s) => (
          <StaffRowCard
            key={s.id}
            row={s}
            branchName={s.branch_id ? (branchNameById.get(s.branch_id) ?? `#${s.branch_id}`) : t('admin.staff.noBranch')}
            branches={branchesQ.data ?? []}
            pending={updateM.isPending}
            onSave={(branchId) => updateM.mutate({ id: s.id, branch_id: branchId })}
          />
        ))}
      </div>
    </Page>
  )
}

function StaffRowCard({
  row,
  branchName,
  branches,
  pending,
  onSave,
}: {
  row: StaffRow
  branchName: string
  branches: BranchRow[]
  pending: boolean
  onSave: (branchId: number | null) => void
}) {
  const t = useT()
  const [value, setValue] = useState(row.branch_id?.toString() ?? '')

  return (
    <Card className="transition hover:border-rose-200 hover:shadow-studio">
      <div className="flex items-baseline justify-between gap-3">
        <div className="text-sm font-semibold text-rose-950">{row.full_name}</div>
        <div className="text-xs font-medium text-rose-900/70">{t(`role.${row.role}`)}</div>
      </div>
      <div className="mt-1 text-xs text-rose-900/75">{row.email}</div>
      <div className="mt-1 text-xs text-rose-900/65">
        {t('admin.staff.branchLine', { branch: branchName })}
      </div>
      <div className="mt-3 flex gap-2">
        <select
          className="w-full rounded-xl border border-rose-200/80 bg-white/90 px-3 py-2 text-sm text-rose-950 shadow-sm"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        >
          <option value="">{t('admin.staff.noBranch')}</option>
          {branches.map((branch) => (
            <option key={branch.id} value={branch.id.toString()}>
              {branch.name}
            </option>
          ))}
        </select>
        <Button
          type="button"
          disabled={pending}
          onClick={() => onSave(value.trim() ? Number(value.trim()) : null)}
        >
          {pending ? t('common.saving') : t('common.save')}
        </Button>
      </div>
    </Card>
  )
}
