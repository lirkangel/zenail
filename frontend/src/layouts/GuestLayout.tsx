import { Link, Outlet } from 'react-router-dom'
import { useT } from '../state/useT'

export function GuestLayout() {
  const t = useT()

  return (
    <div className="min-h-full bg-gradient-to-b from-studio-cream/90 via-white/60 to-fuchsia-50/90">
      <div className="border-b border-rose-100/80 bg-white/85 shadow-sm shadow-rose-100/40 backdrop-blur-md">
        <div className="mx-auto flex max-w-lg items-center justify-between px-4 py-3">
          <Link
            className="text-sm font-semibold bg-gradient-to-r from-rose-700 via-pink-600 to-fuchsia-600 bg-clip-text text-transparent"
            to="/book/branch"
          >
            {t('guest.layout.brand')}
          </Link>
          <Link className="text-xs font-medium text-rose-700 hover:text-rose-900" to="/staff/login">
            {t('guest.layout.staffLogin')}
          </Link>
        </div>
      </div>
      <Outlet />
    </div>
  )
}

