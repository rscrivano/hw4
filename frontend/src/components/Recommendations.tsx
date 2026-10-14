import { useEffect, useState } from 'react'
import { api, Recommendations as Recs } from '../api'
import { useAuth } from '../auth'
import { visitorId } from '../cart'
import HandsomeDan from './HandsomeDan'
import ProductCard from './ProductCard'

/**
 * "Picked for you": products chosen from the shopper's click history (product_views table).
 * With no history yet it shows what's popular. `exclude` hides the product being viewed.
 */
export default function Recommendations({ exclude = [], title }: { exclude?: string[]; title?: string }) {
  const { token, ready } = useAuth()
  const [recs, setRecs] = useState<Recs | null>(null)
  const key = exclude.join(',')

  useEffect(() => {
    if (!ready) return
    api.recommendations(visitorId(), exclude, token).then(setRecs).catch(() => setRecs(null))
  }, [ready, token, key]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!recs || !recs.products.length) return null
  return (
    <section className="section recommendations" aria-label="Recommended for you">
      <div className="section-head">
        <div className="rec-head">
          <HandsomeDan face size={40} title="" />
          <div>
            <h2>{title ?? 'Picked for you'}</h2>
            <p className="muted small">{recs.reason}</p>
          </div>
        </div>
      </div>
      <div className="product-grid">
        {recs.products.map(p => <ProductCard key={p.product_id} product={p} />)}
      </div>
    </section>
  )
}
