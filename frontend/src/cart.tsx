import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react'

/*
 * Shopping cart (Problem 9). Kept in localStorage so it works for guests and survives reloads.
 * It only remembers WHAT the shopper picked; prices and stock are always re-checked by the
 * server (/api/cart/quote) on the Cart page and again at checkout.
 */

export interface CartLine {
  product_id: string
  name: string
  price: number // display only, re-priced by the server
  image_url: string
  size: string
  quantity: number
}

const KEY = 'cc_cart'
const MAX_QTY = 10

function load(): CartLine[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '[]') as CartLine[]
  } catch {
    return []
  }
}

interface CartState {
  lines: CartLine[]
  count: number
  add: (line: CartLine) => void
  setQuantity: (productId: string, size: string, quantity: number) => void
  remove: (productId: string, size: string) => void
  clear: () => void
}

const Ctx = createContext<CartState | null>(null)

export function CartProvider({ children }: { children: ReactNode }) {
  const [lines, setLines] = useState<CartLine[]>(load)

  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(lines))
    } catch {
      /* storage blocked: cart lasts for this page view only */
    }
  }, [lines])

  const add = useCallback((line: CartLine) => {
    setLines(ls => {
      const i = ls.findIndex(l => l.product_id === line.product_id && l.size === line.size)
      if (i === -1) return [...ls, { ...line, quantity: Math.min(line.quantity, MAX_QTY) }]
      const next = [...ls]
      next[i] = { ...next[i], quantity: Math.min(next[i].quantity + line.quantity, MAX_QTY) }
      return next
    })
  }, [])

  const setQuantity = useCallback((productId: string, size: string, quantity: number) => {
    setLines(ls =>
      ls.map(l => (l.product_id === productId && l.size === size ? { ...l, quantity: Math.max(1, Math.min(quantity, MAX_QTY)) } : l)),
    )
  }, [])

  const remove = useCallback((productId: string, size: string) => {
    setLines(ls => ls.filter(l => !(l.product_id === productId && l.size === size)))
  }, [])

  const clear = useCallback(() => setLines([]), [])

  const count = lines.reduce((n, l) => n + l.quantity, 0)
  return <Ctx.Provider value={{ lines, count, add, setQuantity, remove, clear }}>{children}</Ctx.Provider>
}

export function useCart() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useCart must be used inside <CartProvider>')
  return ctx
}

/** Anonymous id for this browser, so a guest's product clicks can power recommendations. */
export function visitorId(): string | null {
  try {
    let id = localStorage.getItem('cc_visitor')
    if (!id) {
      id = crypto.randomUUID()
      localStorage.setItem('cc_visitor', id)
    }
    return id
  } catch {
    return null
  }
}
