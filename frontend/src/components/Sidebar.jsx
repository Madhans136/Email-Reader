import React from 'react'

const menuItems = [
  { id: 'Dashboard', label: 'Dashboard', icon: '📊' },
  { id: 'Emails', label: 'Emails', icon: '📧' },
  { id: 'Tickets', label: 'Tickets', icon: '🎫' },
]

function Sidebar({ activeMenu, setActiveMenu }) {
  return (
    <aside className="w-64 bg-dark-card border-r border-dark-border flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-dark-border">
        <h1 className="text-xl font-bold text-dark-text flex items-center gap-2">
          <span className="text-2xl">🤖</span>
          AI Email Reader
        </h1>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {menuItems.map((item) => (
            <li key={item.id}>
              <button
                onClick={() => setActiveMenu(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                  activeMenu === item.id
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                    : 'text-dark-text-muted hover:bg-dark-bg hover:text-dark-text'
                }`}
              >
                <span className="text-xl">{item.icon}</span>
                <span className="font-medium">{item.label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {/* User Profile
      <div className="p-4 border-t border-dark-border">
        <div className="flex items-center gap-3 px-4 py-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
            JD
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-dark-text">John Doe</p>
            <p className="text-xs text-dark-text-muted">Admin</p>
          </div>
        </div>
      </div> */}
    </aside>
  )
}

export default Sidebar
