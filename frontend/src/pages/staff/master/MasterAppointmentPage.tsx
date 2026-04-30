import { useForm } from 'react-hook-form'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../../../api/client'
import type { Appointment } from '../../../api/types'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Input } from '../../../components/Input'
import { Page } from '../../../components/Page'
import { useAuth } from '../../../state/useAuth'
import { appointmentStatusLabel, useT } from '../../../state/useT'

type FormValues = { proposed_start_time: string; reason?: string }

export function MasterAppointmentPage() {
  const t = useT()
  const { id } = useParams()
  const nav = useNavigate()
  const { token } = useAuth()
  const qc = useQueryClient()

  const apptQ = useQuery({
    queryKey: ['masterAppointment', id],
    enabled: !!id,
    queryFn: () =>
      apiFetch<Appointment>(`/api/master/appointments/${id}`, { token: token ?? undefined }),
  })

  const m = useMutation({
    mutationFn: (v: FormValues) =>
      apiFetch(`/api/master/reschedule-requests`, {
        method: 'POST',
        token: token ?? undefined,
        body: JSON.stringify({
          appointment_id: Number(id),
          proposed_start_time: new Date(v.proposed_start_time).toISOString(),
          reason: v.reason,
        }),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['masterAppointments'] })
    },
  })

  const { register, handleSubmit } = useForm<FormValues>({
    defaultValues: { proposed_start_time: toDateTimeLocal(new Date().toISOString()), reason: '' },
  })

  return (
    <Page title={t('master.appt.title')} subtitle={t('master.appt.subtitle', { id: id ?? '' })}>
      <Button variant="secondary" className="mb-3" type="button" onClick={() => nav(-1)}>
        {t('master.appt.back')}
      </Button>
      <Card className="mb-3">
        {apptQ.isLoading ? <div className="text-xs text-rose-800/80">{t('master.appt.loading')}</div> : null}
        {apptQ.isError ? (
          <div className="text-xs text-rose-700">{t('master.appt.error')}</div>
        ) : null}
        {apptQ.data ? (
          <div className="space-y-1 text-xs text-rose-950">
            <div>
              <span className="text-rose-900/60">{t('master.appt.client')}:</span>{' '}
              {apptQ.data.client_name} ({apptQ.data.client_phone})
            </div>
            <div>
              <span className="text-rose-900/60">{t('master.appt.time')}:</span>{' '}
              {new Date(apptQ.data.start_time).toLocaleString()}
            </div>
            <div>
              <span className="text-rose-900/60">{t('master.appt.procedures')}:</span>{' '}
              {(apptQ.data.procedures ?? []).map((p) => p.name).join(', ') ||
                t('common.procedureFallback', { id: apptQ.data.procedure_id })}
            </div>
            <div>
              <span className="text-rose-900/60">{t('master.appt.total')}:</span> ${apptQ.data.price} ·{' '}
              {apptQ.data.total_duration_minutes ?? t('common.emDash')} {t('common.minutes')}
            </div>
            <div>
              <span className="text-rose-900/60">{t('master.appt.status')}:</span>{' '}
              {appointmentStatusLabel(t, apptQ.data.status)}
            </div>
          </div>
        ) : (
          <div className="text-xs text-rose-900/75">{t('master.appt.hint')}</div>
        )}
      </Card>

      <Card>
        <form
          className="space-y-3"
          onSubmit={handleSubmit(async (v) => {
            await m.mutateAsync(v)
          })}
        >
          <div>
            <label className="mb-1 block text-xs font-medium text-rose-900">{t('master.appt.proposedLabel')}</label>
            <Input type="datetime-local" {...register('proposed_start_time', { required: true })} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-rose-900">{t('master.appt.reasonLabel')}</label>
            <Input {...register('reason')} />
          </div>
          <Button className="w-full" disabled={m.isPending} type="submit">
            {m.isPending ? t('master.appt.sending') : t('master.appt.submit')}
          </Button>
          {m.isError ? <div className="text-xs text-rose-700">{t('master.appt.sendError')}</div> : null}
          {m.isSuccess ? <div className="text-xs text-emerald-700">{t('master.appt.sendOk')}</div> : null}
        </form>
      </Card>
    </Page>
  )
}

function toDateTimeLocal(value: string) {
  const date = new Date(value)
  const offsetMs = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16)
}
