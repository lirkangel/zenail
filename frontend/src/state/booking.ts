import type { Appointment } from '../api/types'

const LAST_BOOKING_KEY = 'zenail.lastBooking'
const GUEST_BOOKING_DRAFT_KEY = 'zenail.guestBookingDraft'

export type LastBooking = {
  booking_reference: string
}

export type GuestBookingDraft = {
  branch_id: string
  master_id: string
  procedures: string
  day: string
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

export function saveGuestBookingDraft(draft: GuestBookingDraft) {
  sessionStorage.setItem(GUEST_BOOKING_DRAFT_KEY, JSON.stringify(draft))
}

export function getGuestBookingDraft(): GuestBookingDraft | null {
  const raw = sessionStorage.getItem(GUEST_BOOKING_DRAFT_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as GuestBookingDraft
  } catch {
    sessionStorage.removeItem(GUEST_BOOKING_DRAFT_KEY)
    return null
  }
}
