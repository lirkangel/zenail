import type { HTMLAttributes } from 'react'

export function Card({ className = '', ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...props}
      className={[
        'rounded-2xl border border-rose-100/90 bg-white/90 p-4 shadow-lg shadow-rose-100/40 backdrop-blur-sm',
        className,
      ].join(' ')}
    />
  )
}

