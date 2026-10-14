import { Link, useLocation, useParams } from 'react-router-dom'
import { money, OrderResult } from '../api'
import HandsomeDan from '../components/HandsomeDan'

interface State {
  order: OrderResult
  name: string
  email: string
  phone?: string
  fulfillment: 'pickup' | 'ship'
}

export default function OrderConfirmation() {
  const { orderNumber } = useParams()
  const state = useLocation().state as State | null

  return (
    <section className="section narrow confirmation">
      <HandsomeDan size={150} />
      <p className="eyebrow">Order placed</p>
      <h1>Boola Boola, thank you{state ? `, ${state.name.split(' ')[0]}` : ''}!</h1>
      <p className="lead">
        Your transaction number is <strong className="order-number">{orderNumber}</strong>.
      </p>
      <p className="muted small">Save it: you can track this order any time with this number and your email or phone.</p>
      <Link
        to={`/track?${new URLSearchParams({ order: orderNumber ?? '', contact: state?.email ?? '' })}`}
        className="btn btn-ghost"
      >
        📦 Track this order
      </Link>
      {state && (
        <>
          <p className="muted">
            {state.fulfillment === 'pickup'
              ? 'Pick it up at 57 Broadway, New Haven, and pay in store.'
              : 'We will ship it to the address you gave and you pay on delivery.'}{' '}
            A confirmation goes to <strong>{state.email}</strong>
            {state.order.guest ? ' (guest checkout).' : '.'} Payment: <strong>{state.order.payment_method}</strong>.
          </p>
          <div className="card pad">
            {state.order.items.map(i => (
              <p key={`${i.product_id}-${i.size}`} className="summary-row">
                <span>
                  <Link to={`/products/${i.product_id}`} className="link">{i.name}</Link> · size {i.size} × {i.quantity}
                </span>
                <span>{money(i.line_total)}</span>
              </p>
            ))}
            <p className="summary-row total"><span>Subtotal</span><span>{money(state.order.subtotal)}</span></p>
          </div>
        </>
      )}
      <Link to="/products" className="btn">Keep shopping</Link>
    </section>
  )
}
