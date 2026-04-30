import { createContext } from 'react'

type Vars = Record<string, string | number>

export type TFn = (key: string, vars?: Vars) => string

export const I18nCtx = createContext<TFn | null>(null)

