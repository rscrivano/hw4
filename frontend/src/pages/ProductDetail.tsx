import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, money, Product } from '../api'
import { useAuth } from '../auth'
import { useCart, visitorId } from '../cart'
import Recommendations from '../components/Recommendations'
import { flyToCart } from '../fx'
import { ErrorBox, Loading } from '../components/Status'

function stockLabel(q: number) {
  if (q === 0) return 'Sold out'
  if (q <= 5) return `Only ${q} left`
  return `${q} in stock`
}

export default function ProductDetail() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState('')
  const [size, setSize] = useState('')
  const [qty, setQty] = useState(1)
  const [added, setAdded] = useState('')
  const { token, ready } = useAuth()
  const cart = useCart()
  const imageRef = useRef<HTMLImageElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    setProduct(null)
    setError('')
    setSize('')
    setQty(1)
    setAdded('')
    api.product(productId).then(setProduct).catch(e => setError(e.message))
  }, [productId])

  // Click history (Problem 9): every product page a shopper opens is recorded for recommendations.
  useEffect(() => {
    if (ready && productId) api.recordView(productId, visitorId(), token)
  }, [ready, productId]) // eslint-disable-line react-hooks/exhaustive-deps

  if (error) {
    return (
      <section className="section">
        <ErrorBox message={error} />
        <Link to="/products" className="link">← Back to products</Link>
      </section>
    )
  }
  if (!product) return <section className="section"><Loading label="Loading product…" /></section>

  const selected = product.inventory.find(s => s.size === size)
  const inCart = cart.lines.find(l => l.product_id === product.product_id && l.size === size)?.quantity ?? 0
  const canAdd = !!selected && selected.quantity - inCart >= qty

  function addToCart() {
    if (!product || !selected) return
    cart.add({ product_id: product.product_id, name: product.name, price: product.price,
      image_url: product.image_url, size: selected.size, quantity: qty })
    setAdded(`Added ${qty} × size ${selected.size} to your cart.`)
    // Problem 10: a bubble with the product photo flies into the cart icon. Start from the photo
    // if it's on screen, otherwise from the button.
    const img = imageRef.current?.getBoundingClientRect()
    const imgVisible = img && img.bottom > 80 && img.top < window.innerHeight
    flyToCart(product.image_url, imgVisible ? imageRef.current : buttonRef.current)
  }

  return (
    <section className="section">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/products">Products</Link> /{' '}
        <Link to={`/products?category=${encodeURIComponent(product.category)}`}>{product.category}</Link> /{' '}
        <span>{product.name}</span>
      </nav>

      <div className="detail">
        <div className="detail-img">
          <img ref={imageRef} src={product.image_url} alt={product.name} />
        </div>

        <div className="detail-info">
          <p className="eyebrow">{product.category}</p>
          <h1>{product.name}</h1>
          <p className="price big">{money(product.price)}</p>
          <p className="lead">{product.description}</p>

          <h2 className="label">Colors</h2>
          <div className="tags">
            {product.colors.map(c => <span key={c} className="tag">{c}</span>)}
          </div>

          <h2 className="label">Sizes &amp; stock</h2>
          <div className="sizes" role="radiogroup" aria-label="Choose a size">
            {product.inventory.map(s => (
              <button
                key={s.size}
                role="radio"
                aria-checked={size === s.size}
                className={`size ${size === s.size ? 'active' : ''} ${s.quantity === 0 ? 'out' : ''}`}
                disabled={s.quantity === 0}
                onClick={() => setSize(s.size)}
              >
                <strong>{s.size}</strong>
                <small>{stockLabel(s.quantity)}</small>
              </button>
            ))}
          </div>
          <p className="muted">
            {selected
              ? `Size ${selected.size}: ${stockLabel(selected.quantity).toLowerCase()}.`
              : `${product.total_stock} units in stock across all sizes.`}
          </p>

          <div className="add-to-cart">
            <label>
              <span className="sr-only">Quantity</span>
              <select value={qty} onChange={e => setQty(Number(e.target.value))} disabled={!selected}>
                {Array.from({ length: Math.max(1, Math.min(10, (selected?.quantity ?? 1) - inCart)) }, (_, i) => i + 1).map(n => (
                  <option key={n} value={n}>Qty {n}</option>
                ))}
              </select>
            </label>
            <button ref={buttonRef} className="btn" onClick={addToCart} disabled={!canAdd}>
              🛒 {selected ? 'Add to cart' : 'Pick a size to add to cart'}
            </button>
          </div>
          {selected && inCart > 0 && selected.quantity - inCart < 1 && (
            <p className="muted small">You already have all {selected.quantity} in size {selected.size} in your cart.</p>
          )}
          {added && (
            <p className="status ok" role="status">
              ✓ {added} <Link to="/cart" className="link">View cart →</Link>
            </p>
          )}

          <h2 className="label">Details</h2>
          <ul className="details-list">
            <li>Style: {product.garment_type}</li>
            <li>Item #: {product.product_id}</li>
            <li>Tags: {product.search_tags.join(', ')}</li>
          </ul>

          <Link to="/products" className="link">← Back to all products</Link>
        </div>
      </div>
      <Recommendations exclude={[product.product_id]} title="You might also like" />
    </section>
  )
}
