import { useState, useEffect } from 'react'
import { api } from '../api'

function fmt(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString()
}

function network(phone) {
  if (!phone) return '?'
  const d = phone.replace(/\D/g, '')
  const local = d.length > 9 ? d.slice(-9) : d
  const p2 = local.slice(0, 2)
  if (['77','78','76','39'].includes(p2)) return 'MTN'
  if (['70','75','74','20'].includes(p2)) return 'Airtel'
  return '?'
}

function StatusBadge({ status }) {
  if (status === 'successful') return <span className="badge badge-green">✓ Successful</span>
  if (status === 'failed')     return <span className="badge badge-red">✗ Failed</span>
  return                              <span className="badge badge-amber">⏳ Pending</span>
}

const FILTERS = ['all', 'successful', 'failed', 'pending']

export default function RedemptionsPage({ token }) {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const [filter,  setFilter]  = useState('all')

  useEffect(() => { load() }, [])

  async function load() {
    try {
      setLoading(true)
      setError(null)
      const d = await api.redemptions(token)
      setData(d)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="loading-wrap">⏳ Loading redemptions…</div>
  if (error)   return <div className="error-wrap">⚠ {error}</div>

  const { stats, redemptions } = data
  const filtered = filter === 'all'
    ? redemptions
    : redemptions.filter(r => r.status === filter)

  const statCards = [
    { label: 'Total Redemptions',      value: stats.total,                                            color: 'var(--teal)' },
    { label: 'Successful',             value: stats.successful,                                        color: 'var(--green)' },
    { label: 'Failed',                 value: stats.failed,                                            color: 'var(--red)' },
    { label: 'Total UGX Paid Out',     value: `UGX ${Number(stats.totalUGX || 0).toLocaleString()}`,  color: 'var(--amber)' },
    { label: 'Total Points Redeemed',  value: (stats.totalPoints || 0).toLocaleString(),               color: 'var(--amber)' },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Airtime Redemptions</div>
          <div className="page-sub">All mobile airtime payout records</div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load}>↺ Refresh</button>
      </div>

      {/* Stats */}
      <div className="stats-grid section-gap" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(155px,1fr))' }}>
        {statCards.map(s => (
          <div key={s.label} className="stat-card" style={{ borderLeftColor: s.color }}>
            <div className="stat-value" style={{ fontSize: 22 }}>{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title">
            Redemption History
            <span className="badge badge-gray" style={{ marginLeft: 10 }}>{filtered.length}</span>
          </div>
          <div className="flex gap-8">
            {FILTERS.map(f => (
              <button
                key={f}
                className={`btn btn-sm ${filter === f ? 'btn-secondary' : 'btn-ghost'}`}
                onClick={() => setFilter(f)}
                style={{ textTransform: 'capitalize' }}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">◈</div>
            <div>No {filter !== 'all' ? filter : ''} redemptions found.</div>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Phone Number</th>
                  <th>Network</th>
                  <th>Points</th>
                  <th>Airtime (UGX)</th>
                  <th>Status</th>
                  <th>AT Transaction ID</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(r => {
                  const net = network(r.phoneNumber)
                  return (
                    <tr key={r.id}>
                      <td>
                        <div className="fw-600 fs-13">{r.user?.name || '—'}</div>
                        <div className="c-gray fs-11">{r.user?.email}</div>
                      </td>
                      <td className="td-mono">{r.phoneNumber}</td>
                      <td>
                        <span className={`badge ${net === 'MTN' ? 'badge-amber' : net === 'Airtel' ? 'badge-red' : 'badge-gray'}`}>
                          {net}
                        </span>
                      </td>
                      <td className="c-amber fw-600">{r.pointsRedeemed}</td>
                      <td className="fw-600">UGX {Number(r.airtimeAmountUgx).toLocaleString()}</td>
                      <td>
                        <StatusBadge status={r.status} />
                        {r.status === 'failed' && r.errorMessage && (
                          <div className="c-red fs-11 mt-4">{r.errorMessage}</div>
                        )}
                      </td>
                      <td className="td-mono td-muted" style={{ fontSize: 11 }}>
                        {r.atTransactionId || '—'}
                      </td>
                      <td className="td-muted fs-12">{fmt(r.createdAt)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
