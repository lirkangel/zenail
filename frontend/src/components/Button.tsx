import type { ButtonHTMLAttributes } from 'react'

const variants = {
  primary:
    'bg-gradient-to-r from-rose-500 via-pink-500 to-fuchsia-500 text-white shadow-md shadow-rose-300/40 hover:from-rose-600 hover:via-pink-600 hover:to-fuchsia-600 active:opacity-95',
  secondary:
    'border border-rose-200 bg-white/90 text-rose-950 shadow-sm hover:bg-rose-50 active:bg-rose-100/80',
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
