import { type ReactNode, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { apiFetch } from '../../api/client'
import type {
  CustomerDetail,
  CustomerPreferenceDefinition,
  CustomerTagDefinition,
} from '../../api/types'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { Input } from '../../components/Input'
import { Page } from '../../components/Page'
import { useAuth } from '../../state/useAuth'
import { appointmentStatusLabel, useT } from '../../state/useT'

export function CustomerDetailPage() {
  const t = useT()
  const { id } = useParams()
  const { me, token } = useAuth()
  const prefix = me?.role === 'admin' ? '/api/admin' : '/api/manager'
  const isAdmin = me?.role === 'admin'

  const customerQ = useQuery({
    queryKey: ['customerDetail', prefix, id],
    queryFn: () => apiFetch<CustomerDetail>(`${prefix}/customers/${id}`, { token: token ?? undefined }),
    enabled: Boolean(token && id && me && me.role !== 'master'),
  })
  const tagDefsQ = useQuery({
    queryKey: ['customerTagDefinitions', prefix],
    queryFn: () => apiFetch<CustomerTagDefinition[]>(`${prefix}/customer-tag-definitions`, { token: token ?? undefined }),
    enabled: Boolean(token && me && me.role !== 'master'),
  })
  const prefDefsQ = useQuery({
    queryKey: ['customerPreferenceDefinitions', prefix],
    queryFn: () =>
      apiFetch<CustomerPreferenceDefinition[]>(`${prefix}/customer-preference-definitions`, {
        token: token ?? undefined,
      }),
    enabled: Boolean(token && me && me.role !== 'master'),
  })

  return (
    <Page title={customerQ.data?.full_name ?? t('customers.detailTitle')} subtitle={t('customers.detailSubtitle')}>
      {customerQ.isLoading ? <div className="text-sm text-rose-800/80">{t('common.loading')}</div> : null}
      {customerQ.isError ? <div className="text-sm text-rose-700">{t('customers.error')}</div> : null}
      {customerQ.data ? (
        <CustomerEditor
          key={customerQ.data.id}
          customer={customerQ.data}
          isAdmin={Boolean(isAdmin)}
          prefix={prefix}
          prefDefs={prefDefsQ.data ?? []}
          tagDefs={tagDefsQ.data ?? []}
          token={token ?? undefined}
        />
      ) : null}
    </Page>
  )
}

function CustomerEditor({
  customer,
  tagDefs,
  prefDefs,
  prefix,
  token,
  isAdmin,
}: {
  customer: CustomerDetail
  tagDefs: CustomerTagDefinition[]
  prefDefs: CustomerPreferenceDefinition[]
  prefix: string
  token?: string
  isAdmin: boolean
}) {
  const t = useT()
  const qc = useQueryClient()
  const catalogPath = isAdmin ? '/staff/admin/customer-catalog' : '/staff/customer-catalog'

  const [fullName, setFullName] = useState(customer.full_name)
  const [phone, setPhone] = useState(customer.phone)
  const [email, setEmail] = useState(customer.email ?? '')
  const [notes, setNotes] = useState(customer.notes ?? '')
  const [selectedTagIds, setSelectedTagIds] = useState(customer.tags.map((tag) => tag.id))
  const [preferenceValues, setPreferenceValues] = useState<Record<number, string | boolean>>(
    Object.fromEntries(
      customer.preferences.map((preference) => [
        preference.definition_id,
        preference.value_type === 'boolean'
          ? Boolean(preference.value_bool)
          : preference.value_type === 'single_select'
            ? preference.value_option ?? ''
            : preference.value_text ?? '',
      ]),
    ),
  )
  const [mergeBanner, setMergeBanner] = useState<number | null>(null)

  const save = useMutation({
    mutationFn: () => {
      const preferencesPayload = prefDefs.flatMap<
        { definition_id: number; value_bool?: boolean; value_option?: string; value_text?: string }[]
      >((definition) => {
        const value = preferenceValues[definition.id]
        if (definition.value_type === 'boolean') {
          return value === true ? [{ definition_id: definition.id, value_bool: true }] : []
        }
        if (definition.value_type === 'single_select') {
          return typeof value === 'string' && value.trim()
            ? [{ definition_id: definition.id, value_option: value.trim() }]
            : []
        }
        return typeof value === 'string' && value.trim()
          ? [{ definition_id: definition.id, value_text: value.trim() }]
          : []
      })

      return apiFetch<CustomerDetail>(`${prefix}/customers/${customer.id}`, {
        method: 'PATCH',
        token,
        body: JSON.stringify({
          full_name: fullName.trim(),
          ...(isAdmin ? { phone: phone.trim() } : {}),
          email: email.trim() || null,
          notes: notes.trim() || null,
          tag_ids: selectedTagIds,
          preferences: preferencesPayload,
        }),
      })
    },
    onSuccess: async (data) => {
      setMergeBanner(data.merged_from_customer_id ?? null)
      await qc.invalidateQueries({ queryKey: ['customerDetail', prefix, String(customer.id)] })
      await qc.invalidateQueries({ queryKey: ['customers'] })
      await qc.invalidateQueries({ queryKey: ['managerAppointments'] })
    },
  })

  return (
    <div className="space-y-4">
      {mergeBanner ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {t('customers.mergeBanner', { id: mergeBanner })}
        </div>
      ) : null}

      <Card>
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="text-sm font-semibold text-rose-950">{t('customers.profile')}</div>
          <Link className="text-xs font-medium text-rose-700 hover:text-rose-900" to={catalogPath}>
            {t('customers.manageCatalog')}
          </Link>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t('common.name')}>
            <Input value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </Field>
          <Field label={t('common.email')}>
            <Input value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field label={t('common.phone')}>
            <Input disabled={!isAdmin} value={phone} onChange={(e) => setPhone(e.target.value)} />
          </Field>
          <Field label={t('customers.notes')}>
            <textarea
              className="min-h-24 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-rose-950 focus:outline-none focus:ring-2 focus:ring-rose-400/40"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </Field>
        </div>
        {!isAdmin ? <div className="mt-2 text-xs text-rose-900/60">{t('customers.phoneAdminOnly')}</div> : null}
        <Button className="mt-4 w-full" disabled={save.isPending} type="button" onClick={() => save.mutate()}>
          {save.isPending ? t('common.saving') : t('customers.saveProfile')}
        </Button>
      </Card>

      <Card>
        <div className="mb-3 text-sm font-semibold text-rose-950">{t('customers.tags')}</div>
        <div className="flex flex-wrap gap-2">
          {tagDefs.map((definition) => {
            const active = selectedTagIds.includes(definition.id)
            return (
              <button
                key={definition.id}
                type="button"
                className={[
                  'rounded-full border px-3 py-1.5 text-xs font-medium transition',
                  active
                    ? 'border-fuchsia-300 bg-fuchsia-50 text-fuchsia-800'
                    : 'border-rose-200 bg-white text-rose-900/70',
                ].join(' ')}
                onClick={() =>
                  setSelectedTagIds((current) =>
                    active ? current.filter((entry) => entry !== definition.id) : [...current, definition.id],
                  )
                }
              >
                {definition.name}
              </button>
            )
          })}
        </div>
      </Card>

      <Card>
        <div className="mb-3 text-sm font-semibold text-rose-950">{t('customers.preferences')}</div>
        <div className="space-y-3">
          {prefDefs.map((definition) => (
            <div key={definition.id} className="rounded-xl border border-rose-100 bg-rose-50/60 p-3">
              <div className="mb-2 text-xs font-medium text-rose-950">{definition.name}</div>
              {definition.value_type === 'boolean' ? (
                <label className="flex items-center gap-2 text-sm text-rose-900/80">
                  <input
                    checked={preferenceValues[definition.id] === true}
                    type="checkbox"
                    onChange={(e) =>
                      setPreferenceValues((current) => ({
                        ...current,
                        [definition.id]: e.target.checked,
                      }))
                    }
                  />
                  {t('customers.preferenceEnabled')}
                </label>
              ) : definition.value_type === 'single_select' ? (
                <select
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                  value={typeof preferenceValues[definition.id] === 'string' ? String(preferenceValues[definition.id]) : ''}
                  onChange={(e) =>
                    setPreferenceValues((current) => ({
                      ...current,
                      [definition.id]: e.target.value,
                    }))
                  }
                >
                  <option value="">{t('customers.preferenceUnset')}</option>
                  {(definition.options_json ?? []).map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              ) : (
                <Input
                  value={typeof preferenceValues[definition.id] === 'string' ? String(preferenceValues[definition.id]) : ''}
                  onChange={(e) =>
                    setPreferenceValues((current) => ({
                      ...current,
                      [definition.id]: e.target.value,
                    }))
                  }
                />
              )}
            </div>
          ))}
        </div>
      </Card>

      <div className="space-y-3">
        <div className="text-sm font-semibold text-rose-950">{t('customers.history')}</div>
        {customer.appointments.length === 0 ? (
          <div className="text-sm text-rose-900/70">{t('customers.noHistory')}</div>
        ) : null}
        {customer.appointments.map((appointment) => (
          <Card key={appointment.id}>
            <div className="flex items-baseline justify-between gap-3">
              <div className="text-sm font-semibold text-rose-950">{new Date(appointment.start_time).toLocaleString()}</div>
              <div className="text-xs font-medium text-rose-900/70">{appointmentStatusLabel(t, appointment.status)}</div>
            </div>
            <div className="mt-1 text-xs text-rose-900/70">{appointment.master_name ?? `#${appointment.master_id}`}</div>
            <div className="mt-1 text-xs text-rose-900/70">
              {appointment.procedures.join(', ') || t('common.procedureFallback', { id: appointment.id })}
            </div>
            <div className="mt-1 text-xs font-medium text-rose-950">{appointment.price}</div>
          </Card>
        ))}
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <div className="mb-1 text-[11px] font-medium text-rose-900/75">{label}</div>
      {children}
    </div>
  )
}
