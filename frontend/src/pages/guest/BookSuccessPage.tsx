import { useSearchParams } from 'react-router-dom'
import { Card } from '../../components/Card'
import { Page } from '../../components/Page'

export function BookSuccessPage() {
  const [sp] = useSearchParams()
  const id = sp.get('id')
  return (
    <Page title="Booked" subtitle="Your appointment is confirmed.">
      <Card>
        <div className="text-sm">
          Appointment ID: <span className="font-semibold">{id ?? '—'}</span>
        </div>
        <div className="mt-2 text-xs text-slate-600">
          Please arrive a few minutes early. If you need to change time, contact the salon.
        </div>
      </Card>
    </Page>
  )
}

