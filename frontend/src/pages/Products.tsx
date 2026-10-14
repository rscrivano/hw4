import HandsomeDan from '../components/HandsomeDan'
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, Product } from '../api'
import ProductCard from '../components/ProductCard'
import { ErrorBox, Loading } from '../components/Status'

export default function Products() {
  const [params, setParams] = useSearchParams()
  const category = params.get('category') ?? ''
  // ?ids=a,b,c comes from the chat's "Show these on the page" button (Handsome Dan's picks).
  const picks = useMemo(() => (params.get('ids') ?? '').split(',').filter(Boolean), [params])
  const [all, setAll] = useState<Product[] | null>(null)
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.products().then(setAll).catch(e => setError(e.message))
  }, [])

  const categories = useMemo(
    () => Array.from(new Set((all ?? []).map(p => p.category))),
    [all],
  )

  const visible = useMemo(() => {
    const words = query.toLowerCase().split(/\s+/).filter(Boolean)
    const pool = picks.length
      ? picks.map(id => (all ?? []).find(p => p.product_id === id)).filter((p): p is Product => !!p)
      : all ?? []
    return pool.filter(p => {
      if (category && p.category !== category) return false
      const hay = [p.name, p.description, p.category, ...p.colors, ...p.search_tags].join(' ').toLowerCase()
      return words.every(w => hay.includes(w))
    })
  }, [all, category, query, picks])

  const pick = (c: string) => setParams(c ? { category: c } : {})

  return (
    <section className="section">
      <div className="section-head">
        <div>
          <h1>Products</h1>
          <p className="muted">Officially licensed Yale apparel. Click any item for sizes and stock.</p>
        </div>
        <label className="search">
          <span className="sr-only">Search products</span>
          <input
            type="search"
            placeholder="Search: navy, hockey, bulldog…"
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
        </label>
      </div>

      <div className="filters" role="group" aria-label="Filter by category">
        <button className={!category ? 'active' : ''} onClick={() => pick('')}>All</button>
        {categories.map(c => (
          <button key={c} className={c === category ? 'active' : ''} onClick={() => pick(c)}>{c}</button>
        ))}
      </div>

      {picks.length > 0 && (
        <div className="picks-banner" role="status">
          <HandsomeDan face size={44} title="" />
          <p>
            <strong>Handsome Dan's picks</strong> from your chat · {picks.length} item{picks.length > 1 ? 's' : ''}
          </p>
          <button className="btn btn-small btn-ghost" onClick={() => setParams({})}>Show all products</button>
        </div>
      )}

      {error && <ErrorBox message={error} />}
      {!all && !error && <Loading label="Loading products…" />}
      {all && (
        <p className="muted result-count">
          Showing {visible.length} of {all.length} products
        </p>
      )}
      {all && visible.length === 0 && <p className="status">No products match that search.</p>}

      <div className="product-grid">
        {visible.map(p => <ProductCard key={p.product_id} product={p} />)}
      </div>
    </section>
  )
}
