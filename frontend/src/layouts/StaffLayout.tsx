import { Link, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../state/useAuth'
import { useI18n, useT } from '../state/useT'

function NavLink({ to, label }: { to: string; label: string }) {
  const loc = useLocation()
  const active = loc.pathname === to
  return (
    <Link
      to={to}
      className={[
        'flex min-w-0 flex-1 flex-col items-center justify-center px-1 py-2 text-[11px]',
        active ? 'text-rose-800' : 'text-rose-500/80',
      ].join(' ')}
    >
      <span className={['truncate', active ? 'font-semibold' : ''].join(' ')}>{label}</span>
    </Link>
  )
}

export function StaffLayout() {
  const t = useT()
  const { locale, setLocale } = useI18n()
  const { me, logout } = useAuth()
  const role = me?.role

  const tabs =
    role === 'master'
      ? [
          { to: '/staff/schedule', label: t('staff.tab.schedule') },
          { to: '/staff', label: t('staff.tab.home') },
        ]
      : role === 'manager'
        ? [
            { to: '/staff/dashboard', label: t('staff.tab.today') },
            { to: '/staff/appointments', label: t('staff.tab.clients') },
            { to: '/staff/masters', label: t('staff.tab.masters') },
            { to: '/staff/requests', label: t('staff.tab.requests') },
            { to: '/staff/revenue', label: t('staff.tab.revenue') },
          ]
        : [
            { to: '/staff/admin/branches', label: t('staff.tab.branches') },
            { to: '/staff/admin/staff', label: t('staff.tab.staff') },
            { to: '/staff/admin/procedures', label: t('staff.tab.procedures') },
            { to: '/staff/admin/revenue', label: t('staff.tab.revenue') },
          ]

  return (
    <div className="min-h-full bg-gradient-to-b from-studio-cream/90 via-white/60 to-fuchsia-50/90 pb-16">
      <div className="border-b border-rose-100/80 bg-white/85 shadow-sm shadow-rose-100/40 backdrop-blur-md">
        <div className="mx-auto flex max-w-lg items-center justify-between px-4 py-3">
          <div className="text-sm font-semibold bg-gradient-to-r from-rose-700 to-fuchsia-600 bg-clip-text text-transparent">
            {t('staff.layout.title')}
          </div>
          <div className="flex items-center gap-3">
            <button
              className="text-[11px] font-semibold uppercase tracking-[0.16em] text-rose-700 hover:text-rose-900"
              type="button"
              onClick={() => setLocale(locale === 'vi' ? 'en' : 'vi')}
            >
              {locale === 'vi' ? 'EN' : 'VI'}
            </button>
            <button
              onClick={logout}
              className="text-xs font-medium text-rose-700 hover:text-rose-900"
              type="button"
            >
              {t('staff.layout.logout')}
            </button>
          </div>
        </div>
      </div>

      <Outlet />

      <div className="fixed bottom-0 left-0 right-0 border-t border-rose-100/90 bg-white/95 shadow-[0_-8px_30px_-12px_rgba(251,113,133,0.35)] backdrop-blur-md">
        <div className="mx-auto flex max-w-lg">
          {tabs.map((tab) => (
            <NavLink key={tab.to} to={tab.to} label={tab.label} />
          ))}
        </div>
      </div>
    </div>
  )
}
