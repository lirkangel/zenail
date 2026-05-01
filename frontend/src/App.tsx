import { Navigate, Route, Routes } from 'react-router-dom'
import { RequireRole, RequireStaff } from './state/auth.tsx'
import { GuestLayout } from './layouts/GuestLayout.tsx'
import { StaffLayout } from './layouts/StaffLayout.tsx'
import { BookBranchPage } from './pages/guest/BookBranchPage.tsx'
import { BookConfirmPage } from './pages/guest/BookConfirmPage.tsx'
import { BookMasterPage } from './pages/guest/BookMasterPage.tsx'
import { BookProcedurePage } from './pages/guest/BookProcedurePage.tsx'
import { BookSuccessPage } from './pages/guest/BookSuccessPage.tsx'
import { BookTimePage } from './pages/guest/BookTimePage.tsx'
import { StaffLoginPage } from './pages/staff/StaffLoginPage.tsx'
import { StaffHomeRedirect } from './pages/staff/StaffHomeRedirect.tsx'
import { StaffAccountPage } from './pages/staff/StaffAccountPage.tsx'
import { MasterSchedulePage } from './pages/staff/master/MasterSchedulePage.tsx'
import { MasterAppointmentPage } from './pages/staff/master/MasterAppointmentPage.tsx'
import { ManagerDashboardPage } from './pages/staff/manager/ManagerDashboardPage.tsx'
import { ManagerAppointmentsPage } from './pages/staff/manager/ManagerAppointmentsPage.tsx'
import { ManagerMastersPage } from './pages/staff/manager/ManagerMastersPage.tsx'
import { ManagerRequestsPage } from './pages/staff/manager/ManagerRequestsPage.tsx'
import { ManagerRevenuePage } from './pages/staff/manager/ManagerRevenuePage.tsx'
import { AdminBranchesPage } from './pages/staff/admin/AdminBranchesPage.tsx'
import { AdminProceduresPage } from './pages/staff/admin/AdminProceduresPage.tsx'
import { AdminStaffPage } from './pages/staff/admin/AdminStaffPage.tsx'
import { AdminRevenuePage } from './pages/staff/admin/AdminRevenuePage.tsx'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/book/branch" replace />} />

      <Route element={<GuestLayout />}>
        <Route path="/book/branch" element={<BookBranchPage />} />
        <Route path="/book/master" element={<BookMasterPage />} />
        <Route path="/book/procedure" element={<BookProcedurePage />} />
        <Route path="/book/time" element={<BookTimePage />} />
        <Route path="/book/confirm" element={<BookConfirmPage />} />
        <Route path="/book/success" element={<BookSuccessPage />} />
      </Route>

      <Route path="/staff/login" element={<StaffLoginPage />} />
      <Route
        element={
          <RequireStaff>
            <StaffLayout />
          </RequireStaff>
        }
      >
        <Route path="/staff" element={<StaffHomeRedirect />} />
        <Route path="/staff/account" element={<StaffAccountPage />} />

        <Route element={<RequireRole roles={['master', 'admin']} />}>
          <Route path="/staff/schedule" element={<MasterSchedulePage />} />
          <Route path="/staff/appointments/:id" element={<MasterAppointmentPage />} />
        </Route>

        <Route element={<RequireRole roles={['manager', 'admin']} />}>
          <Route path="/staff/dashboard" element={<ManagerDashboardPage />} />
          <Route path="/staff/appointments" element={<ManagerAppointmentsPage />} />
          <Route path="/staff/masters" element={<ManagerMastersPage />} />
          <Route path="/staff/requests" element={<ManagerRequestsPage />} />
          <Route path="/staff/revenue" element={<ManagerRevenuePage />} />
        </Route>

        <Route element={<RequireRole roles={['admin']} />}>
          <Route path="/staff/admin/branches" element={<AdminBranchesPage />} />
          <Route path="/staff/admin/staff" element={<AdminStaffPage />} />
          <Route path="/staff/admin/procedures" element={<AdminProceduresPage />} />
          <Route path="/staff/admin/revenue" element={<AdminRevenuePage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/book/branch" replace />} />
    </Routes>
  )
}

export default App
