import { Outlet } from 'react-router-dom'

export function GuestLayout() {
  return (
    <div className="min-h-full bg-slate-50">
      <div className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-lg items-center justify-between px-4 py-3">
          <div className="text-sm font-semibold">Zenail</div>
          <a className="text-xs text-slate-600 hover:text-slate-900" href="/staff/login">
            Staff login
          </a>
        </div>
      </div>
      <Outlet />
    </div>
  )
}

