import { FormEvent, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, money, TrackedOrder } from '../api'
import HandsomeDan from '../components/HandsomeDan'

/** Track an order with its transaction number + the email or phone used at checkout (Problem 12). */
export default function TrackOrder() {
  const [params] = useSearchParams()
  const [number, setNumber] = useState(params.get('order') ?? '')
  const [contact, setContact] = useState(params.get('contact') ?? '')
  const [order, setOrder] = useState<TrackedOrder | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function lookup(e?: FormEvent) {
    e?.preventDefault()
    setError('')
    setOrder(null)
    setLoading(true)
    try {
      setOrder(await api.trackOrder(number, contact))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  // Arriving from the confirmation page with both values filled in: look it up straight away.
  useEffect(() => {
    if (params.get('order') && params.get('contact')) lookup()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <section className="section narrow track-page">
      <div className="about-hero">
        <div>
          <p className="eyebrow">Order tracking</p>
          <h1>Track your order</h1>
          <p className="muted">Enter your transaction number (e.g. CC-261014-K7Q2MX) and the email or phone you used at checkout.</p>
        </div>
        <HandsomeDan size={110} />
      </div>

      <form className="card pad checkout-form" onSubmit={lookup}>
        <label>
          Transaction number
          <input required value={number} onChange={e => setNumber(e.target.value)} placeholder="CC-…" autoCapitalize="characters" />
        </label>
        <label>
          Email or phone used at checkout
          <input required value={contact} onChange={e => setContact(e.target.value)} autoComplete="email" />
        </label>
        {error && <p className="status error" role="alert">{error}</p>}
        <button className="btn btn-block" disabled={loading}>{loading ? 'Looking it up…' : 'Track order'}</button>
      </form>

      {order && (
        <div className="card pad track-result" role="status">
          <p className="eyebrow">Order {order.order_number}</p>
          <h2>Thanks, {order.customer_name.split(' ')[0]}! Your order is {order.status}.</h2>
          <ol className="timeline">
            {order.timeline.map(t => (
              <li key={t.step} className={t.done ? 'done' : ''}>
                <span>{t.done ? '✓' : '…'}</span> {t.step}
                {t.at && <small> · {t.at} UTC</small>}
              </li>
            ))}
          </ol>
          <p className="summary-row"><span>Payment</span><span>{order.payment_method} · {order.payment_status}</span></p>
          {order.items.map(i => (
            <p key={`${i.product_id}-${i.size}`} className="summary-row">
              <span><Link to={`/products/${i.product_id}`} className="link">{i.name}</Link> · size {i.size} × {i.quantity}</span>
              <span>{money(i.line_total)}</span>
            </p>
          ))}
          <p className="summary-row total"><span>Subtotal</span><span>{money(order.subtotal)}</span></p>
        </div>
      )}
    </section>
  )
}
