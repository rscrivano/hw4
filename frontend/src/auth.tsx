import { createContext, ReactNode, useContext, useEffect, useState } from 'react'
import { api, Session, User } from './api'

// The token is a signed session ID from the backend, never the password.
const TOKEN_KEY = 'cc_token'

function readToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

function writeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* storage blocked: session lasts for this page view only */
  }
}

interface AuthState {
  user: User | null
  token: string | null
  ready: boolean
  signIn: (session: Session) => void
  signOut: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(readToken)
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  // On page load, turn a saved token back into the logged-in user (or drop it if expired).
  useEffect(() => {
    if (!token) {
      setReady(true)
      return
    }
    api
      .me(token)
      .then(setUser)
      .catch(() => {
        writeToken(null)
        setToken(null)
      })
      .finally(() => setReady(true))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const signIn = (session: Session) => {
    writeToken(session.token)
    setToken(session.token)
    setUser(session.user)
  }

  const signOut = () => {
    writeToken(null)
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, ready, signIn, signOut }}>{children}</AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
