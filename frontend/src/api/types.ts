export type StaffRole = 'master' | 'manager' | 'admin'

export type Branch = {
  id: number
  name: string
  address?: string | null
  phone?: string | null
  timezone: string
  open_time: string
  close_time: string
}

export type Master = { id: number; full_name: string }

export type Procedure = {
  id: number
  name: string
  description?: string | null
  category?: string | null
  duration_minutes: number
  price: string
}

export type Availability = {
  master_id: number
  procedure_id?: number | null
  procedure_ids: number[]
  date: string
  branch_timezone: string
  total_duration_minutes: number
  total_price: string
  slots: string[]
}

export type AppointmentProcedure = {
  id: number
  name: string
  duration_minutes: number
  price: string
}

export type Appointment = {
  id: number
  booking_reference: string
  branch_id: number
  master_id: number
  customer_id?: number | null
  master_name?: string | null
  procedure_id: number
  procedure_ids: number[]
  procedures: AppointmentProcedure[]
  client_name: string
  client_phone: string
  client_email?: string | null
  start_time: string
  end_time: string
  total_duration_minutes: number
  price: string
  status: 'scheduled' | 'completed' | 'canceled'
}

export type LoginResponse = {
  access_token: string
  token_type: 'bearer'
  role: StaffRole
  branch_id: number | null
}

export type Me = {
  id: number
  full_name: string
  email: string
  phone?: string | null
  role: StaffRole
  branch_id: number | null
}

export type CustomerSummary = {
  id: number
  full_name: string
  phone: string
  email?: string | null
  notes?: string | null
  visit_count: number
  completed_spend: string
  latest_visit?: string | null
  upcoming_appointment?: string | null
}

export type CustomerList = {
  items: CustomerSummary[]
  total: number
  limit: number
  offset: number
}

export type CustomerAppointment = {
  id: number
  branch_id: number
  master_id: number
  master_name?: string | null
  start_time: string
  end_time: string
  price: string
  status: 'scheduled' | 'completed' | 'canceled'
  procedures: string[]
}

export type CustomerDetail = CustomerSummary & {
  appointments: CustomerAppointment[]
}
