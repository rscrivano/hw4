// Thin client for the FastAPI backend (proxied by Vite in development).

export interface SizeStock {
  size: string
  quantity: number
}

export interface Product {
  product_id: string
  name: string
  garment_type: string
  category: string
  description: string
  colors: string[]
  search_tags: string[]
  image_url: string
  price: number
  inventory: SizeStock[]
  total_stock: number
}

export interface Category {
  name: string
  count: number
  min_price: number
  max_price: number
  image_url: string
}

export interface User {
  id: number
  first_name: string
  last_name: string
  name: string
  email: string
}

export interface Session {
  token: string
  user: User
}

export interface RegisterInput {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export type StockStatus = 'in stock' | 'low stock' | 'sold out'

export interface SizeStatus {
  size: string
  quantity: number
  status: StockStatus
}

/** Product card built by the backend from the database (the agent only picks product_ids). */
export interface ProductCard {
  product_id: string
  name: string
  category: string
  price: number
  image_url: string
  short_description: string
  colors: string[]
  sizes_in_stock: string[]
  total_stock: number
  stock: SizeStatus[]
}

/** API contract: chat search matches the website renders as product cards on the page. */
export interface PageResults {
  title: string
  total_matches: number
  category: string | null
  products: ProductCard[]
}

/** Database lookups the agent ran for this reply (shown as small badges). */
export type Checked =
  | 'live stock'
  | 'catalogue prices'
  | 'product details'
  | 'catalogue search'
  | 'your account'
  | 'your browsing history'

/** What the shopper is looking at when they send a chat message (Problem 8). */
export interface PageContext {
  path: string
  product_id?: string | null
  category?: string | null
  results_title?: string | null
}

export interface ChatResponse {
  reply: string
  products: ProductCard[]
  page_results: PageResults | null
  focus_size: string | null
  suggestions: string[]
  checked: Checked[]
}

export interface ChatHistoryMessage {
  role: 'user' | 'assistant'
  content: string
  products: ProductCard[]
  created_at: string
}

// ---- Problem 9: cart, checkout, click history, recommendations

function visitorId(): string | null {
  try {
    return localStorage.getItem('cc_visitor')
  } catch {
    return null
  }
}

export interface CartItemInput {
  product_id: string
  size: string
  quantity: number
}

export interface QuoteLine extends CartItemInput {
  name: string
  unit_price: number
  line_total: number
  image_url: string
  available: number
  issue: string | null
}

export interface Quote {
  lines: QuoteLine[]
  subtotal: number
  item_count: number
  ok: boolean
  problems: string[]
}

export type PaymentMethod = 'card_at_pickup' | 'cash_at_pickup' | 'card_on_delivery' | 'cash_on_delivery'

export interface OrderInput {
  items: CartItemInput[]
  customer_name: string
  email: string
  phone?: string
  fulfillment: 'pickup' | 'ship'
  shipping_address?: string
  payment_method: PaymentMethod | null
}

export interface TrackedOrder {
  order_number: string
  placed_at: string
  status: string
  customer_name: string
  fulfillment: 'pickup' | 'ship'
  payment_method: string
  payment_status: string
  subtotal: number
  items: { product_id: string; name: string; size: string; quantity: number; unit_price: number; line_total: number }[]
  timeline: { step: string; done: boolean; at: string | null }[]
}

export interface OrderResult {
  order_number: string
  subtotal: number
  guest: boolean
  payment_method: string
  payment_status: string
  items: (CartItemInput & { name: string; unit_price: number; line_total: number })[]
}

export interface Recommendations {
  reason: string
  products: ProductCard[]
}

const bearer = (token?: string | null): Record<string, string> =>
  token ? { Authorization: `Bearer ${token}` } : {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : detail
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  categories: () => request<Category[]>('/api/categories'),
  products: (params: { category?: string; q?: string; ids?: string } = {}) => {
    const qs = new URLSearchParams()
    if (params.category) qs.set('category', params.category)
    if (params.q) qs.set('q', params.q)
    if (params.ids) qs.set('ids', params.ids)
    const s = qs.toString()
    return request<Product[]>(`/api/products${s ? `?${s}` : ''}`)
  },
  product: (id: string) => request<Product>(`/api/products/${encodeURIComponent(id)}`),
  register: (input: RegisterInput) =>
    request<Session>('/api/auth/register', { method: 'POST', body: JSON.stringify(input) }),
  login: (email: string, password: string) =>
    request<Session>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  me: (token: string) => request<User>('/api/auth/me', { headers: bearer(token) }),
  // Guests can chat; with a token the conversation is saved to the shopper's account.
  // Logged-in shoppers' history is loaded from the database by the server, so it isn't sent.
  chat: (message: string, history: ChatTurn[], token?: string | null, page?: PageContext) =>
    request<ChatResponse>('/api/chat', {
      method: 'POST',
      headers: bearer(token),
      body: JSON.stringify({ message, history: token ? [] : history, page, visitor_id: visitorId() }),
    }),
  quote: (items: CartItemInput[]) =>
    request<Quote>('/api/cart/quote', { method: 'POST', body: JSON.stringify({ items }) }),
  placeOrder: (order: OrderInput, token?: string | null) =>
    request<OrderResult>('/api/orders', { method: 'POST', headers: bearer(token), body: JSON.stringify(order) }),
  trackOrder: (order_number: string, contact: string) =>
    request<TrackedOrder>(
      `/api/orders/track?${new URLSearchParams({ order_number: order_number.trim(), contact: contact.trim() })}`,
    ),
  recordView: (product_id: string, visitor_id: string | null, token?: string | null) =>
    fetch('/api/events/view', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...bearer(token) },
      body: JSON.stringify({ product_id, visitor_id, source: 'product_page' }),
    }).catch(() => undefined), // tracking must never break the page
  recommendations: (visitor_id: string | null, exclude: string[], token?: string | null, limit = 4) => {
    const qs = new URLSearchParams({ exclude: exclude.join(','), limit: String(limit) })
    if (visitor_id) qs.set('visitor_id', visitor_id)
    return request<Recommendations>(`/api/recommendations?${qs}`, { headers: bearer(token) })
  },
  chatHistory: (token: string) => request<ChatHistoryMessage[]>('/api/chat/history', { headers: bearer(token) }),
}

export const money = (n: number) => `$${n.toFixed(2)}`

export function shortText(text: string, max = 110) {
  if (text.length <= max) return text
  return text.slice(0, text.lastIndexOf(' ', max)) + '…'
}
