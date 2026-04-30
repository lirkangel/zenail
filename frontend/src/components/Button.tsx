import type { ButtonHTMLAttributes } from 'react'

const variants = {
  primary: 'bg-slate-900 text-white hover:bg-slate-800 active:bg-slate-950',
  secondary: 'border border-slate-200 bg-white text-slate-900 hover:bg-slate-50',
  danger: 'bg-rose-600 text-white hover:bg-rose-700 active:bg-rose-800',
}

export function Button({
  className = '',
  variant = 'primary',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof variants }) {
  return (
    <button
      {...props}
      className={[
        'inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-medium',
        variants[variant],
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className,
      ].join(' ')}
    />
  )
}
