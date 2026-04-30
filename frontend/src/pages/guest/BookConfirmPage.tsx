import { useForm } from 'react-hook-form'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { apiFetch } from '../../api/client'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { Input } from '../../components/Input'
import { Page } from '../../components/Page'
import type { Appointment } from '../../api/types'

type FormValues = { client_name: string; client_phone: string }

export function BookConfirmPage() {
  const [sp] = useSearchParams()
  const nav = useNavigate()
  const branchId = sp.get('branch')
  const masterId = sp.get('master')
  const procedureId = sp.get('procedure')
  const startTime = sp.get('start_time')

  const {
    register,
    handleSubmit,
    formState: { isSubmitting, errors },
  } = useForm<FormValues>({ defaultValues: { client_name: '', client_phone: '' } })

  return (
    <Page title="Confirm booking" subtitle="Enter your details and confirm.">
      {!branchId || !masterId || !procedureId || !startTime ? (
        <div className="text-sm text-rose-700">Missing booking information.</div>
      ) : null}

      <Card>
        <form
          className="space-y-3"
          onSubmit={handleSubmit(async (v) => {
            if (!branchId || !masterId || !procedureId || !startTime) return
            const appt = await apiFetch<Appointment>('/api/appointments', {
              method: 'POST',
              body: JSON.stringify({
                branch_id: Number(branchId),
                master_id: Number(masterId),
                procedure_id: Number(procedureId),
                client_name: v.client_name,
                client_phone: v.client_phone,
                start_time: startTime,
              }),
            })
            nav(`/book/success?id=${appt.id}`, { replace: true })
          })}
        >
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Name</label>
            <Input {...register('client_name', { required: true })} />
            {errors.client_name ? (
              <div className="mt-1 text-xs text-rose-600">Name is required</div>
            ) : null}
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Phone</label>
            <Input {...register('client_phone', { required: true })} />
            {errors.client_phone ? (
              <div className="mt-1 text-xs text-rose-600">Phone is required</div>
            ) : null}
          </div>

          <Button className="w-full" disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Booking…' : 'Confirm booking'}
          </Button>
        </form>
      </Card>
    </Page>
  )
}

