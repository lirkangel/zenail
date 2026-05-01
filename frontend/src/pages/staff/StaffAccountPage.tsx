import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { apiFetch, type ApiError } from '../../api/client'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { Input } from '../../components/Input'
import { Page } from '../../components/Page'
import { useAuth } from '../../state/useAuth'
import { useT } from '../../state/useT'

type FormValues = {
  full_name: string
  email: string
  phone: string
  password: string
}

export function StaffAccountPage() {
  const t = useT()
  const nav = useNavigate()
  const { me, token, refreshMe } = useAuth()
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
    setError,
  } = useForm<FormValues>({
    defaultValues: {
      full_name: me?.full_name ?? '',
      email: me?.email ?? '',
      phone: me?.phone ?? '',
      password: '',
    },
  })

  return (
    <Page title={t('staff.account.title')} subtitle={t('staff.account.subtitle')}>
      <Card>
        <form
          className="space-y-3"
          onSubmit={handleSubmit(async (values) => {
            try {
              await apiFetch('/api/me', {
                method: 'PATCH',
                token: token ?? undefined,
                body: JSON.stringify({
                  full_name: values.full_name.trim(),
                  email: values.email.trim(),
                  phone: values.phone.trim() || null,
                  ...(values.password.trim() ? { password: values.password.trim() } : {}),
                }),
              })
              await refreshMe()
              nav('/staff', { replace: true })
            } catch (error) {
              const apiError = error as ApiError
              setError('email', { message: apiError.message || t('staff.account.saveError') })
            }
          })}
        >
          <div>
            <label className="mb-1 block text-xs font-medium text-rose-900">{t('common.name')}</label>
            <Input {...register('full_name', { required: true })} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-rose-900">{t('common.email')}</label>
            <Input type="email" {...register('email', { required: true })} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-rose-900">{t('common.phone')}</label>
            <Input {...register('phone')} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-rose-900">{t('staff.account.newPassword')}</label>
            <Input type="password" {...register('password')} placeholder={t('staff.account.passwordHint')} />
          </div>
          <Button className="w-full" disabled={isSubmitting} type="submit">
            {isSubmitting ? t('common.saving') : t('staff.account.save')}
          </Button>
        </form>
      </Card>
    </Page>
  )
}
