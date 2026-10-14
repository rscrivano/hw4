import { FormEvent, useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { api, money, PaymentMethod, Quote } from '../api'
import { useAuth } from '../auth'
import { useCart } from '../cart'
import { Loading } from '../components/Status'

export default function Checkout() {
  const { user, token } = useAuth()
  const { lines, clear } = useCart()
  const navigate = useNavigate()
  const [quote, setQuote] = useState<Quote | null>(null)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [fulfillment, setFulfillment] = useState<'pickup' | 'ship'>('pickup')
  const [address, setAddress] = useState('')
  const [phone, setPhone] = useState('')
  const [payment, setPayment] = useState<PaymentMethod | null>(null) // nothing pre-selected: the shopper must choose
  const [error, setError] = useState('')
  const [placing, setPlacing] = useState(false)

  // Logged-in shoppers get their details filled in; guests type them.
  useEffect(() => {
    if (user) {
      setName(user.name)
      setEmail(user.email)
    }
  }, [user])

  const items = lines.map(({ product_id, size, quantity }) => ({ product_id, size, quantity }))
  useEffect(() => {
    if (items.length) api.quote(items).then(setQuote).catch(e => setError(e.message))
  }, [lines]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!lines.length) return <Navigate to="/cart" replace />

  const methods: { id: PaymentMethod; label: string; note: string }[] =
    fulfillment === 'pickup'
      ? [
          { id: 'card_at_pickup', label: 'Card at pickup', note: 'Tap or insert your card at the register.' },
          { id: 'cash_at_pickup', label: 'Cash at pickup', note: 'Pay in cash when you collect your order.' },
        ]
      : [
          { id: 'card_on_delivery', label: 'Card on delivery', note: 'The courier brings a card reader.' },
          { id: 'cash_on_delivery', label: 'Cash on delivery', note: 'Pay the courier in cash.' },
        ]
  const phoneDigits = phone.replace(/\D/g, '')
  const phoneOk = phoneDigits.length === 0 ? !!user : phoneDigits.length >= 10 && phoneDigits.length <= 15

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setPlacing(true)
    try {
      const order = await api.placeOrder(
        {
          items, customer_name: name, email, phone: phone || undefined, fulfillment,
          shipping_address: fulfillment === 'ship' ? address : undefined, payment_method: payment,
        },
        token,
      )
      clear()
      navigate(`/order/${order.order_number}`, { state: { order, name, email, phone, fulfillment } })
    } catch (err) {
      setError((err as Error).message)
      api.quote(items).then(setQuote).catch(() => {}) // refresh the summary after a stock conflict
    } finally {
      setPlacing(false)
    }
  }

  return (
    <section className="section checkout-page">
      <h1>Checkout</h1>
      <div className="cart-layout">
        <form className="card pad checkout-form" onSubmit={submit}>
          {user ? (
            <p className="status ok">Checking out as <strong>{user.name}</strong>. This order will be linked to your account.</p>
          ) : (
            <div className="guest-banner">
              <strong>Checking out as a guest</strong>
              <span className="muted small">
                No account needed. Just tell us where to send your confirmation.{' '}
                <Link to="/login" className="link">Log in</Link> instead
              </span>
            </div>
          )}

          <label>
            Full name
            <input required autoComplete="name" value={name} onChange={e => setName(e.target.value)} />
          </label>
          <label>
            Email for your confirmation
            <input type="email" required autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} />
          </label>

          <label>
            Phone number {user ? <span className="muted small">(optional)</span> : <span className="req">required for guests</span>}
            <input
              type="tel"
              required={!user}
              autoComplete="tel"
              inputMode="tel"
              placeholder="(203) 555-0123"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              aria-invalid={phone.length > 0 && !phoneOk}
            />
          </label>

          <fieldset className="fulfillment">
            <legend>How would you like to get it?</legend>
            <label className={fulfillment === 'pickup' ? 'active' : ''}>
              <input type="radio" name="fulfillment" checked={fulfillment === 'pickup'} onChange={() => { setFulfillment('pickup'); setPayment(null) }} />
              <span><strong>In-store pickup</strong><small>57 Broadway, New Haven. Pay when you pick up.</small></span>
            </label>
            <label className={fulfillment === 'ship' ? 'active' : ''}>
              <input type="radio" name="fulfillment" checked={fulfillment === 'ship'} onChange={() => { setFulfillment('ship'); setPayment(null) }} />
              <span><strong>Ship to me</strong><small>Pay on delivery.</small></span>
            </label>
          </fieldset>
          {fulfillment === 'ship' && (
            <label>
              Shipping address
              <textarea required rows={3} autoComplete="street-address" value={address} onChange={e => setAddress(e.target.value)} />
            </label>
          )}

          <fieldset className="fulfillment payment">
            <legend>Payment method <span className="req">required</span></legend>
            {methods.map(m => (
              <label key={m.id} className={payment === m.id ? 'active' : ''}>
                <input type="radio" name="payment" checked={payment === m.id} onChange={() => setPayment(m.id)} />
                <span><strong>{m.label}</strong><small>{m.note}</small></span>
              </label>
            ))}
          </fieldset>
          <p className="muted small">
            🔒 We never ask for card details online. You pay {fulfillment === 'pickup' ? 'at pickup' : 'on delivery'}.
          </p>
          {error && <p className="status error" role="alert">{error}</p>}
          {!payment && <p className="muted small center">Choose a payment method to place your order.</p>}
          <button className="btn btn-block" disabled={placing || !quote?.ok || !payment || !phoneOk}>
            {placing ? 'Placing order…' : `Place order${quote ? ` · ${money(quote.subtotal)}` : ''}`}
          </button>
        </form>

        <aside className="card pad cart-summary">
          <h2>Your order</h2>
          {!quote && <Loading label="Checking prices and stock…" />}
          {quote?.lines.map(l => (
            <div key={`${l.product_id}-${l.size}`} className="summary-line">
              <img src={l.image_url} alt="" />
              <span>
                {l.name}
                <small>Size {l.size} · Qty {l.quantity}{l.issue ? ` · ⚠ ${l.issue}` : ''}</small>
              </span>
              <strong>{money(l.line_total)}</strong>
            </div>
          ))}
          {quote && <p className="summary-row total"><span>Subtotal</span><span>{money(quote.subtotal)}</span></p>}
          <Link to="/cart" className="link small">← Edit cart</Link>
        </aside>
      </div>
    </section>
  )
}
