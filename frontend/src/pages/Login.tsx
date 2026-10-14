import HandsomeDan from '../components/HandsomeDan'
import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'

export default function Login() {
  const { user, signIn, signOut } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      signIn(await api.login(email, password))
      navigate('/products')
    } catch (err) {
      setError((err as Error).message)
      setPassword('')
    } finally {
      setLoading(false)
    }
  }

  if (user) {
    return (
      <section className="section auth">
        <div className="card pad auth-card">
          <h1>You're logged in</h1>
          <p className="muted">Signed in as {user.name} ({user.email}).</p>
          <Link to="/products" className="btn btn-block">Keep shopping</Link>
          <button className="btn btn-ghost btn-block" onClick={signOut}>Log out</button>
        </div>
      </section>
    )
  }

  return (
    <section className="section auth">
      <form className="card pad auth-card" onSubmit={submit}>
        <HandsomeDan face size={72} className="auth-dan" title="" />
        <h1>Log in</h1>
        <p className="muted">Welcome back, Bulldog.</p>

        <label>
          Email
          <input type="email" required autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={e => setPassword(e.target.value)}
          />
        </label>

        {error && <p className="status error" role="alert">{error}</p>}
        <button className="btn btn-block" disabled={loading}>{loading ? 'Logging in…' : 'Log in'}</button>
        <p className="muted small">
          New here? <Link to="/register" className="link">Create an account</Link>
        </p>
      </form>
    </section>
  )
}
