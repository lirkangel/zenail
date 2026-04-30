import { Link, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../state/auth'

function NavLink({ to, label }: { to: string; label: string }) {
  const loc = useLocation()
  const active = loc.pathname === to
  return (
    <Link
      to={to}
      className={[
        'flex min-w-0 flex-1 flex-col items-center justify-center px-1 py-2 text-[11px]',
        active ? 'text-slate-900' : 'text-slate-500',
      ].join(' ')}
    >
      <span className={['truncate', active ? 'font-semibold' : ''].join(' ')}>{label}</span>
    </Link>
  )
}

export function StaffLayout() {
  const { me, logout } = useAuth()
  const role = me?.role

  const tabs =
    role === 'master'
      ? [
          { to: '/staff/schedule', label: 'Schedule' },
          { to: '/staff', label: 'Home' },
        ]
      : role === 'manager'
        ? [
            { to: '/staff/dashboard', label: 'Today' },
            { to: '/staff/appointments', label: 'Clients' },
            { to: '/staff/masters', label: 'Masters' },
            { to: '/staff/requests', label: 'Requests' },
            { to: '/staff/revenue', label: 'Revenue' },
          ]
        : [
            { to: '/staff/admin/branches', label: 'Branches' },
            { to: '/staff/admin/staff', label: 'Staff' },
            { to: '/staff/admin/procedures', label: 'Procedures' },
            { to: '/staff/admin/revenue', label: 'Revenue' },
          ]

  return (
    <div className="min-h-full bg-slate-50 pb-16">
      <div className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-lg items-center justify-between px-4 py-3">
          <div className="text-sm font-semibold">Zenail Staff</div>
          <button
            onClick={logout}
            className="text-xs text-slate-600 hover:text-slate-900"
            type="button"
          >
            Logout
          </button>
        </div>
      </div>

      <Outlet />

      <div className="fixed bottom-0 left-0 right-0 border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-lg">
          {tabs.map((t) => (
            <NavLink key={t.to} to={t.to} label={t.label} />
          ))}
        </div>
      </div>
    </div>
  )
}

