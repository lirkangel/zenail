import type { HTMLAttributes } from 'react'

export function Card({ className = '', ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...props}
      className={[
        'rounded-2xl border border-slate-200 bg-white p-4 shadow-sm',
        className,
      ].join(' ')}
    />
  )
}

