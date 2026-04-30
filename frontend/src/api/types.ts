export type StaffRole = 'master' | 'manager' | 'admin'

export type Branch = {
  id: number
  name: string
  address?: string | null
  phone?: string | null
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
  branch_id: number
  master_id: number
  master_name?: string | null
  procedure_id: number
  procedure_ids: number[]
  procedures: AppointmentProcedure[]
  client_name: string
  client_phone: string
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
  role: StaffRole
  branch_id: number | null
}

