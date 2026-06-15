import type { AppointmentCustomerSummary, CustomerPreference, CustomerTag } from '../api/types'

export function CustomerCrmSummary({
  customer,
  tags,
  preferences,
  compact = false,
}: {
  customer?: AppointmentCustomerSummary | null
  tags: CustomerTag[]
  preferences: CustomerPreference[]
  compact?: boolean
}) {
  if (!customer) return null

  const activePreferences = preferences
    .map((preference) => ({
      ...preference,
      display:
        preference.value_type === 'boolean'
          ? preference.value_bool
            ? preference.name
            : ''
          : preference.value_type === 'single_select'
            ? preference.value_option ?? ''
            : preference.value_text ?? '',
    }))
    .filter((preference) => preference.display)

  return (
    <div className={['rounded-xl border border-rose-100 bg-rose-50/70 p-3', compact ? 'mt-2' : ''].join(' ')}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-rose-950">{customer.full_name}</div>
          <div className="mt-1 text-xs text-rose-900/70">{customer.phone}</div>
          {customer.email ? <div className="mt-1 text-xs text-rose-900/60">{customer.email}</div> : null}
        </div>
        {tags.length ? (
          <div className="flex flex-wrap justify-end gap-1">
            {tags.map((tag) => (
              <span
                key={tag.id}
                className="rounded-full border border-fuchsia-200 bg-white px-2 py-1 text-[11px] font-medium text-fuchsia-700"
              >
                {tag.name}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      {activePreferences.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {activePreferences.map((preference) => (
            <span
              key={preference.definition_id}
              className="rounded-full border border-rose-200 bg-white px-2.5 py-1 text-[11px] text-rose-900/75"
            >
              <span className="font-medium text-rose-950">{preference.name}</span>
              {preference.value_type === 'boolean' ? null : <span>: {preference.display}</span>}
            </span>
          ))}
        </div>
      ) : null}

      {customer.notes ? (
        <div className="mt-3 border-t border-rose-100 pt-3 text-xs leading-5 text-rose-900/70">{customer.notes}</div>
      ) : null}
    </div>
  )
}
