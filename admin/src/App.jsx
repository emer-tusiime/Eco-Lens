import { useState } from 'react'
import './index.css'
import Layout       from './components/Layout'
import LoginPage    from './pages/LoginPage'
import OverviewPage from './pages/OverviewPage'
import KiosksPage   from './pages/KiosksPage'
import KioskDetail  from './pages/KioskDetailPage'
import RedemptionsPage from './pages/RedemptionsPage'

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem('ecl_admin_tok') || null)
  const [admin,  setAdmin]  = useState(() => {
    try { return JSON.parse(localStorage.getItem('ecl_admin_info') || 'null') } catch { return null }
  })
  const [page,    setPage]    = useState('overview')
  const [kioskId, setKioskId] = useState(null)

  function handleLogin(tok, adminData) {
    localStorage.setItem('ecl_admin_tok',  tok)
    localStorage.setItem('ecl_admin_info', JSON.stringify(adminData))
    setToken(tok)
    setAdmin(adminData)
  }

  function handleLogout() {
    localStorage.removeItem('ecl_admin_tok')
    localStorage.removeItem('ecl_admin_info')
    setToken(null)
    setAdmin(null)
    setPage('overview')
  }

  function navigate(p, id = null) {
    setPage(p)
    if (id !== null) setKioskId(id)
  }

  if (!token) return <LoginPage onLogin={handleLogin} />

  return (
    <Layout page={page} navigate={navigate} admin={admin} onLogout={handleLogout}>
      {page === 'overview'     && <OverviewPage    token={token} navigate={navigate} />}
      {page === 'kiosks'       && <KiosksPage      token={token} navigate={navigate} />}
      {page === 'kiosk-detail' && <KioskDetail     token={token} kioskId={kioskId} navigate={navigate} />}
      {page === 'redemptions'  && <RedemptionsPage token={token} />}
    </Layout>
  )
}
