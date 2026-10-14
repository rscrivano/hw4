import { Link } from 'react-router-dom'
import { money, Product, ProductCard as ChatCard, shortText } from '../api'

/**
 * One product card, used everywhere: the Products page, the home page and the chat's
 * on-page search results. It accepts a full catalogue Product or the lighter card the
 * chat API returns; either way it links to the single-item page /products/:id.
 */
export default function ProductCard({ product }: { product: Product | ChatCard }) {
  const isCatalogue = 'inventory' in product
  const info = isCatalogue ? shortText(product.description) : product.short_description
  const soldOutSizes = isCatalogue
    ? product.inventory.filter(s => s.quantity === 0).length
    : product.stock.filter(s => s.status === 'sold out').length
  return (
    <Link to={`/products/${product.product_id}`} className="card product-card">
      <div className="product-img">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        <span className="chip">{product.category}</span>
      </div>
      <div className="product-info">
        <h3>{product.name}</h3>
        <p className="price">{money(product.price)}</p>
        <p className="muted">{info}</p>
        {soldOutSizes > 0 && (
          <p className="stock-note">{soldOutSizes} size{soldOutSizes > 1 ? 's' : ''} sold out</p>
        )}
      </div>
    </Link>
  )
}
