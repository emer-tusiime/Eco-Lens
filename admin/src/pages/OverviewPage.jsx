import { useState, useEffect } from 'react'
import { api } from '../api'

export default function OverviewPage({ token, navigate }) {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => { load() }, [])

  async function load() {
    try {
      setLoading(true)
      setError(null)
      const d = await api.overview(token)
      setData(d)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="loading-wrap">⏳ Loading overview…</div>
  if (error)   return <div className="error-wrap">⚠ {error}</div>

  const acceptPct = data.totalDisposals > 0
    ? ((data.acceptedDisposals / data.totalDisposals) * 100).toFixed(1)
    : '0'

  const stats = [
    { icon: '⬡', label: 'Total Kiosks',       value: data.totalKiosks,                              color: 'var(--teal)' },
    { icon: '✅', label: 'Active Kiosks',       value: data.activeKiosks,                             color: 'var(--green)' },
    { icon: '👥', label: 'Registered Users',    value: data.totalUsers,                               color: 'var(--green)' },
    { icon: '♻', label: 'Total Disposals',      value: data.totalDisposals.toLocaleString(),          color: 'var(--teal)' },
    { icon: '✓',  label: 'Accepted Plastics',   value: data.acceptedDisposals.toLocaleString(),       color: 'var(--green)' },
    { icon: '⭐', label: 'Total Points Awarded', value: (data.totalPointsAwarded||0).toLocaleString(), color: 'var(--amber)' },
  ]

  const barClass = parseFloat(acceptPct) >= 70 ? 'prog-green'
                 : parseFloat(acceptPct) >= 40 ? 'prog-amber'
                 : 'prog-red'

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">System Overview</div>
          <div className="page-sub">Real-time EcoLens platform statistics</div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load}>↺ Refresh</button>
      </div>

      {/* Stat cards */}
      <div className="stats-grid">
        {stats.map(s => (
          <div key={s.label} className="stat-card" style={{ borderLeftColor: s.color }}>
            <div className="stat-icon">{s.icon}</div>
            <div className="stat-value">{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Acceptance rate */}
      <div className="card section-gap">
        <div className="card-header">
          <div className="card-title">Disposal Acceptance Rate</div>
          <span className={`badge ${parseFloat(acceptPct) >= 60 ? 'badge-green' : 'badge-amber'}`}>
            {acceptPct}% accepted
          </span>
        </div>
        <div className="prog-wrap" style={{ height: 14 }}>
          <div className={`prog-bar ${barClass}`} style={{ width: `${acceptPct}%` }} />
        </div>
        <div className="flex justify-between mt-8 fs-12 c-gray">
          <span>{data.acceptedDisposals.toLocaleString()} accepted items</span>
          <span>{(data.totalDisposals - data.acceptedDisposals).toLocaleString()} rejected items</span>
        </div>
      </div>

      {/* Quick actions */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">Quick Actions</div>
        </div>
        <div className="flex gap-12 flex-wrap">
          <button className="btn btn-primary"   onClick={() => navigate('kiosks')}>      Manage Kiosks →</button>
          <button className="btn btn-secondary" onClick={() => navigate('redemptions')}>  View Redemptions →</button>
        </div>
      </div>
    </div>
  )
}
