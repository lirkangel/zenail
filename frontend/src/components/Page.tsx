import type { ReactNode } from 'react'

export function Page({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: ReactNode
}) {
  return (
    <div className="mx-auto w-full max-w-lg px-4 py-5">
      <div className="mb-4">
        <h1 className="bg-gradient-to-r from-rose-700 via-pink-600 to-fuchsia-600 bg-clip-text text-xl font-semibold tracking-tight text-transparent">
          {title}
        </h1>
        {subtitle ? <p className="mt-1 text-sm text-rose-900/70">{subtitle}</p> : null}
      </div>
      {children}
    </div>
  )
}

