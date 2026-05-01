import { createContext } from 'react'

type Vars = Record<string, string | number>
export type Locale = 'vi' | 'en'

export type TFn = (key: string, vars?: Vars) => string

export type I18nState = {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: TFn
}

export const I18nCtx = createContext<I18nState | null>(null)
