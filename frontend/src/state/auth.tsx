import React, { createContext, useContext, useMemo, useState } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { apiFetch } from '../api/client'
import type { LoginResponse, Me, StaffRole } from '../api/types'

type AuthState = {
  token: string | null
  me: Me | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refreshMe: () => Promise<void>
}

const AuthCtx = createContext<AuthState | null>(null)

const TOKEN_KEY = 'zenail.token'
const ME_KEY = 'zenail.me'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [me, setMe] = useState<Me | null>(() => {
    const raw = localStorage.getItem(ME_KEY)
    return raw ? (JSON.parse(raw) as Me) : null
  })

  async function refreshMe() {
    return refreshMeWithToken(token)
  }

  async function refreshMeWithToken(nextToken: string | null) {
    if (!nextToken) {
      setMe(null)
      localStorage.removeItem(ME_KEY)
      return
    }
    const next = await apiFetch<Me>('/api/me', { token: nextToken })
    setMe(next)
    localStorage.setItem(ME_KEY, JSON.stringify(next))
  }

  async function login(email: string, password: string) {
    const resp = await apiFetch<LoginResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    setToken(resp.access_token)
    localStorage.setItem(TOKEN_KEY, resp.access_token)
    await refreshMeWithToken(resp.access_token)
  }

  function logout() {
    setToken(null)
    setMe(null)
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(ME_KEY)
  }

  const value = useMemo<AuthState>(
    () => ({ token, me, login, logout, refreshMe }),
    [token, me],
  )

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthCtx)
  if (!ctx) throw new Error('AuthProvider missing')
  return ctx
}

export function RequireStaff({ children }: { children: React.ReactNode }) {
  const { token } = useAuth()
  const loc = useLocation()
  if (!token) return <Navigate to="/staff/login" replace state={{ from: loc.pathname }} />
  return <>{children}</>
}

export function RequireRole({ roles }: { roles: StaffRole[] }) {
  const { me } = useAuth()
  if (!me) return <Outlet />
  if (!roles.includes(me.role)) return <Navigate to="/staff" replace />
  return <Outlet />
}

