// Small fetch wrapper: sends cookies, parses JSON, throws readable errors
export async function api(path, { method = 'GET', body, signal } = {}) {
  const options = { method, credentials: 'include', signal, headers: {} }
  if (body instanceof FormData) {
    options.body = body
  } else if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(body)
  }

  let res
  try {
    res = await fetch(`/api${path}`, options)
  } catch (e) {
    if (e.name === 'AbortError') throw e
    throw new Error('Network error, check your connection')
  }

  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = new Error(data.error || `Something went wrong (${res.status})`)
    err.status = res.status
    throw err
  }
  return data
}

const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' })
export const money = (n) => inr.format(Number(n) || 0)

export function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

// Shrink big phone photos before upload (Vercel limits request size to ~4.5 MB)
export function compressImage(file, maxSide = 1800, quality = 0.85) {
  return new Promise((resolve) => {
    const img = new Image()
    const url = URL.createObjectURL(file)
    img.onload = () => {
      const scale = Math.min(1, maxSide / Math.max(img.width, img.height))
      const canvas = document.createElement('canvas')
      canvas.width = Math.round(img.width * scale)
      canvas.height = Math.round(img.height * scale)
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height)
      canvas.toBlob((blob) => {
        URL.revokeObjectURL(url)
        resolve(blob ? new File([blob], 'bill.jpg', { type: 'image/jpeg' }) : file)
      }, 'image/jpeg', quality)
    }
    img.onerror = () => { URL.revokeObjectURL(url); resolve(file) }
    img.src = url
  })
}
