import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'

export function GuestLayout() {
  const loc = useLocation()
  const nav = useNavigate()
  const canGoBack = loc.pathname !== '/book/branch'

  return (
    <div className="min-h-full bg-slate-50">
      <div className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-lg items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            {canGoBack ? (
              <button
                className="text-xs text-slate-600 hover:text-slate-900"
                type="button"
                onClick={() => nav(-1)}
              >
                Back
              </button>
            ) : null}
            <Link className="text-sm font-semibold" to="/book/branch">
              Zenail
            </Link>
          </div>
          <Link className="text-xs text-slate-600 hover:text-slate-900" to="/staff/login">
            Staff login
          </Link>
        </div>
      </div>
      <Outlet />
    </div>
  )
}

