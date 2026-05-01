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
  phone?: string | null
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
    mutationFn: (args: {
      id: number
      full_name?: string
      email?: string
      phone?: string | null
      role?: 'master' | 'manager' | 'admin'
      branch_id?: number | null
      is_active?: boolean
      password?: string
    }) =>
      apiFetch(`/api/admin/staff/${args.id}`, {
        method: 'PATCH',
        token: token ?? undefined,
        body: JSON.stringify({
          full_name: args.full_name,
          email: args.email,
          phone: args.phone,
          role: args.role,
          branch_id: args.branch_id,
          is_active: args.is_active,
          password: args.password,
        }),
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
            onSave={(body) => updateM.mutate({ id: s.id, ...body })}
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
  onSave: (body: {
    full_name: string
    email: string
    phone: string | null
    role: 'master' | 'manager' | 'admin'
    branch_id: number | null
    is_active: boolean
    password?: string
  }) => void
}) {
  const t = useT()
  const [isEditing, setIsEditing] = useState(false)
  const [fullName, setFullName] = useState(row.full_name)
  const [email, setEmail] = useState(row.email)
  const [phone, setPhone] = useState(row.phone ?? '')
  const [role, setRole] = useState<StaffRow['role']>(row.role)
  const [branchValue, setBranchValue] = useState(row.branch_id?.toString() ?? '')
  const [isActive, setIsActive] = useState(row.is_active)
  const [password, setPassword] = useState('')

  return (
    <Card className="transition hover:border-rose-200 hover:shadow-studio">
      <div className="flex items-baseline justify-between gap-3">
        <div className="text-sm font-semibold text-rose-950">{row.full_name}</div>
        <div className="text-xs font-medium text-rose-900/70">{t(`role.${row.role}`)}</div>
      </div>
      <div className="mt-1 text-xs text-rose-900/75">{row.email}</div>
      {row.phone ? <div className="mt-1 text-xs text-rose-900/65">{row.phone}</div> : null}
      <div className="mt-1 text-xs text-rose-900/65">
        {t('admin.staff.branchLine', { branch: branchName })}
      </div>
      <div className="mt-1 text-xs text-rose-900/65">
        {row.is_active ? t('admin.staff.active') : t('admin.staff.inactive')}
      </div>
      {!isEditing ? (
        <div className="mt-3">
          <Button type="button" variant="secondary" onClick={() => setIsEditing(true)}>
            {t('admin.staff.edit')}
          </Button>
        </div>
      ) : (
        <div className="mt-3 space-y-2">
          <Input value={fullName} onChange={(e) => setFullName(e.target.value)} />
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Input placeholder={t('placeholder.phone')} value={phone} onChange={(e) => setPhone(e.target.value)} />
          <div className="flex gap-2">
            <select
              className="w-full rounded-xl border border-rose-200/80 bg-white/90 px-3 py-2 text-sm text-rose-950 shadow-sm"
              value={role}
              onChange={(e) => setRole(e.target.value as StaffRow['role'])}
            >
              <option value="master">{t('role.master')}</option>
              <option value="manager">{t('role.manager')}</option>
              <option value="admin">{t('role.admin')}</option>
            </select>
            <select
              className="w-full rounded-xl border border-rose-200/80 bg-white/90 px-3 py-2 text-sm text-rose-950 shadow-sm"
              value={branchValue}
              onChange={(e) => setBranchValue(e.target.value)}
            >
              <option value="">{t('admin.staff.noBranch')}</option>
              {branches.map((branch) => (
                <option key={branch.id} value={branch.id.toString()}>
                  {branch.name}
                </option>
              ))}
            </select>
          </div>
          <Input
            placeholder={t('admin.staff.passwordOptional')}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <label className="flex items-center gap-2 text-xs text-rose-900/75">
            <input checked={isActive} type="checkbox" onChange={(e) => setIsActive(e.target.checked)} />
            <span>{t('admin.staff.activeToggle')}</span>
          </label>
          <div className="flex gap-2">
            <Button
              type="button"
              disabled={pending}
              onClick={() => {
                onSave({
                  full_name: fullName.trim(),
                  email: email.trim(),
                  phone: phone.trim() || null,
                  role,
                  branch_id: branchValue.trim() ? Number(branchValue.trim()) : null,
                  is_active: isActive,
                  ...(password.trim() ? { password: password.trim() } : {}),
                })
                setIsEditing(false)
                setPassword('')
              }}
            >
              {pending ? t('common.saving') : t('common.save')}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setIsEditing(false)
                setFullName(row.full_name)
                setEmail(row.email)
                setPhone(row.phone ?? '')
                setRole(row.role)
                setBranchValue(row.branch_id?.toString() ?? '')
                setIsActive(row.is_active)
                setPassword('')
              }}
            >
              {t('common.cancel')}
            </Button>
          </div>
        </div>
      )}
    </Card>
  )
}
