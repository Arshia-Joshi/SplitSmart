import { useEffect, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { api, money } from '../api'
import { clearDraft, loadDraft, saveDraft, uid } from '../draft'

// What the server needs (empty names/prices get sensible defaults)
function toPayload(d) {
  return {
    restaurant_name: d.restaurant_name.trim() || 'Restaurant',
    people: d.people.map((p, i) => p.trim() || `Person ${i + 1}`),
    items: d.items.map((it) => ({ name: it.name, price: it.price || 0, assigned: it.assigned })),
    charges: d.charges.map((c) => ({ name: c.name, amount: c.amount || 0 })),
    discount: d.discount || 0,
  }
}

export default function Split() {
  const navigate = useNavigate()
  const location = useLocation()
  const [draft, setDraft] = useState(loadDraft)
  const [result, setResult] = useState(null)
  const [previewError, setPreviewError] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [showImage, setShowImage] = useState(false)
  const image = location.state?.image

  // Keep the draft saved and ask the server for live totals (debounced)
  useEffect(() => {
    if (!draft) return
    saveDraft(draft)
    const ctrl = new AbortController()
    const t = setTimeout(() => {
      api('/split/preview', { method: 'POST', body: toPayload(draft), signal: ctrl.signal })
        .then((r) => { setResult(r); setPreviewError('') })
        .catch((e) => { if (e.name !== 'AbortError') setPreviewError(e.message) })
    }, 300)
    return () => { clearTimeout(t); ctrl.abort() }
  }, [draft])

  if (!draft) return <Navigate to="/new" replace />

  const update = (changes) => setDraft((d) => ({ ...d, ...changes }))
  const names = draft.people.map((p, i) => p.trim() || `Person ${i + 1}`)

  // ----- people -----
  const setPerson = (i, value) => update({ people: draft.people.map((p, j) => (j === i ? value : p)) })
  const addPerson = () => update({ people: [...draft.people, ''] })
  const removePerson = (i) => {
    if (draft.people.length === 1) return
    update({
      people: draft.people.filter((_, j) => j !== i),
      // shift assignments so they still point at the right people
      items: draft.items.map((it) => ({
        ...it,
        assigned: it.assigned.filter((a) => a !== i).map((a) => (a > i ? a - 1 : a)),
      })),
    })
  }

  // ----- items -----
  const setItem = (id, changes) => update({ items: draft.items.map((it) => (it.id === id ? { ...it, ...changes } : it)) })
  const addItem = () => update({ items: [...draft.items, { id: uid(), name: '', price: '', assigned: [] }] })
  const removeItem = (id) => update({ items: draft.items.filter((it) => it.id !== id) })
  const toggle = (it, i) => setItem(it.id, {
    assigned: it.assigned.includes(i) ? it.assigned.filter((a) => a !== i) : [...it.assigned, i].sort((a, b) => a - b),
  })
  const toggleAll = (it) => setItem(it.id, {
    assigned: it.assigned.length === draft.people.length ? [] : draft.people.map((_, i) => i),
  })

  // ----- charges -----
  const setCharge = (id, changes) => update({ charges: draft.charges.map((c) => (c.id === id ? { ...c, ...changes } : c)) })
  const addCharge = () => update({ charges: [...draft.charges, { id: uid(), name: '', amount: '' }] })
  const removeCharge = (id) => update({ charges: draft.charges.filter((c) => c.id !== id) })

  const save = async () => {
    setSaveError('')
    if (!draft.items.some((it) => Number(it.price) > 0)) return setSaveError('Add at least one item with a price')
    setSaving(true)
    try {
      const { bill } = await api('/bills', { method: 'POST', body: toPayload(draft) })
      clearDraft()
      navigate(`/bills/${bill.id}`, { replace: true, state: { justSaved: true } })
    } catch (e) {
      setSaveError(e.message)
      setSaving(false)
    }
  }

  const mismatch = result && draft.printed_total > 0 && Math.abs(result.total - draft.printed_total) >= 0.01

  return (
    <div className="container section">
      <div className="split-head">
        <input className="title-input" placeholder="Restaurant name" value={draft.restaurant_name}
          onChange={(e) => update({ restaurant_name: e.target.value })} aria-label="Restaurant name" />
        {image && (
          <button className="btn btn-ghost btn-sm" onClick={() => setShowImage(!showImage)}>
            {showImage ? 'Hide bill photo' : 'Show bill photo'}
          </button>
        )}
      </div>
      {showImage && image && <img src={image} alt="Bill" className="bill-photo card" />}

      <div className="split-grid">
        <div className="split-main">
          {/* People */}
          <section className="card panel">
            <div className="panel-head">
              <h2>People</h2>
              <button className="btn btn-ghost btn-sm" onClick={addPerson}>+ Add person</button>
            </div>
            <div className="people-list">
              {draft.people.map((p, i) => (
                <div className="person-input" key={i}>
                  <div className={`avatar c${i % 6}`}>{(names[i][0] || '?').toUpperCase()}</div>
                  <input value={p} placeholder={`Person ${i + 1}`} maxLength={100}
                    onChange={(e) => setPerson(i, e.target.value)} aria-label={`Person ${i + 1} name`} />
                  {draft.people.length > 1 && (
                    <button className="icon-btn" onClick={() => removePerson(i)} aria-label={`Remove ${names[i]}`}>×</button>
                  )}
                </div>
              ))}
            </div>
          </section>

          {/* Items */}
          <section className="card panel">
            <div className="panel-head">
              <h2>Items</h2>
              <span className="muted small">Tap names to assign. Nobody ticked = shared by all.</span>
            </div>
            <div className="items">
              {draft.items.map((it) => {
                const price = Number(it.price) || 0
                const count = it.assigned.length || draft.people.length
                return (
                  <div className="item" key={it.id}>
                    <div className="item-top">
                      <input className="item-name" placeholder="Item name" value={it.name}
                        onChange={(e) => setItem(it.id, { name: e.target.value })} aria-label="Item name" />
                      <div className="money-input">
                        <span>₹</span>
                        <input type="number" inputMode="decimal" step="0.01" min="0" placeholder="0.00" value={it.price}
                          onChange={(e) => setItem(it.id, { price: e.target.value })} aria-label="Item price" />
                      </div>
                      <button className="icon-btn" onClick={() => removeItem(it.id)} aria-label="Remove item">×</button>
                    </div>
                    <div className="chips">
                      <button className={`chip ${it.assigned.length === draft.people.length ? 'on' : ''}`}
                        onClick={() => toggleAll(it)}>Everyone</button>
                      {names.map((n, i) => (
                        <button key={i} className={`chip ${it.assigned.includes(i) ? 'on' : ''}`} onClick={() => toggle(it, i)}>
                          {n}
                        </button>
                      ))}
                      {price > 0 && count > 1 && (
                        <span className="muted small each">{money(price / count)} each</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
            <button className="btn btn-ghost btn-block" onClick={addItem}>+ Add item</button>
          </section>

          {/* Taxes & charges */}
          <section className="card panel">
            <div className="panel-head">
              <h2>Taxes &amp; charges</h2>
              <button className="btn btn-ghost btn-sm" onClick={addCharge}>+ Add</button>
            </div>
            <p className="muted small">Split equally between everyone. Use a negative amount for round off down.</p>
            {draft.charges.map((c) => (
              <div className="row-input" key={c.id}>
                <input placeholder="e.g. CGST 2.5%" value={c.name} onChange={(e) => setCharge(c.id, { name: e.target.value })}
                  aria-label="Charge name" />
                <div className="money-input">
                  <span>₹</span>
                  <input type="number" inputMode="decimal" step="0.01" placeholder="0.00" value={c.amount}
                    onChange={(e) => setCharge(c.id, { amount: e.target.value })} aria-label="Charge amount" />
                </div>
                <button className="icon-btn" onClick={() => removeCharge(c.id)} aria-label="Remove charge">×</button>
              </div>
            ))}
            <div className="row-input">
              <label className="grow">Discount</label>
              <div className="money-input">
                <span>₹</span>
                <input type="number" inputMode="decimal" step="0.01" min="0" placeholder="0.00" value={draft.discount}
                  onChange={(e) => update({ discount: e.target.value })} aria-label="Discount" />
              </div>
              <span className="icon-btn-space" />
            </div>
          </section>
        </div>

        {/* Live summary */}
        <aside className="split-side">
          <div className="card panel summary">
            <h2>Summary</h2>
            {previewError && <div className="alert alert-error">{previewError}</div>}
            {result && (
              <>
                <div className="sum-lines">
                  <div><span>Items</span><span>{money(result.items_total)}</span></div>
                  {result.charges_total !== 0 && <div><span>Taxes &amp; charges</span><span>{money(result.charges_total)}</span></div>}
                  {result.discount > 0 && <div><span>Discount</span><span>−{money(result.discount)}</span></div>}
                  <div className="sum-total"><span>Total</span><span>{money(result.total)}</span></div>
                </div>

                {mismatch && (
                  <div className="alert alert-warn">
                    The bill says {money(draft.printed_total)}. Check the items and charges match.
                  </div>
                )}
                {result.unassigned_items.length > 0 && (
                  <div className="alert alert-info">
                    Shared by everyone: {result.unassigned_items.join(', ')}
                  </div>
                )}

                <div className="shares">
                  {result.people.map((p, i) => (
                    <div className="share" key={i}>
                      <div className={`avatar c${i % 6}`}>{p.name[0].toUpperCase()}</div>
                      <div className="grow">
                        <div className="share-name">{p.name}</div>
                        <small className="muted">
                          {money(p.items_total)} items{p.extras !== 0 && ` + ${money(p.extras)} tax`}
                        </small>
                      </div>
                      <strong>{money(p.total)}</strong>
                    </div>
                  ))}
                </div>
              </>
            )}
            {!result && !previewError && <div className="spinner" />}

            {saveError && <div className="alert alert-error">{saveError}</div>}
            <button className="btn btn-primary btn-block btn-lg" onClick={save} disabled={saving || !result}>
              {saving ? 'Saving…' : 'Save split'}
            </button>
          </div>
        </aside>
      </div>
    </div>
  )
}
