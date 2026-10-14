import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import HandsomeDan from './HandsomeDan'
import ProductCard from './ProductCard'
import { usePageResults } from '../pageResults'

/**
 * "Handsome Dan found…" – the chat's search results rendered as product cards at the top of the
 * current page. Full grid on most pages. On a product's detail page it shrinks to a slim bar
 * (expandable to a scrolling strip) so the large image + full info stay in view.
 * Every card is the shared ProductCard, which opens /products/:id.
 */
export default function ChatResults() {
  const { current, clear } = usePageResults()
  const { pathname } = useLocation()
  const ref = useRef<HTMLElement>(null)
  const lastId = useRef<number | null>(current?.id ?? null)
  const [stripOpen, setStripOpen] = useState(false)
  useEffect(() => setStripOpen(false), [pathname]) // each detail page starts with the bar collapsed

  // Bring brand-new results into view (not when they're restored after navigating back).
  useEffect(() => {
    if (current && current.id !== lastId.current) {
      lastId.current = current.id
      ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [current])

  if (!current) return null
  // Keep cart, checkout and account pages focused: the results come back on any other page.
  if (/^\/(cart|checkout|order|track|login|register)(\/|$)/.test(pathname)) return null
  const { results, id } = current
  const compact = /^\/products\/[^/]+$/.test(pathname)

  if (compact && !stripOpen) {
    return (
      <div className="chat-results-bar" role="region" aria-label="Chat search results">
        <HandsomeDan face size={30} title="" />
        <span>
          Dan's results: <strong>{results.title}</strong> ({results.products.length})
        </span>
        <button className="btn btn-small btn-ghost" onClick={() => setStripOpen(true)} aria-expanded={false}>
          Show
        </button>
      </div>
    )
  }

  return (
    <section
      ref={ref}
      key={id}
      className={`chat-results ${compact ? 'compact' : ''}`}
      aria-label={`Chat search results: ${results.title}`}
    >
      <header className="chat-results-head">
        <HandsomeDan face size={48} title="" />
        <div className="chat-results-title">
          <p className="eyebrow">Handsome Dan found</p>
          <h2>{results.title}</h2>
          <p className="muted small">
            Showing {results.products.length} of {results.total_matches} · click any card for full details
          </p>
        </div>
        <div className="chat-results-actions">
          {results.category && results.total_matches > results.products.length && (
            <Link to={`/products?category=${encodeURIComponent(results.category)}`} className="btn btn-small">
              See all {results.total_matches}
            </Link>
          )}
          {compact && (
            <button className="btn btn-small btn-ghost" onClick={() => setStripOpen(false)} aria-expanded>
              Hide
            </button>
          )}
          <button className="btn btn-small btn-ghost" onClick={clear} aria-label="Clear chat results">
            Clear
          </button>
        </div>
      </header>

      <div className={compact ? 'chat-results-strip' : 'product-grid'}>
        {results.products.map((p, i) => (
          <div key={p.product_id} className="pop-in" style={{ animationDelay: `${Math.min(i, 11) * 40}ms` }}>
            <ProductCard product={p} />
          </div>
        ))}
      </div>
    </section>
  )
}
