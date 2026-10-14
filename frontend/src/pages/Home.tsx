import HandsomeDan from '../components/HandsomeDan'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, Category, money, Product } from '../api'
import ProductCard from '../components/ProductCard'
import Recommendations from '../components/Recommendations'
import { ErrorBox, Loading } from '../components/Status'

const BLURBS: Record<string, string> = {
  'T-Shirts': 'Everyday tees for game day, The Game and every day in between.',
  Crewnecks: 'Classic crewnecks for residential college and varsity pride.',
  Hoodies: 'Cozy pullovers for late nights in the library and cold New Haven mornings.',
  'Quarter-Zips': 'Polished layers that go from class to the office.',
  'Full-Zip Hoodies': 'Easy zip-up warmth with Bulldog style.',
  'Jackets & Fleece': 'Our warmest layers: fleece, sweater-fleece and bomber jackets.',
  'Performance Long Sleeves': 'Lightweight technical pieces for training and game day.',
}

export default function Home() {
  const [categories, setCategories] = useState<Category[] | null>(null)
  const [featured, setFeatured] = useState<Product[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.categories(), api.products()])
      .then(([cats, products]) => {
        setCategories(cats)
        // One product from each category, so the home page shows the whole range.
        const seen = new Set<string>()
        setFeatured(products.filter(p => !seen.has(p.category) && seen.add(p.category)).slice(0, 4))
      })
      .catch(e => setError(e.message))
  }, [])

  return (
    <>
      <section className="hero">
        <div className="hero-text">
          <p className="eyebrow">Officially licensed · New Haven, CT</p>
          <h1>
            Big Spirit. <span>Big Yale.</span>
          </h1>
          <p className="lead">
            Casual comfort and classic Bulldog pride for students, families and alumni. Find your college colors,
            your team and your next favorite hoodie, all in one place.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="btn">Shop all products</Link>
            <Link to="/about" className="btn btn-ghost">Our story</Link>
          </div>
        </div>
        <div className="hero-art">
          <span className="confetti c1" aria-hidden />
          <span className="confetti c2" aria-hidden />
          <span className="confetti c3" aria-hidden />
          <span className="confetti c4" aria-hidden />
          <span className="speech">Woof! Boola Boola!</span>
          <HandsomeDan className="dan" size={320} />
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Shop by category</h2>
          <p className="muted">Everything we carry, grouped the way you shop.</p>
        </div>
        {error && <ErrorBox message={error} />}
        {!categories && !error && <Loading label="Loading categories…" />}
        <div className="category-grid">
          {categories?.map(c => (
            <Link
              key={c.name}
              to={`/products?category=${encodeURIComponent(c.name)}`}
              className="card category-card"
            >
              <img src={c.image_url} alt="" loading="lazy" />
              <div>
                <h3>{c.name}</h3>
                <p className="muted">{BLURBS[c.name] ?? 'Bulldog favorites.'}</p>
                <p className="meta">
                  {c.count} styles ·{' '}
                  {c.min_price === c.max_price ? money(c.min_price) : `${money(c.min_price)}–${money(c.max_price)}`}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {featured.length > 0 && (
        <section className="section">
          <div className="section-head">
            <h2>Show your Bulldog pride</h2>
            <Link to="/products" className="link">View all →</Link>
          </div>
          <div className="product-grid">
            {featured.map(p => <ProductCard key={p.product_id} product={p} />)}
          </div>
        </section>
      )}

      <Recommendations />

      <section className="banner">
        <HandsomeDan face size={84} className="dan-face" title="" />
        <div>
          <h2>Need a hand finding the right fit?</h2>
          <p>Ask Handsome Dan, our shopping assistant in the bottom-right corner, about styles, colors, sizes and stock.</p>
        </div>
      </section>
    </>
  )
}
