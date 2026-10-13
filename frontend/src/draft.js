// The bill being edited is kept in sessionStorage so a refresh doesn't lose it
const KEY = 'splitsmart-draft'

let nextId = 1
export const uid = () => `${Date.now().toString(36)}-${nextId++}`

export function newDraft(username, scanned = {}) {
  const items = (scanned.items || []).map((i) => ({ id: uid(), name: i.name, price: String(i.price), assigned: [] }))
  return {
    restaurant_name: scanned.restaurant_name || '',
    people: [username, ''],
    items: items.length ? items : [{ id: uid(), name: '', price: '', assigned: [] }],
    charges: (scanned.charges || []).map((c) => ({ id: uid(), name: c.name, amount: String(c.amount) })),
    discount: scanned.discount ? String(scanned.discount) : '',
    printed_total: scanned.printed_total || 0,
  }
}

export function loadDraft() {
  try {
    return JSON.parse(sessionStorage.getItem(KEY))
  } catch {
    return null
  }
}

export function saveDraft(draft) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(draft))
  } catch { /* storage full or blocked, ignore */ }
}

export function clearDraft() {
  try { sessionStorage.removeItem(KEY) } catch { /* ignore */ }
}
