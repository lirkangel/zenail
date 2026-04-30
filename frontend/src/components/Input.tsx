import type { InputHTMLAttributes } from 'react'

export function Input({
  className = '',
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={[
        'w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm',
        'focus:outline-none focus:ring-2 focus:ring-slate-900/20',
        className,
      ].join(' ')}
    />
  )
}

