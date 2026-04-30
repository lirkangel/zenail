import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { Input } from '../../components/Input'
import { Page } from '../../components/Page'
import { useAuth } from '../../state/useAuth'
import { useT } from '../../state/useT'

type FormValues = { email: string; password: string }

export function StaffLoginPage() {
  const t = useT()
  const { login } = useAuth()
  const nav = useNavigate()
  const {
    register,
    handleSubmit,
    formState: { isSubmitting, errors },
    setError,
  } = useForm<FormValues>({ defaultValues: { email: '', password: '' } })

  return (
    <Page title={t('staff.login.title')} subtitle={t('staff.login.subtitle')}>
      <Card>
        <form
          className="space-y-3"
          onSubmit={handleSubmit(async (v) => {
            try {
              await login(v.email, v.password)
              nav('/staff', { replace: true })
            } catch {
              setError('password', { message: t('staff.login.invalid') })
            }
          })}
        >
          <div>
            <label className="mb-1 block text-xs font-medium text-rose-900">{t('staff.login.emailLabel')}</label>
            <Input type="text" autoComplete="email" {...register('email', { required: true })} />
            {errors.email ? (
              <div className="mt-1 text-xs text-rose-600">{t('staff.login.emailRequired')}</div>
            ) : null}
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-rose-900">{t('staff.login.passwordLabel')}</label>
            <Input
              type="password"
              autoComplete="current-password"
              {...register('password', { required: true })}
            />
            {errors.password ? (
              <div className="mt-1 text-xs text-rose-600">
                {errors.password.message ?? t('staff.login.passwordRequired')}
              </div>
            ) : null}
          </div>

          <Button className="w-full" disabled={isSubmitting} type="submit">
            {isSubmitting ? t('staff.login.signingIn') : t('staff.login.signIn')}
          </Button>
        </form>
      </Card>
    </Page>
  )
}
