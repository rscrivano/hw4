import HandsomeDan from '../components/HandsomeDan'
import { ChangeEvent, FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, RegisterInput } from '../api'
import { useAuth } from '../auth'

const EMPTY: RegisterInput = { first_name: '', last_name: '', email: '', password: '', confirm_password: '' }

export default function Register() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<RegisterInput>(EMPTY)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (k: keyof RegisterInput) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  async function submit(e: FormEvent) {
    e.preventDefault()
    // Quick checks in the browser; the backend repeats every check.
    if (form.password.length < 8) return setError('Password must be at least 8 characters.')
    if (form.password !== form.confirm_password) return setError('Passwords do not match.')
    setError('')
    setLoading(true)
    try {
      signIn(await api.register(form))
      navigate('/products')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="section auth">
      <form className="card pad auth-card" onSubmit={submit}>
        <HandsomeDan face size={72} className="auth-dan" title="" />
        <h1>Create account</h1>
        <p className="muted">Join Campus Customs to chat with our assistant and save your favorites.</p>

        <div className="row">
          <label>
            First name
            <input required autoComplete="given-name" value={form.first_name} onChange={set('first_name')} />
          </label>
          <label>
            Last name
            <input required autoComplete="family-name" value={form.last_name} onChange={set('last_name')} />
          </label>
        </div>
        <label>
          Email
          <input type="email" required autoComplete="email" value={form.email} onChange={set('email')} />
        </label>
        <label>
          Password <span className="muted small">(at least 8 characters)</span>
          <input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={form.password}
            onChange={set('password')}
          />
        </label>
        <label>
          Confirm password
          <input
            type="password"
            required
            autoComplete="new-password"
            value={form.confirm_password}
            onChange={set('confirm_password')}
          />
        </label>

        {error && <p className="status error" role="alert">{error}</p>}
        <button className="btn btn-block" disabled={loading}>{loading ? 'Creating account…' : 'Create account'}</button>
        <p className="muted small">
          Already have an account? <Link to="/login" className="link">Log in</Link>
        </p>
      </form>
    </section>
  )
}
