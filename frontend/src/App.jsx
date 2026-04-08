import React, { useState } from 'react'
import Sidebar from './components/Sidebar'
import Dashboard from './components/Dashboard'

function App() {
  const [activeMenu, setActiveMenu] = useState('Dashboard')

  return (
    <div className="flex h-screen bg-dark-bg">
      <Sidebar activeMenu={activeMenu} setActiveMenu={setActiveMenu} />
      <main className="flex-1 overflow-hidden">
        <Dashboard activeMenu={activeMenu} />
      </main>
    </div>
  )
}

export default App
