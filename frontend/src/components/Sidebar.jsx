import React from 'react'

const menuItems = [
  { id: 'Dashboard', label: 'Dashboard', icon: 'M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z' },
  { id: 'Emails', label: 'Emails', icon: 'M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z' },
  { id: 'Tickets', label: 'Tickets', icon: 'M18 7H6V5h12v2zm0 5H6v-2h12v2zm0 5H6v-2h12v2z' },
]

function Sidebar({ activeMenu, setActiveMenu }) {
  return (
    <aside className="w-64 bg-[#111622] border-r border-[#262D3D] flex flex-col">
      <div className="p-8">
        <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-3">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <span className="text-xs">AI</span>
          </div>
          EmailReader
        </h1>
      </div>

      <nav className="flex-1 px-4">
        <ul className="space-y-1">
          {menuItems.map((item) => (
            <li key={item.id}>
              <button
                onClick={() => setActiveMenu(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                  activeMenu === item.id
                    ? 'active-nav-gradient text-indigo-400 border-l-2 border-indigo-500'
                    : 'text-gray-400 hover:bg-[#1A202E] hover:text-gray-200'
                }`}
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d={item.icon} />
                </svg>
                <span className="text-sm font-semibold">{item.label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  )
}

export default Sidebar