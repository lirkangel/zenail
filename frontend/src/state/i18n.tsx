import { createContext, useContext, useMemo } from 'react'
import { VI } from '../i18n/messages'

type Vars = Record<string, string | number>

function interpolate(template: string, vars?: Vars): string {
  if (!vars) return template
  return template.replace(/\{(\w+)\}/g, (_, key: string) => String(vars[key] ?? `{${key}}`))
}

type TFn = (key: string, vars?: Vars) => string

const I18nCtx = createContext<TFn | null>(null)

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const t = useMemo<TFn>(() => {
    return (key: string, vars?: Vars) => {
      const template = VI[key] ?? key
      return interpolate(template, vars)
    }
  }, [])

  return <I18nCtx.Provider value={t}>{children}</I18nCtx.Provider>
}

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
