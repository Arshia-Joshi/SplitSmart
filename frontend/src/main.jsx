import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, RequireAuth, useAuth } from './auth'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import { Login, Signup } from './pages/Auth'
import Upload from './pages/Upload'
import Split from './pages/Split'
import History from './pages/History'
import BillDetail from './pages/BillDetail'
import './styles.css'

function Home() {
  const { user, loading } = useAuth()
  if (loading) return null
  return user ? <Navigate to="/new" replace /> : <Landing />
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/new" element={<RequireAuth><Upload /></RequireAuth>} />
            <Route path="/split" element={<RequireAuth><Split /></RequireAuth>} />
            <Route path="/bills" element={<RequireAuth><History /></RequireAuth>} />
            <Route path="/bills/:id" element={<RequireAuth><BillDetail /></RequireAuth>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
