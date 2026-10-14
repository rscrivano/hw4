import { FormEvent, ReactNode, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import HandsomeDan from './HandsomeDan'
import { api, ChatTurn, Checked, money, PageContext, ProductCard, SizeStatus } from '../api'
import { useAuth } from '../auth'
import { usePageResults } from '../pageResults'

interface Message extends ChatTurn {
  products?: ProductCard[]
  focusSize?: string | null
  suggestions?: string[]
  checked?: Checked[]
  pageTitle?: string // set when this reply put search results on the page
  pageCount?: number
  error?: boolean
}

const BADGE_TEXT: Record<Checked, string> = {
  'your browsing history': 'Based on what you viewed',
  'your account': 'Checked your account',
  'live stock': 'Checked live stock',
  'catalogue prices': 'Prices from our catalogue',
  'product details': 'Product details from our catalogue',
  'catalogue search': 'Searched our catalogue',
}

/** XS–XXL chips: green = in stock, amber = low (≤5), struck-through = sold out. The asked-about size is ringed. */
function SizeStrip({ stock, focus }: { stock: SizeStatus[]; focus?: string | null }) {
  if (!stock.length) return null
  return (
    <span className="size-strip" aria-label="Stock by size">
      {stock.map(s => (
        <span
          key={s.size}
          className={`size-chip ${s.status.replace(' ', '-')} ${focus === s.size ? 'focus' : ''}`}
          title={s.status === 'sold out' ? `${s.size}: sold out` : `${s.size}: ${s.quantity} left`}
        >
          {s.size}
          {s.status === 'low stock' && <b>{s.quantity}</b>}
          <span className="sr-only">
            {s.status === 'sold out' ? ' sold out' : s.status === 'low stock' ? ` only ${s.quantity} left` : ' in stock'}
          </span>
        </span>
      ))}
    </span>
  )
}

/** For the asked-about size: a one-line status right on the card, so a sold-out size can't be missed. */
function FocusLine({ stock, focus }: { stock: SizeStatus[]; focus: string }) {
  const s = stock.find(x => x.size === focus)
  if (!s) return null
  const text =
    s.status === 'sold out' ? `Size ${focus}: sold out` : s.status === 'low stock' ? `Size ${focus}: only ${s.quantity} left` : `Size ${focus}: in stock`
  return <small className={`focus-line ${s.status.replace(' ', '-')}`}>{text}</small>
}

const WELCOME: Message = {
  role: 'assistant',
  content: "Woof! I'm Handsome Dan, your Campus Customs shopping buddy. Ask me about hoodies, tees, sizes or colors.",
  suggestions: ['What hoodies do you have?', "What's your cheapest item?", 'Show me navy crewnecks'],
}

/** Renders the agent's light markdown (**bold** and "- " bullets) without injecting HTML. */
function RichText({ text }: { text: string }) {
  const inline = (line: string): ReactNode[] =>
    line.split(/(\*\*[^*]+\*\*)/g).map((chunk, i) =>
      chunk.startsWith('**') && chunk.endsWith('**') ? <strong key={i}>{chunk.slice(2, -2)}</strong> : chunk,
    )
  const blocks: ReactNode[] = []
  let bullets: string[] = []
  const flush = () => {
    if (bullets.length) blocks.push(<ul key={`u${blocks.length}`}>{bullets.map((b, i) => <li key={i}>{inline(b)}</li>)}</ul>)
    bullets = []
  }
  text.split('\n').forEach(raw => {
    const line = raw.trim()
    const bullet = line.match(/^[-*•]\s+(.*)/)
    if (bullet) return bullets.push(bullet[1])
    flush()
    if (line) blocks.push(<p key={`p${blocks.length}`}>{inline(line)}</p>)
  })
  flush()
  return <>{blocks}</>
}

export default function ChatWidget() {
  const { user, token, ready } = useAuth()
  const pageResults = usePageResults()
  const navigate = useNavigate()
  const location = useLocation()

  // Page context (Problem 8): which page/product the shopper is on, sent with every message so the
  // agent knows what "this" means. The server re-reads the product from the database.
  const viewingId = location.pathname.match(/^\/products\/([^/]+)$/)?.[1] ?? null
  const [viewingName, setViewingName] = useState<string | null>(null)
  useEffect(() => {
    setViewingName(null)
    if (viewingId) api.product(decodeURIComponent(viewingId)).then(p => setViewingName(p.name)).catch(() => {})
  }, [viewingId])
  const pageContext = (): PageContext => ({
    path: location.pathname,
    product_id: viewingId ? decodeURIComponent(viewingId) : null,
    category: new URLSearchParams(location.search).get('category'),
    results_title: pageResults.current?.results.title ?? null,
  })
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([WELCOME])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  // Logged-in shoppers get their saved conversation back; logging out resets to a fresh chat.
  useEffect(() => {
    if (!ready) return
    if (!token) {
      setMessages([WELCOME])
      return
    }
    api
      .chatHistory(token)
      .then(saved => {
        const greeting: Message = {
          ...WELCOME,
          content: `Woof, welcome back${user ? `, ${user.first_name}` : ''}! What can I help you find today?`,
        }
        setMessages([greeting, ...saved.map(m => ({ role: m.role, content: m.content, products: m.products }))])
      })
      .catch(() => setMessages([WELCOME]))
  }, [ready, token]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading, open])

  async function send(text: string) {
    text = text.trim()
    if (!text || loading) return
    const history: ChatTurn[] = messages
      .slice(1) // skip the greeting
      .filter(m => !m.error)
      .map(({ role, content }) => ({ role, content }))
    setMessages(m => [...m, { role: 'user', content: text }])
    setInput('')
    setLoading(true)
    try {
      const res = await api.chat(text, history, token, pageContext())
      // API contract: page_results -> product cards rendered on the page by <ChatResults />.
      if (res.page_results) pageResults.show(res.page_results)
      setMessages(m => [
        ...m,
        {
          role: 'assistant',
          content: res.reply,
          products: res.products,
          focusSize: res.focus_size,
          suggestions: res.suggestions,
          checked: res.checked,
          pageTitle: res.page_results?.title,
          pageCount: res.page_results?.products.length,
        },
      ])
    } catch (err) {
      setMessages(m => [...m, { role: 'assistant', content: (err as Error).message, error: true }])
    } finally {
      setLoading(false)
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    send(input)
  }

  const showOnPage = (cards: ProductCard[]) =>
    navigate(`/products?ids=${encodeURIComponent(cards.map(c => c.product_id).join(','))}`)

  // Close the panel (it covers the page on phones) and jump to the on-page results.
  const viewOnPage = () => {
    setOpen(false)
    setTimeout(() => document.querySelector('.chat-results')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
  }

  const last = messages[messages.length - 1]

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" role="dialog" aria-label="Shopping assistant">
          <header className="chat-head">
            <div className="who">
              <HandsomeDan face size={40} title="" />
              <div>
                <strong>Handsome Dan · Shop Assistant</strong>
                <small>{user ? `Chatting as ${user.first_name} · saved to your account` : 'Answers from our live catalogue'}</small>
              </div>
            </div>
            <div className="chat-head-actions">
              <button
                aria-label="Start a new chat"
                title="New chat"
                onClick={() => setMessages([WELCOME])}
                disabled={loading}
              >
                ↺
              </button>
              <button aria-label="Close chat" onClick={() => setOpen(false)}>✕</button>
            </div>
          </header>

          {viewingName && (
            <div className="chat-context" title="Handsome Dan knows which product you're looking at">
              <span aria-hidden>👀</span> Viewing: <strong>{viewingName}</strong> · ask "do you have this in…?"
            </div>
          )}

          <div className="chat-body" aria-live="polite">
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role} ${m.error ? 'error' : ''}`}>
                {m.role === 'assistant' ? <RichText text={m.content} /> : <p>{m.content}</p>}
                {m.pageTitle && (
                  <button className="chat-on-page" onClick={viewOnPage}>
                    <span aria-hidden>▦</span> {m.pageCount} {m.pageTitle.toLowerCase()} are on the page · View
                  </button>
                )}
                {m.checked && m.checked.length > 0 && (
                  <div className="checked-badges">
                    {m.checked.map(c => <span key={c}>✓ {BADGE_TEXT[c]}</span>)}
                  </div>
                )}
                {m.products && m.products.length > 0 && (
                  <div className="chat-products">
                    {m.products.map(p => (
                      <Link key={p.product_id} to={`/products/${p.product_id}`} className="chat-product">
                        <img src={p.image_url} alt="" />
                        <span>
                          {p.name}
                          <em>{money(p.price)}</em>
                          {m.focusSize && <FocusLine stock={p.stock} focus={m.focusSize} />}
                          <SizeStrip stock={p.stock} focus={m.focusSize} />
                        </span>
                      </Link>
                    ))}
                    {m.products.length > 1 && !m.pageTitle && (
                      <button className="chat-show" onClick={() => showOnPage(m.products!)}>
                        Show these on the page →
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="msg assistant typing" role="status">
                <p><span className="dots" aria-hidden><i /><i /><i /></span> Dan is checking the shelves…</p>
              </div>
            )}
            {!loading && last?.role === 'assistant' && last.suggestions && last.suggestions.length > 0 && (
              <div className="chat-suggestions">
                {last.suggestions.map(s => (
                  <button key={s} onClick={() => send(s)}>{s}</button>
                ))}
              </div>
            )}
            <div ref={endRef} />
          </div>

          <form className="chat-form" onSubmit={onSubmit}>
            <label htmlFor="chat-input" className="sr-only">Message</label>
            <input
              id="chat-input"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask about a product…"
              autoComplete="off"
              maxLength={1000}
            />
            <button className="btn" disabled={loading || !input.trim()}>Send</button>
          </form>
        </section>
      )}

      <button
        className={`chat-fab ${open ? 'is-open' : ''}`}
        aria-label={open ? 'Close chat' : 'Open chat'}
        aria-expanded={open}
        onClick={() => setOpen(o => !o)}
      >
        {open ? (
          '✕'
        ) : (
          <>
            <span className="fab-face"><HandsomeDan face size={36} title="" /></span>
            <span className="fab-label">Ask Handsome Dan</span>
          </>
        )}
      </button>
    </div>
  )
}
