import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { Input } from '../../components/Input'
import { Page } from '../../components/Page'
import { useAuth } from '../../state/auth'

type FormValues = { email: string; password: string }

export function StaffLoginPage() {
  const { login } = useAuth()
  const nav = useNavigate()
  const {
    register,
    handleSubmit,
    formState: { isSubmitting, errors },
    setError,
  } = useForm<FormValues>({ defaultValues: { email: '', password: '' } })

  return (
    <div className="min-h-full bg-slate-50">
      <Page title="Staff login" subtitle="Managers, masters, and admins only.">
        <Card>
          <form
            className="space-y-3"
            onSubmit={handleSubmit(async (v) => {
              try {
                await login(v.email, v.password)
                nav('/staff', { replace: true })
              } catch (e) {
                setError('password', { message: 'Invalid email or password' })
              }
            })}
          >
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700">Email</label>
              <Input type="email" autoComplete="email" {...register('email', { required: true })} />
              {errors.email ? (
                <div className="mt-1 text-xs text-rose-600">Email is required</div>
              ) : null}
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-slate-700">Password</label>
              <Input
                type="password"
                autoComplete="current-password"
                {...register('password', { required: true })}
              />
              {errors.password ? (
                <div className="mt-1 text-xs text-rose-600">
                  {errors.password.message ?? 'Password is required'}
                </div>
              ) : null}
            </div>

            <Button className="w-full" disabled={isSubmitting} type="submit">
              {isSubmitting ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>
        </Card>
      </Page>
    </div>
  )
}

