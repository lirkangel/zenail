import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { apiFetch } from '../../api/client'
import type {
  Branch,
  CustomerPreferenceDefinition,
  CustomerTagDefinition,
} from '../../api/types'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { Input } from '../../components/Input'
import { Page } from '../../components/Page'
import { useAuth } from '../../state/useAuth'
import { useT } from '../../state/useT'

type CatalogMode = 'tags' | 'preferences'

export function CustomerCatalogPage() {
  const t = useT()
  const { me, token } = useAuth()
  const qc = useQueryClient()
  const [mode, setMode] = useState<CatalogMode>('tags')
  const prefix = me?.role === 'admin' ? '/api/admin' : '/api/manager'
  const isAdmin = me?.role === 'admin'

  const tagsQ = useQuery({
    queryKey: ['customerTagDefinitions', prefix],
    queryFn: () => apiFetch<CustomerTagDefinition[]>(`${prefix}/customer-tag-definitions`, { token: token ?? undefined }),
    enabled: Boolean(token && me && me.role !== 'master'),
  })
  const prefsQ = useQuery({
    queryKey: ['customerPreferenceDefinitions', prefix],
    queryFn: () =>
      apiFetch<CustomerPreferenceDefinition[]>(`${prefix}/customer-preference-definitions`, {
        token: token ?? undefined,
      }),
    enabled: Boolean(token && me && me.role !== 'master'),
  })
  const branchesQ = useQuery({
    queryKey: ['adminBranchesForCatalog'],
    queryFn: () => apiFetch<Branch[]>('/api/admin/branches', { token: token ?? undefined }),
    enabled: Boolean(token && isAdmin),
  })

  const refresh = async () => {
    await qc.invalidateQueries({ queryKey: ['customerTagDefinitions', prefix] })
    await qc.invalidateQueries({ queryKey: ['customerPreferenceDefinitions', prefix] })
    await qc.invalidateQueries({ queryKey: ['customerDetail'] })
    await qc.invalidateQueries({ queryKey: ['customers'] })
  }

  return (
    <Page title={t('customerCatalog.title')} subtitle={t('customerCatalog.subtitle')}>
      <div className="mb-4 grid grid-cols-2 gap-2">
        <button
          type="button"
          className={[
            'rounded-xl border px-3 py-2 text-sm font-medium',
            mode === 'tags'
              ? 'border-rose-300 bg-white text-rose-950 shadow-sm'
              : 'border-rose-100 bg-white/70 text-rose-900/60',
          ].join(' ')}
          onClick={() => setMode('tags')}
        >
          {t('customerCatalog.tags')}
        </button>
        <button
          type="button"
          className={[
            'rounded-xl border px-3 py-2 text-sm font-medium',
            mode === 'preferences'
              ? 'border-rose-300 bg-white text-rose-950 shadow-sm'
              : 'border-rose-100 bg-white/70 text-rose-900/60',
          ].join(' ')}
          onClick={() => setMode('preferences')}
        >
          {t('customerCatalog.preferences')}
        </button>
      </div>

      {mode === 'tags' ? (
        <TagCatalog
          isAdmin={Boolean(isAdmin)}
          branches={branchesQ.data ?? []}
          definitions={tagsQ.data ?? []}
          isLoading={tagsQ.isLoading}
          token={token ?? undefined}
          prefix={prefix}
          onSaved={refresh}
        />
      ) : (
        <PreferenceCatalog
          isAdmin={Boolean(isAdmin)}
          branches={branchesQ.data ?? []}
          definitions={prefsQ.data ?? []}
          isLoading={prefsQ.isLoading}
          token={token ?? undefined}
          prefix={prefix}
          onSaved={refresh}
        />
      )}
    </Page>
  )
}

function TagCatalog({
  definitions,
  branches,
  isAdmin,
  isLoading,
  token,
  prefix,
  onSaved,
}: {
  definitions: CustomerTagDefinition[]
  branches: Branch[]
  isAdmin: boolean
  isLoading: boolean
  token?: string
  prefix: string
  onSaved: () => Promise<void>
}) {
  const t = useT()
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [scope, setScope] = useState<'global' | 'branch'>('global')
  const [branchId, setBranchId] = useState('')

  const create = useMutation({
    mutationFn: () =>
      apiFetch<CustomerTagDefinition>(`${prefix}/customer-tag-definitions`, {
        method: 'POST',
        token,
        body: JSON.stringify({
          name,
          slug,
          scope,
          branch_id: scope === 'branch' && branchId ? Number(branchId) : null,
        }),
      }),
    onSuccess: async () => {
      setName('')
      setSlug('')
      setBranchId('')
      setScope('global')
      await onSaved()
    },
  })

  return (
    <div className="space-y-4">
      <Card>
        <div className="mb-3 text-sm font-semibold text-rose-950">{t('customerCatalog.addTag')}</div>
        <div className="grid gap-2 sm:grid-cols-2">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder={t('customerCatalog.name')} />
          <Input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder={t('customerCatalog.slug')} />
        </div>
        {isAdmin ? (
          <div className="mt-2 grid gap-2 sm:grid-cols-[140px_1fr]">
            <select
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
              value={scope}
              onChange={(e) => setScope(e.target.value as 'global' | 'branch')}
            >
              <option value="global">{t('customerCatalog.global')}</option>
              <option value="branch">{t('customerCatalog.branchLocal')}</option>
            </select>
            {scope === 'branch' ? (
              <select
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                value={branchId}
                onChange={(e) => setBranchId(e.target.value)}
              >
                <option value="">{t('customerCatalog.selectBranch')}</option>
                {branches.map((branch) => (
                  <option key={branch.id} value={branch.id}>
                    {branch.name}
                  </option>
                ))}
              </select>
            ) : null}
          </div>
        ) : null}
        <Button
          className="mt-3 w-full"
          disabled={create.isPending || !name.trim() || !slug.trim() || (scope === 'branch' && isAdmin && !branchId)}
          type="button"
          onClick={() => create.mutate()}
        >
          {create.isPending ? t('common.saving') : t('customerCatalog.create')}
        </Button>
      </Card>

      {isLoading ? <div className="text-sm text-rose-800/80">{t('common.loading')}</div> : null}
      <div className="space-y-3">
        {definitions.map((definition) => (
          <TagDefinitionRow
            key={definition.id}
            definition={definition}
            branches={branches}
            isAdmin={isAdmin}
            token={token}
            prefix={prefix}
            onSaved={onSaved}
          />
        ))}
      </div>
    </div>
  )
}

function TagDefinitionRow({
  definition,
  branches,
  isAdmin,
  token,
  prefix,
  onSaved,
}: {
  definition: CustomerTagDefinition
  branches: Branch[]
  isAdmin: boolean
  token?: string
  prefix: string
  onSaved: () => Promise<void>
}) {
  const t = useT()
  const editable = isAdmin || definition.scope === 'branch'
  const [name, setName] = useState(definition.name)
  const [slug, setSlug] = useState(definition.slug)
  const [scope, setScope] = useState<'global' | 'branch'>(definition.scope)
  const [branchId, setBranchId] = useState(definition.branch_id ? String(definition.branch_id) : '')
  const [isActive, setIsActive] = useState(definition.is_active)

  const save = useMutation({
    mutationFn: () =>
      apiFetch<CustomerTagDefinition>(`${prefix}/customer-tag-definitions/${definition.id}`, {
        method: 'PATCH',
        token,
        body: JSON.stringify({
          name,
          slug,
          scope,
          branch_id: scope === 'branch' && branchId ? Number(branchId) : null,
          is_active: isActive,
        }),
      }),
    onSuccess: onSaved,
  })

  return (
    <div className="rounded-xl border border-rose-100 bg-white/85 p-3">
      <div className="grid gap-2 sm:grid-cols-2">
        <Input disabled={!editable} value={name} onChange={(e) => setName(e.target.value)} />
        <Input disabled={!editable} value={slug} onChange={(e) => setSlug(e.target.value)} />
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <select
          disabled={!isAdmin}
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm disabled:opacity-60"
          value={scope}
          onChange={(e) => setScope(e.target.value as 'global' | 'branch')}
        >
          <option value="global">{t('customerCatalog.global')}</option>
          <option value="branch">{t('customerCatalog.branchLocal')}</option>
        </select>
        {scope === 'branch' ? (
          <select
            disabled={!isAdmin}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm disabled:opacity-60"
            value={branchId}
            onChange={(e) => setBranchId(e.target.value)}
          >
            <option value="">{t('customerCatalog.selectBranch')}</option>
            {branches.map((branch) => (
              <option key={branch.id} value={branch.id}>
                {branch.name}
              </option>
            ))}
          </select>
        ) : null}
        <label className="flex items-center gap-2 text-xs text-rose-900/75">
          <input checked={isActive} onChange={(e) => setIsActive(e.target.checked)} type="checkbox" />
          {t('customerCatalog.active')}
        </label>
      </div>
      <Button className="mt-3 w-full" disabled={!editable || save.isPending} type="button" onClick={() => save.mutate()}>
        {save.isPending ? t('common.saving') : t('common.save')}
      </Button>
    </div>
  )
}

function PreferenceCatalog({
  definitions,
  branches,
  isAdmin,
  isLoading,
  token,
  prefix,
  onSaved,
}: {
  definitions: CustomerPreferenceDefinition[]
  branches: Branch[]
  isAdmin: boolean
  isLoading: boolean
  token?: string
  prefix: string
  onSaved: () => Promise<void>
}) {
  const t = useT()
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [scope, setScope] = useState<'global' | 'branch'>('global')
  const [branchId, setBranchId] = useState('')
  const [valueType, setValueType] = useState<'text' | 'boolean' | 'single_select'>('boolean')
  const [optionsText, setOptionsText] = useState('')

  const create = useMutation({
    mutationFn: () =>
      apiFetch<CustomerPreferenceDefinition>(`${prefix}/customer-preference-definitions`, {
        method: 'POST',
        token,
        body: JSON.stringify({
          name,
          slug,
          scope,
          branch_id: scope === 'branch' && branchId ? Number(branchId) : null,
          value_type: valueType,
          options_json:
            valueType === 'single_select'
              ? optionsText
                  .split(',')
                  .map((item) => item.trim())
                  .filter(Boolean)
              : null,
        }),
      }),
    onSuccess: async () => {
      setName('')
      setSlug('')
      setBranchId('')
      setScope('global')
      setValueType('boolean')
      setOptionsText('')
      await onSaved()
    },
  })

  return (
    <div className="space-y-4">
      <Card>
        <div className="mb-3 text-sm font-semibold text-rose-950">{t('customerCatalog.addPreference')}</div>
        <div className="grid gap-2 sm:grid-cols-2">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder={t('customerCatalog.name')} />
          <Input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder={t('customerCatalog.slug')} />
        </div>
        <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_1fr]">
          <select
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
            value={valueType}
            onChange={(e) => setValueType(e.target.value as 'text' | 'boolean' | 'single_select')}
          >
            <option value="boolean">{t('customerCatalog.boolean')}</option>
            <option value="text">{t('customerCatalog.text')}</option>
            <option value="single_select">{t('customerCatalog.singleSelect')}</option>
          </select>
          {valueType === 'single_select' ? (
            <Input
              value={optionsText}
              onChange={(e) => setOptionsText(e.target.value)}
              placeholder={t('customerCatalog.options')}
            />
          ) : null}
        </div>
        {isAdmin ? (
          <div className="mt-2 grid gap-2 sm:grid-cols-[140px_1fr]">
            <select
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
              value={scope}
              onChange={(e) => setScope(e.target.value as 'global' | 'branch')}
            >
              <option value="global">{t('customerCatalog.global')}</option>
              <option value="branch">{t('customerCatalog.branchLocal')}</option>
            </select>
            {scope === 'branch' ? (
              <select
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                value={branchId}
                onChange={(e) => setBranchId(e.target.value)}
              >
                <option value="">{t('customerCatalog.selectBranch')}</option>
                {branches.map((branch) => (
                  <option key={branch.id} value={branch.id}>
                    {branch.name}
                  </option>
                ))}
              </select>
            ) : null}
          </div>
        ) : null}
        <Button
          className="mt-3 w-full"
          disabled={create.isPending || !name.trim() || !slug.trim() || (scope === 'branch' && isAdmin && !branchId)}
          type="button"
          onClick={() => create.mutate()}
        >
          {create.isPending ? t('common.saving') : t('customerCatalog.create')}
        </Button>
      </Card>

      {isLoading ? <div className="text-sm text-rose-800/80">{t('common.loading')}</div> : null}
      <div className="space-y-3">
        {definitions.map((definition) => (
          <PreferenceDefinitionRow
            key={definition.id}
            definition={definition}
            branches={branches}
            isAdmin={isAdmin}
            token={token}
            prefix={prefix}
            onSaved={onSaved}
          />
        ))}
      </div>
    </div>
  )
}

function PreferenceDefinitionRow({
  definition,
  branches,
  isAdmin,
  token,
  prefix,
  onSaved,
}: {
  definition: CustomerPreferenceDefinition
  branches: Branch[]
  isAdmin: boolean
  token?: string
  prefix: string
  onSaved: () => Promise<void>
}) {
  const t = useT()
  const editable = isAdmin || definition.scope === 'branch'
  const [name, setName] = useState(definition.name)
  const [slug, setSlug] = useState(definition.slug)
  const [scope, setScope] = useState<'global' | 'branch'>(definition.scope)
  const [branchId, setBranchId] = useState(definition.branch_id ? String(definition.branch_id) : '')
  const [valueType, setValueType] = useState<'text' | 'boolean' | 'single_select'>(definition.value_type)
  const [optionsText, setOptionsText] = useState((definition.options_json ?? []).join(', '))
  const [isActive, setIsActive] = useState(definition.is_active)

  const save = useMutation({
    mutationFn: () =>
      apiFetch<CustomerPreferenceDefinition>(`${prefix}/customer-preference-definitions/${definition.id}`, {
        method: 'PATCH',
        token,
        body: JSON.stringify({
          name,
          slug,
          scope,
          branch_id: scope === 'branch' && branchId ? Number(branchId) : null,
          value_type: valueType,
          options_json:
            valueType === 'single_select'
              ? optionsText
                  .split(',')
                  .map((item) => item.trim())
                  .filter(Boolean)
              : null,
          is_active: isActive,
        }),
      }),
    onSuccess: onSaved,
  })

  return (
    <div className="rounded-xl border border-rose-100 bg-white/85 p-3">
      <div className="grid gap-2 sm:grid-cols-2">
        <Input disabled={!editable} value={name} onChange={(e) => setName(e.target.value)} />
        <Input disabled={!editable} value={slug} onChange={(e) => setSlug(e.target.value)} />
      </div>
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        <select
          disabled={!editable}
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm disabled:opacity-60"
          value={valueType}
          onChange={(e) => setValueType(e.target.value as 'text' | 'boolean' | 'single_select')}
        >
          <option value="boolean">{t('customerCatalog.boolean')}</option>
          <option value="text">{t('customerCatalog.text')}</option>
          <option value="single_select">{t('customerCatalog.singleSelect')}</option>
        </select>
        {valueType === 'single_select' ? (
          <Input
            disabled={!editable}
            value={optionsText}
            onChange={(e) => setOptionsText(e.target.value)}
            placeholder={t('customerCatalog.options')}
          />
        ) : null}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <select
          disabled={!isAdmin}
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm disabled:opacity-60"
          value={scope}
          onChange={(e) => setScope(e.target.value as 'global' | 'branch')}
        >
          <option value="global">{t('customerCatalog.global')}</option>
          <option value="branch">{t('customerCatalog.branchLocal')}</option>
        </select>
        {scope === 'branch' ? (
          <select
            disabled={!isAdmin}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm disabled:opacity-60"
            value={branchId}
            onChange={(e) => setBranchId(e.target.value)}
          >
            <option value="">{t('customerCatalog.selectBranch')}</option>
            {branches.map((branch) => (
              <option key={branch.id} value={branch.id}>
                {branch.name}
              </option>
            ))}
          </select>
        ) : null}
        <label className="flex items-center gap-2 text-xs text-rose-900/75">
          <input checked={isActive} onChange={(e) => setIsActive(e.target.checked)} type="checkbox" />
          {t('customerCatalog.active')}
        </label>
      </div>
      <Button className="mt-3 w-full" disabled={!editable || save.isPending} type="button" onClick={() => save.mutate()}>
        {save.isPending ? t('common.saving') : t('common.save')}
      </Button>
    </div>
  )
}
