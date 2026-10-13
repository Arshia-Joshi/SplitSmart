import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, compressImage } from '../api'
import { useAuth } from '../auth'
import { newDraft, saveDraft } from '../draft'

export default function Upload() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const fileRef = useRef()
  const cameraRef = useRef()
  const [preview, setPreview] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const handleFile = async (file) => {
    if (!file) return
    if (!file.type.startsWith('image/')) return setError('Please choose an image file')
    setError('')
    const url = URL.createObjectURL(file)
    setPreview(url)
    setBusy(true)
    try {
      const small = await compressImage(file)
      const form = new FormData()
      form.append('bill', small)
      const scanned = await api('/scan', { method: 'POST', body: form })
      saveDraft(newDraft(user.username, scanned))
      navigate('/split', { state: { image: url } })
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  const manual = () => {
    saveDraft(newDraft(user.username))
    navigate('/split')
  }

  return (
    <div className="container narrow section">
      <h1>New bill</h1>
      <p className="muted">Hi {user.username}! Upload a photo of the bill and we'll read it for you.</p>

      <div
        className={`dropzone card ${dragging ? 'dragging' : ''} ${busy ? 'busy' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]) }}
        onClick={() => !busy && fileRef.current.click()}
        role="button" tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && !busy && fileRef.current.click()}
      >
        {preview ? (
          <img src={preview} alt="Bill preview" className="dz-preview" />
        ) : (
          <div className="dz-icon" aria-hidden="true">
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="M17 8l-5-5-5 5" /><path d="M12 3v12" /></svg>
          </div>
        )}
        {busy ? (
          <div className="dz-text"><div className="spinner" /><strong>Reading your bill…</strong><span className="muted">This takes a few seconds</span></div>
        ) : (
          <div className="dz-text">
            <strong>Drop a bill photo here, or click to choose</strong>
            <span className="muted">JPG, PNG or WEBP</span>
          </div>
        )}
      </div>

      <input ref={fileRef} type="file" accept="image/*" hidden onChange={(e) => handleFile(e.target.files[0])} />
      <input ref={cameraRef} type="file" accept="image/*" capture="environment" hidden onChange={(e) => handleFile(e.target.files[0])} />

      {error && <div className="alert alert-error">{error}</div>}

      <div className="upload-actions">
        <button className="btn btn-ghost" disabled={busy} onClick={() => cameraRef.current.click()}>Take a photo</button>
        <button className="btn btn-ghost" disabled={busy} onClick={manual}>Enter bill manually</button>
      </div>
    </div>
  )
}
