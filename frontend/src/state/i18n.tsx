import { useMemo, useState } from 'react'
import { EN, VI } from '../i18n/messages'
import { I18nCtx, type Locale, type TFn } from './i18nContext'

type Vars = Record<string, string | number>

function interpolate(template: string, vars?: Vars): string {
  if (!vars) return template
  return template.replace(/\{(\w+)\}/g, (_, key: string) => String(vars[key] ?? `{${key}}`))
}

const LOCALE_KEY = 'zenail.locale'

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<Locale>(() => {
    const raw = localStorage.getItem(LOCALE_KEY)
    return raw === 'en' ? 'en' : 'vi'
  })

  const t = useMemo<TFn>(() => {
    return (key: string, vars?: Vars) => {
      const messages = locale === 'en' ? EN : VI
      const template = messages[key] ?? key
      return interpolate(template, vars)
    }
  }, [locale])

  return (
    <I18nCtx.Provider
      value={{
        locale,
        setLocale: (nextLocale) => {
          setLocale(nextLocale)
          localStorage.setItem(LOCALE_KEY, nextLocale)
        },
        t,
      }}
    >
      {children}
    </I18nCtx.Provider>
  )
}
