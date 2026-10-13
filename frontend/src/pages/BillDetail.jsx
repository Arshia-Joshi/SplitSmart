import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api, formatDate, money } from '../api'

function shareText(bill) {
  const lines = [`${bill.restaurant_name} - ${money(bill.total)}`, '']
  bill.people.forEach((p) => lines.push(`${p.name}: ${money(p.total)}`))
  lines.push('', 'Split with SplitSmart')
  return lines.join('\n')
}

export default function BillDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [bill, setBill] = useState(null)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)
  const [open, setOpen] = useState({})

  useEffect(() => {
    api(`/bills/${id}`).then((d) => setBill(d.bill)).catch((e) => setError(e.message))
  }, [id])

  const share = async () => {
    const text = shareText(bill)
    if (navigator.share) {
      try { await navigator.share({ text }); return } catch { /* cancelled, fall back to copy */ }
    }
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setError('Could not copy, please copy manually')
    }
  }

  const remove = async () => {
    if (!confirm('Delete this bill?')) return
    try {
      await api(`/bills/${id}`, { method: 'DELETE' })
      navigate('/bills', { replace: true })
    } catch (e) {
      setError(e.message)
    }
  }

  if (error) return <div className="container section"><div className="alert alert-error">{error}</div><Link to="/bills">Back to history</Link></div>
  if (!bill) return <div className="page-loading"><div className="spinner" /></div>

  return (
    <div className="container narrow section">
      {location.state?.justSaved && <div className="alert alert-success">Split saved!</div>}
      <Link to="/bills" className="back">← History</Link>

      <div className="card panel detail-head">
        <div>
          <h1>{bill.restaurant_name}</h1>
          <p className="muted">{formatDate(bill.created_at)}</p>
        </div>
        <div className="detail-total">{money(bill.total)}</div>
      </div>

      <div className="sum-lines card panel">
        <div><span>Items</span><span>{money(bill.items_total)}</span></div>
        {bill.charges.map((c, i) => <div key={i}><span>{c.name}</span><span>{money(c.amount)}</span></div>)}
        {bill.discount > 0 && <div><span>Discount</span><span>−{money(bill.discount)}</span></div>}
        <div className="sum-total"><span>Total</span><span>{money(bill.total)}</span></div>
      </div>

      <h2>Who pays what</h2>
      <div className="people-cards">
        {bill.people.map((p, i) => (
          <div className="card person-card" key={i}>
            <button className="person-card-head" onClick={() => setOpen({ ...open, [i]: !open[i] })} aria-expanded={!!open[i]}>
              <div className={`avatar c${i % 6}`}>{p.name[0].toUpperCase()}</div>
              <div className="grow">
                <strong>{p.name}</strong>
                <small className="muted">{p.items.length} item{p.items.length === 1 ? '' : 's'}</small>
              </div>
              <strong className="person-total">{money(p.total)}</strong>
              <span className={`chev ${open[i] ? 'up' : ''}`} aria-hidden="true">⌄</span>
            </button>
            {open[i] && (
              <div className="person-items">
                {p.items.map((it, j) => (
                  <div key={j}>
                    <span>{it.name}{it.shared_with > 1 && <small className="muted"> (1/{it.shared_with})</small>}</span>
                    <span>{money(it.share)}</span>
                  </div>
                ))}
                {p.extras !== 0 && <div><span>Taxes &amp; charges share</span><span>{money(p.extras)}</span></div>}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="detail-actions">
        <button className="btn btn-primary" onClick={share}>{copied ? 'Copied!' : 'Share split'}</button>
        <Link to="/new" className="btn btn-ghost">New bill</Link>
        <button className="btn btn-danger-ghost" onClick={remove}>Delete</button>
      </div>
    </div>
  )
}
