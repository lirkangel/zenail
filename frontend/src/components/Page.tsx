import type { ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useT } from '../state/useT'

export function Page({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: ReactNode
}) {
  const t = useT()
  const loc = useLocation()
  const nav = useNavigate()
  const canGoBack = loc.pathname.startsWith('/book') && loc.pathname !== '/book/branch'

  return (
    <div className="mx-auto w-full max-w-lg px-4 py-5">
      <div className="mb-4">
        <div
          className={[
            'flex w-full items-baseline',
            canGoBack ? 'justify-between' : 'justify-start',
          ].join(' ')}
        >
          {canGoBack ? (
            <button
              className="shrink-0 text-xs font-medium text-rose-700 hover:text-rose-900"
              type="button"
              onClick={() => nav(-1)}
            >
              {t('common.back')}
            </button>
          ) : null}
          <h1 className="min-w-0 bg-gradient-to-r from-rose-700 via-pink-600 to-fuchsia-600 bg-clip-text text-xl font-semibold tracking-tight text-transparent">
            {title}
          </h1>
        </div>
        {subtitle ? <p className="mt-1 text-sm text-rose-900/70">{subtitle}</p> : null}
      </div>
      {children}
    </div>
  )
}

