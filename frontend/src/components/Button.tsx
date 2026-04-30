import type { ButtonHTMLAttributes } from 'react'

export function Button({
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={[
        'inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-medium',
        'bg-slate-900 text-white hover:bg-slate-800 active:bg-slate-950',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className,
      ].join(' ')}
    />
  )
}

