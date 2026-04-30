import { useForm } from 'react-hook-form'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { apiFetch } from '../../api/client'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { Input } from '../../components/Input'
import { Page } from '../../components/Page'
import type { Appointment } from '../../api/types'
import { useT } from '../../state/useT'
import { saveLastBooking } from '../../state/booking'

type FormValues = { client_name: string; client_phone: string }

export function BookConfirmPage() {
  const t = useT()
  const [sp] = useSearchParams()
  const nav = useNavigate()
  const branchId = sp.get('branch')
  const masterId = sp.get('master')
  const procedureIds = sp.get('procedures') ?? sp.get('procedure')
  const startTime = sp.get('start_time')

  const {
    register,
    handleSubmit,
    formState: { isSubmitting, errors },
  } = useForm<FormValues>({ defaultValues: { client_name: '', client_phone: '' } })

  return (
    <Page title={t('guest.confirm.title')} subtitle={t('guest.confirm.subtitle')}>
      {!branchId || !masterId || !procedureIds || !startTime ? (
        <div className="text-sm text-rose-700">{t('guest.confirm.missing')}</div>
      ) : null}

      <Card>
        <form
          className="space-y-3"
          onSubmit={handleSubmit(async (v) => {
            if (!branchId || !masterId || !procedureIds || !startTime) return
            const appt = await apiFetch<Appointment>('/api/appointments', {
              method: 'POST',
              body: JSON.stringify({
                branch_id: Number(branchId),
                master_id: Number(masterId),
                procedure_ids: procedureIds.split(',').map((id) => Number(id)),
                client_name: v.client_name,
                client_phone: v.client_phone,
                start_time: startTime,
              }),
            })
            saveLastBooking(appt)
            nav(`/book/success?id=${appt.id}`, { replace: true })
          })}
        >
          <div>
            <label className="mb-1 block text-xs font-medium text-rose-900/80">{t('common.name')}</label>
            <Input {...register('client_name', { required: true })} />
            {errors.client_name ? (
              <div className="mt-1 text-xs text-rose-600">{t('guest.confirm.nameRequired')}</div>
            ) : null}
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-rose-900/80">{t('common.phone')}</label>
            <Input {...register('client_phone', { required: true })} />
            {errors.client_phone ? (
              <div className="mt-1 text-xs text-rose-600">{t('guest.confirm.phoneRequired')}</div>
            ) : null}
          </div>

          <Button className="w-full" disabled={isSubmitting} type="submit">
            {isSubmitting ? t('guest.confirm.booking') : t('guest.confirm.submit')}
          </Button>
        </form>
      </Card>
    </Page>
  )
}
