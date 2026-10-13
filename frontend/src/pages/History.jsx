import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatDate, money } from '../api'

export default function History() {
  const [bills, setBills] = useState(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')

  useEffect(() => {
    api('/bills').then((d) => setBills(d.bills)).catch((e) => setError(e.message))
  }, [])

  const remove = async (bill) => {
    if (!confirm(`Delete the bill from ${bill.restaurant_name}?`)) return
    try {
      await api(`/bills/${bill.id}`, { method: 'DELETE' })
      setBills((bs) => bs.filter((b) => b.id !== bill.id))
    } catch (e) {
      setError(e.message)
    }
  }

  if (error) return <div className="container section"><div className="alert alert-error">{error}</div></div>
  if (!bills) return <div className="page-loading"><div className="spinner" /></div>

  const shown = bills.filter((b) => b.restaurant_name.toLowerCase().includes(query.toLowerCase()))
  const spent = bills.reduce((s, b) => s + b.total, 0)

  return (
    <div className="container section">
      <div className="history-head">
        <div>
          <h1>Bill history</h1>
          <p className="muted">{bills.length} bill{bills.length === 1 ? '' : 's'} · {money(spent)} split in total</p>
        </div>
        <Link to="/new" className="btn btn-primary">+ New bill</Link>
      </div>

      {bills.length === 0 ? (
        <div className="card empty">
          <h3>No bills yet</h3>
          <p className="muted">Split your first bill and it will show up here.</p>
          <Link to="/new" className="btn btn-primary">Split a bill</Link>
        </div>
      ) : (
        <>
          <input className="search" placeholder="Search by restaurant" value={query} onChange={(e) => setQuery(e.target.value)} />
          <div className="bill-list">
            {shown.map((b) => (
              <div className="card bill-row" key={b.id}>
                <Link to={`/bills/${b.id}`} className="bill-link">
                  <div className="bill-icon" aria-hidden="true">{b.restaurant_name[0].toUpperCase()}</div>
                  <div className="grow">
                    <strong>{b.restaurant_name}</strong>
                    <small className="muted">{formatDate(b.created_at)} · {b.people_count} people · {b.item_count} items</small>
                  </div>
                  <strong className="bill-total">{money(b.total)}</strong>
                </Link>
                <button className="icon-btn" onClick={() => remove(b)} aria-label={`Delete ${b.restaurant_name}`}>×</button>
              </div>
            ))}
            {shown.length === 0 && <p className="muted center">No bills match “{query}”.</p>}
          </div>
        </>
      )}
    </div>
  )
}
