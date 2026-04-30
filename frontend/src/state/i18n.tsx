import { useMemo } from 'react'
import { VI } from '../i18n/messages'
import { I18nCtx, type TFn } from './i18nContext'

type Vars = Record<string, string | number>

function interpolate(template: string, vars?: Vars): string {
  if (!vars) return template
  return template.replace(/\{(\w+)\}/g, (_, key: string) => String(vars[key] ?? `{${key}}`))
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const t = useMemo<TFn>(() => {
    return (key: string, vars?: Vars) => {
      const template = VI[key] ?? key
      return interpolate(template, vars)
    }
  }, [])

  return <I18nCtx.Provider value={t}>{children}</I18nCtx.Provider>
}
