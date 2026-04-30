import { Navigate } from 'react-router-dom'
import { useAuth } from '../../state/useAuth'

export function StaffHomeRedirect() {
  const { me } = useAuth()
  if (!me) return <Navigate to="/staff/login" replace />
  if (me.role === 'master') return <Navigate to="/staff/schedule" replace />
  if (me.role === 'manager') return <Navigate to="/staff/dashboard" replace />
  return <Navigate to="/staff/admin/revenue" replace />
}

