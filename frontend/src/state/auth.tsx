import React, { useCallback, useEffect, useEffectEvent, useMemo, useState } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { apiFetch } from '../api/client'
import type { LoginResponse, Me, StaffRole } from '../api/types'
import { AuthCtx, type AuthState } from './authContext'
import { useAuth } from './useAuth'

const TOKEN_KEY = 'zenail.token'
const ME_KEY = 'zenail.me'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isReady, setIsReady] = useState(false)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [me, setMe] = useState<Me | null>(() => {
    const raw = localStorage.getItem(ME_KEY)
    return raw ? (JSON.parse(raw) as Me) : null
  })

  const refreshMeWithToken = useCallback(async (nextToken: string | null) => {
    if (!nextToken) {
      setMe(null)
      localStorage.removeItem(ME_KEY)
      return
    }
    const next = await apiFetch<Me>('/api/me', { token: nextToken })
    setMe(next)
    localStorage.setItem(ME_KEY, JSON.stringify(next))
  }, [])

  const clearSession = useCallback(() => {
    setToken(null)
    setMe(null)
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(ME_KEY)
  }, [])

  const bootstrapAuth = useEffectEvent(async () => {
    if (!token) {
      setIsReady(true)
      return
    }
    try {
      await refreshMeWithToken(token)
    } catch {
      clearSession()
    } finally {
      setIsReady(true)
    }
  })

  useEffect(() => {
    void bootstrapAuth()
  }, [bootstrapAuth, token])

  const refreshMe = useCallback(async () => refreshMeWithToken(token), [refreshMeWithToken, token])

  const login = useCallback(
    async (email: string, password: string) => {
      const resp = await apiFetch<LoginResponse>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      setToken(resp.access_token)
      localStorage.setItem(TOKEN_KEY, resp.access_token)
      await refreshMeWithToken(resp.access_token)
    },
    [refreshMeWithToken],
  )

  const logout = clearSession

  const value = useMemo<AuthState>(
    () => ({ isReady, token, me, login, logout, refreshMe }),
    [isReady, token, me, login, logout, refreshMe],
  )

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>
}

export function RequireStaff({ children }: { children: React.ReactNode }) {
  const { isReady, token } = useAuth()
  const loc = useLocation()
  if (!isReady) return null
  if (!token) return <Navigate to="/staff/login" replace state={{ from: loc.pathname }} />
  return <>{children}</>
}

export function RequireRole({ roles }: { roles: StaffRole[] }) {
  const { isReady, me } = useAuth()
  if (!isReady || !me) return null
  if (!roles.includes(me.role)) return <Navigate to="/staff" replace />
  return <Outlet />
}
