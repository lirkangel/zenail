import type { Appointment } from '../api/types'

const LAST_BOOKING_KEY = 'zenail.lastBooking'

export type LastBooking = {
  id: number
  client_phone: string
}

export function saveLastBooking(appt: Appointment) {
  localStorage.setItem(
    LAST_BOOKING_KEY,
    JSON.stringify({ id: appt.id, client_phone: appt.client_phone }),
  )
}

export function getLastBooking(): LastBooking | null {
  const raw = localStorage.getItem(LAST_BOOKING_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as LastBooking
  } catch {
    localStorage.removeItem(LAST_BOOKING_KEY)
    return null
  }
}

