import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { apiFetch } from '../../api/client'
import type { Procedure } from '../../api/types'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { Page } from '../../components/Page'
import { useT } from '../../state/i18n'

export function BookProcedurePage() {
  const t = useT()
  const [sp] = useSearchParams()
  const branchId = sp.get('branch')
  const masterId = sp.get('master')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const q = useQuery({
    queryKey: ['procedures', masterId],
    enabled: !!masterId,
    queryFn: () => apiFetch<Procedure[]>(`/api/masters/${masterId}/procedures`),
  })
  const selected = useMemo(
    () => (q.data ?? []).filter((p) => selectedIds.includes(p.id)),
    [q.data, selectedIds],
  )
  const totalPrice = selected.reduce((sum, p) => sum + Number(p.price), 0)
  const totalDuration = selected.reduce((sum, p) => sum + p.duration_minutes, 0)

  return (
    <Page title={t('guest.procedure.title')} subtitle={t('guest.procedure.subtitle')}>
      {!branchId || !masterId ? (
        <div className="text-sm text-rose-700">{t('guest.procedure.missing')}</div>
      ) : null}
      {q.isLoading ? <div className="text-sm text-rose-800/80">{t('guest.procedure.loading')}</div> : null}
      {q.isError ? <div className="text-sm text-rose-700">{t('guest.procedure.error')}</div> : null}
      <div className="space-y-3">
        {(q.data ?? []).map((p) => (
          <button
            key={p.id}
            type="button"
            className="block w-full text-left"
            onClick={() =>
              setSelectedIds((current) =>
                current.includes(p.id) ? current.filter((id) => id !== p.id) : [...current, p.id],
              )
            }
          >
            <Card
              className={[
                'transition hover:border-rose-300 hover:shadow-studio',
                selectedIds.includes(p.id)
                  ? 'border-rose-400 ring-2 ring-rose-300/60 shadow-studio'
                  : '',
              ].join(' ')}
            >
              <div className="mb-2 flex items-center justify-between gap-3">
                <span className="rounded-full bg-rose-100 px-2 py-1 text-[11px] font-medium text-rose-800">
                  {p.category ?? t('guest.procedure.categoryDefault')}
                </span>
                <span className="text-xs text-rose-700/80">
                  {selectedIds.includes(p.id) ? t('guest.procedure.selected') : t('guest.procedure.tapToSelect')}
                </span>
              </div>
              <div className="flex items-baseline justify-between gap-3">
                <div className="text-sm font-semibold text-rose-950">{p.name}</div>
                <div className="text-xs font-medium text-rose-800">${p.price}</div>
              </div>
              <div className="mt-1 text-xs text-rose-900/70">
                {p.duration_minutes} {t('common.minutes')}
              </div>
              {p.description ? (
                <div className="mt-2 text-xs leading-5 text-rose-900/65">{p.description}</div>
              ) : null}
            </Card>
          </button>
        ))}
      </div>

      <div className="sticky bottom-0 mt-4 border-t border-rose-100/80 bg-gradient-to-t from-studio-cream/95 via-white/90 to-transparent py-3 backdrop-blur-sm">
        <Card>
          <div className="mb-3 flex items-center justify-between text-sm">
            <div>
              <div className="font-semibold text-rose-950">
                {t('guest.procedure.selectedCount', { count: selected.length })}
              </div>
              <div className="text-xs text-rose-900/70">
                {t('guest.procedure.totalDuration', { minutes: totalDuration })}
              </div>
            </div>
            <div className="font-semibold text-rose-800">${totalPrice.toFixed(2)}</div>
          </div>
          <Link
            className={selected.length ? '' : 'pointer-events-none'}
            to={`/book/time?branch=${branchId}&master=${masterId}&procedures=${selectedIds.join(',')}`}
          >
            <Button className="w-full" disabled={!selected.length} type="button">
              {t('guest.procedure.chooseTime')}
            </Button>
          </Link>
        </Card>
      </div>
    </Page>
  )
}
