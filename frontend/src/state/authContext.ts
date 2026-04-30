import { createContext } from 'react'
import type { Me } from '../api/types'

export type AuthState = {
  token: string | null
  me: Me | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refreshMe: () => Promise<void>
}

export const AuthCtx = createContext<AuthState | null>(null)

