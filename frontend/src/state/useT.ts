import { useContext } from 'react'
import { I18nCtx, type TFn } from './i18nContext'

export function useT(): TFn {
  const ctx = useContext(I18nCtx)
  if (!ctx) throw new Error('I18nProvider missing')
  return ctx
}

export function appointmentStatusLabel(t: TFn, status: string): string {
  if (status === 'scheduled') return t('status.scheduled')
  if (status === 'completed') return t('status.completed')
  if (status === 'canceled') return t('status.canceled')
  return status
}

