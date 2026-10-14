import { createContext, ReactNode, useCallback, useContext, useState } from 'react'
import { PageResults } from './api'

/*
 * Shared store for the chat's on-page search results (Problem 7).
 * ChatWidget writes the latest `page_results` from /api/chat here; ChatResults reads it and
 * renders the product cards at the top of the page. Saved to sessionStorage so the results are
 * still there after a shopper opens a product's detail page and comes back.
 */

const KEY = 'cc_page_results'

interface Stored {
  results: PageResults
  id: number // changes on every new search, so the page can scroll to and animate fresh results
}

function load(): Stored | null {
  try {
    const raw = sessionStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as Stored) : null
  } catch {
    return null
  }
}

function save(value: Stored | null) {
  try {
    if (value) sessionStorage.setItem(KEY, JSON.stringify(value))
    else sessionStorage.removeItem(KEY)
  } catch {
    /* storage blocked: results last for this page view only */
  }
}

interface PageResultsState {
  current: Stored | null
  show: (results: PageResults) => void
  clear: () => void
}

const Ctx = createContext<PageResultsState | null>(null)

export function PageResultsProvider({ children }: { children: ReactNode }) {
  const [current, setCurrent] = useState<Stored | null>(load)

  const show = useCallback((results: PageResults) => {
    const next = { results, id: Date.now() }
    save(next)
    setCurrent(next)
  }, [])

  const clear = useCallback(() => {
    save(null)
    setCurrent(null)
  }, [])

  return <Ctx.Provider value={{ current, show, clear }}>{children}</Ctx.Provider>
}

export function usePageResults() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('usePageResults must be used inside <PageResultsProvider>')
  return ctx
}
