import HandsomeDan from './HandsomeDan'
import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { useCart } from '../cart'
import { bark, setSoundOn, soundOn } from '../fx'

const LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const [open, setOpen] = useState(false)
  const [wiggle, setWiggle] = useState(0) // bumping the key restarts the wiggle animation
  const [sound, setSound] = useState(soundOn)
  const close = () => setOpen(false)
  const { user, ready, signOut } = useAuth()
  const { count } = useCart()
  const navigate = useNavigate()

  function logOut() {
    signOut()
    close()
    navigate('/')
  }

  return (
    <header className="nav">
      <div className="nav-inner">
        <Link
          to="/"
          className="brand"
          aria-label="Campus Customs home"
          onClick={() => {
            close()
            bark() // Handsome Dan says hi on the way home (Problem 10)
            setWiggle(w => w + 1)
          }}
        >
          <span key={wiggle} className={`brand-mark ${wiggle ? 'wiggle' : ''}`} aria-hidden>
            <HandsomeDan face size={38} title="" />
          </span>
          <span>
            Campus Customs
            <small>Officially licensed Yale apparel</small>
          </span>
        </Link>

        <button
          className="sound-toggle"
          aria-pressed={sound}
          aria-label={sound ? 'Mute site sounds' : 'Turn site sounds on'}
          title={sound ? 'Sounds on (click to mute)' : 'Sounds off'}
          onClick={() => {
            setSoundOn(!sound)
            setSound(!sound)
          }}
        >
          {sound ? '🔊' : '🔇'}
        </button>
        {/* Phones: the cart stays visible outside the collapsed menu */}
        <Link to="/cart" className="cart-mobile" onClick={close} aria-label={`Cart, ${count} item${count === 1 ? '' : 's'}`}>
          🛒
          {count > 0 && <span className="cart-badge">{count}</span>}
        </Link>
        <button
          className="nav-toggle"
          aria-label="Toggle navigation"
          aria-expanded={open}
          onClick={() => setOpen(o => !o)}
        >
          ☰
        </button>

        <nav className={`nav-links ${open ? 'open' : ''}`} aria-label="Main">
          {LINKS.map(l => (
            <NavLink key={l.to} to={l.to} end={l.end} onClick={close}>
              {l.label}
            </NavLink>
          ))}
          <NavLink to="/cart" className="cart-link" onClick={close} aria-label={`Cart, ${count} item${count === 1 ? '' : 's'}`}>
            🛒 Cart
            {count > 0 && <span className="cart-badge">{count}</span>}
          </NavLink>
          {ready && user ? (
            <>
              <span className="nav-user" title={user.email}>Hi, {user.first_name}</span>
              <button className="btn btn-small btn-ghost" onClick={logOut}>Log out</button>
            </>
          ) : (
            <>
              <NavLink to="/login" onClick={close}>Log in</NavLink>
              <NavLink to="/register" className="btn btn-small" onClick={close}>
                Create account
              </NavLink>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
