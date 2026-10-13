import { Link } from 'react-router-dom'

const steps = [
  { n: 1, title: 'Snap the bill', text: 'Upload or take a photo. AI reads the items, taxes and total for you.' },
  { n: 2, title: 'Tick who had what', text: 'Tap names next to each item. Shared dishes are divided automatically.' },
  { n: 3, title: 'Share the split', text: 'Everyone sees exactly what they owe, down to the paisa. Send it on WhatsApp.' },
]

export default function Landing() {
  return (
    <>
      <section className="hero">
        <div className="container hero-inner">
          <div>
            <span className="pill">Free · No more calculator at the table</span>
            <h1>Split bills <span className="grad">effortlessly</span></h1>
            <p className="lead">
              Upload your receipt and let SplitSmart handle the maths. Fair shares for shared
              dishes, taxes split evenly, and totals that always add up.
            </p>
            <div className="hero-cta">
              <Link to="/signup" className="btn btn-primary btn-lg">Get started free</Link>
              <Link to="/login" className="btn btn-ghost btn-lg">I have an account</Link>
            </div>
          </div>

          <div className="hero-card card" aria-hidden="true">
            <div className="hero-card-head">
              <strong>Cafe Mocha</strong><span className="muted">₹1,260.00</span>
            </div>
            {[['Asha', 'Pasta, ½ Nachos', '₹472.50'], ['Ravi', 'Burger, ½ Nachos', '₹417.50'], ['Meera', 'Salad, Coffee', '₹370.00']].map(([n, i, t]) => (
              <div className="hero-row" key={n}>
                <div className="avatar">{n[0]}</div>
                <div className="grow"><div>{n}</div><small className="muted">{i}</small></div>
                <strong>{t}</strong>
              </div>
            ))}
            <div className="hero-foot muted">GST ₹60 split equally · adds up to the paisa</div>
          </div>
        </div>
      </section>

      <section className="container section">
        <h2 className="center">How it works</h2>
        <div className="steps">
          {steps.map((s) => (
            <div className="card step" key={s.n}>
              <div className="step-n">{s.n}</div>
              <h3>{s.title}</h3>
              <p className="muted">{s.text}</p>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}
