import type { Appointment } from '../api/types'

const LAST_BOOKING_KEY = 'zenail.lastBooking'

export type LastBooking = {
  booking_reference: string
}

export function saveLastBooking(appt: Appointment) {
  localStorage.setItem(
    LAST_BOOKING_KEY,
    JSON.stringify({ booking_reference: appt.booking_reference }),
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
