import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, money, Quote } from '../api'
import { useCart } from '../cart'
import { ErrorBox, Loading } from '../components/Status'
import HandsomeDan from '../components/HandsomeDan'
import { growl } from '../fx'

export default function Cart() {
  const { lines, setQuantity, remove } = useCart()
  const [quote, setQuote] = useState<Quote | null>(null)
  const [error, setError] = useState('')

  // Re-price from the server whenever the cart changes: live prices, live stock, clear problems.
  useEffect(() => {
    setError('')
    if (!lines.length) return setQuote(null)
    api
      .quote(lines.map(({ product_id, size, quantity }) => ({ product_id, size, quantity })))
      .then(setQuote)
      .catch(e => setError(e.message))
  }, [lines])

  if (!lines.length) {
    return (
      <section className="section narrow cart-empty">
        <HandsomeDan size={140} />
        <h1>Your cart is empty</h1>
        <p className="muted">Find something you love, pick a size and add it to your cart.</p>
        <Link to="/products" className="btn">Browse products</Link>
      </section>
    )
  }

  return (
    <section className="section cart-page">
      <h1>Your cart</h1>
      {error && <ErrorBox message={error} />}
      {!quote && !error && <Loading label="Checking prices and stock…" />}

      {quote && (
        <div className="cart-layout">
          <ul className="cart-lines">
            {quote.lines.map(l => (
              <li key={`${l.product_id}-${l.size}`} className={`card cart-line ${l.issue ? 'has-issue' : ''}`}>
                <Link to={`/products/${l.product_id}`} className="cart-thumb">
                  <img src={l.image_url} alt={l.name} />
                </Link>
                <div className="cart-info">
                  <Link to={`/products/${l.product_id}`} className="cart-name">{l.name}</Link>
                  <p className="muted small">Size <strong>{l.size}</strong> · {money(l.unit_price)} each</p>
                  {l.issue && <p className="cart-issue" role="alert">⚠ {l.issue}</p>}
                  <div className="cart-controls">
                    <label>
                      <span className="sr-only">Quantity for {l.name} size {l.size}</span>
                      <select
                        value={l.quantity}
                        onChange={e => setQuantity(l.product_id, l.size, Number(e.target.value))}
                      >
                        {Array.from({ length: Math.max(Math.min(l.available, 10), l.quantity, 1) }, (_, i) => i + 1).map(n => (
                          <option key={n} value={n}>Qty {n}</option>
                        ))}
                      </select>
                    </label>
                    <button
                      className="link-button"
                      onClick={() => {
                        growl() // Handsome Dan isn't happy to see it go (Problem 10)
                        remove(l.product_id, l.size)
                      }}
                    >
                      Remove
                    </button>
                  </div>
                </div>
                <p className="cart-total">{money(l.line_total)}</p>
              </li>
            ))}
          </ul>

          <aside className="card pad cart-summary">
            <h2>Order summary</h2>
            <p className="summary-row"><span>Items</span><span>{quote.item_count}</span></p>
            <p className="summary-row total"><span>Subtotal</span><span>{money(quote.subtotal)}</span></p>
            <p className="muted small">Tax and shipping are calculated at pickup / delivery.</p>
            {quote.problems.length > 0 && (
              <p className="status error small">Please fix the items marked ⚠ before checking out.</p>
            )}
            {quote.ok ? (
              <Link to="/checkout" className="btn btn-block">Checkout</Link>
            ) : (
              <button className="btn btn-block" disabled>Checkout</button>
            )}
            <p className="muted small center">No account needed: you can check out as a guest.</p>
            <Link to="/products" className="link small center">← Keep shopping</Link>
          </aside>
        </div>
      )}
    </section>
  )
}
