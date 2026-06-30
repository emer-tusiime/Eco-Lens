const NAV = [
  { key: 'overview',    icon: '◉', label: 'Overview'    },
  { key: 'kiosks',      icon: '⬡', label: 'Kiosks'      },
  { key: 'redemptions', icon: '◈', label: 'Redemptions' },
]

const TITLES = {
  overview:     'Overview',
  kiosks:       'Kiosks',
  'kiosk-detail': 'Kiosk Detail',
  redemptions:  'Airtime Redemptions',
}

export default function Layout({ children, page, navigate, admin, onLogout }) {
  const isKioskSection = page === 'kiosks' || page === 'kiosk-detail'

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-logo">♻ EcoLens</div>
          <div className="sidebar-sub">Admin Dashboard</div>
        </div>

        <nav className="sidebar-nav">
          {NAV.map(n => (
            <button
              key={n.key}
              className={`nav-item${(n.key === 'kiosks' ? isKioskSection : page === n.key) ? ' active' : ''}`}
              onClick={() => navigate(n.key)}
            >
              <span className="nav-icon">{n.icon}</span>
              {n.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          {admin && (
            <div className="admin-pill">
              <div className="admin-name">{admin.name}</div>
              <div className="admin-email">{admin.email}</div>
            </div>
          )}
          <button className="btn btn-ghost btn-sm btn-full" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </aside>

      <div className="main-area">
        <div className="topbar">
          <div className="topbar-title">{TITLES[page] || 'EcoLens'}</div>
          <div className="topbar-badge">♻ EcoLens Platform</div>
        </div>
        <div className="content">{children}</div>
      </div>
    </div>
  )
}
