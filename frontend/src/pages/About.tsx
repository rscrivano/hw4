import HandsomeDan from '../components/HandsomeDan'
import { Link } from 'react-router-dom'

export default function About() {
  return (
    <section className="section narrow">
      <div className="about-hero">
        <div>
          <p className="eyebrow">About Us</p>
          <h1>
            More than a campus store. <span className="accent">A global one.</span>
          </h1>
        </div>
        <HandsomeDan size={150} />
      </div>

      <p className="lead">
        We are not just a campus store, but rather a store that is vibrant and multicultural, gathering designs
        inspired by cultures from around the globe. With Yale being a multinational institution with students from
        across the world, we want to ensure our branding and store merchandise collectively bring together designs
        from a diverse range of cultures and appeal to our students, their families and our alumni.
      </p>

      <div className="about-grid">
        <div className="card pad">
          <h3>Bulldog pride, worldwide</h3>
          <p className="muted">
            From residential college crewnecks to varsity hoodies, every piece celebrates the Yale community, wherever
            home happens to be.
          </p>
        </div>
        <div className="card pad">
          <h3>Officially licensed</h3>
          <p className="muted">
            Our apparel carries authentic Yale marks, so what you wear on campus, at The Game or back home is the
            real thing.
          </p>
        </div>
        <div className="card pad">
          <h3>For the whole family</h3>
          <p className="muted">
            Students, parents, aunts, uncles and alumni all deserve casual comfort and classic Bulldog spirit.
          </p>
        </div>
      </div>

      <div className="card pad visit">
        <h3>Visit us</h3>
        <p>57 Broadway, New Haven, CT 06511</p>
        <Link to="/products" className="btn">Browse the collection</Link>
      </div>
    </section>
  )
}
