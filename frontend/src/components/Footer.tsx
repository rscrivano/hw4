import HandsomeDan from './HandsomeDan'
import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <HandsomeDan face size={52} title="" />
          <div>
            <strong>Campus Customs</strong>
            <p>Bulldog pride, designed with the world in mind.</p>
          </div>
        </div>
        <div>
          <strong>Visit us</strong>
          <p>57 Broadway, New Haven, CT 06511</p>
        </div>
        <div>
          <strong>Shop</strong>
          <p>
            <Link to="/products">All products</Link> · <Link to="/about">About us</Link> · <Link to="/track">Track an order</Link>
          </p>
        </div>
      </div>
      <p className="footer-note">© {new Date().getFullYear()} Campus Customs · Mgmt 409 class project</p>
    </footer>
  )
}
