import React, { useState } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './components/Dashboard'
import TicketDetails from './components/TicketDetails'

function App() {
  const [activeMenu, setActiveMenu] = useState('Dashboard')

  return (
    <Router>
      <div className="flex h-screen bg-dark-bg">
        <Sidebar activeMenu={activeMenu} setActiveMenu={setActiveMenu} />
        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/ticket/:id" element={<TicketDetails />} />
            <Route path="/*" element={<Dashboard activeMenu={activeMenu} />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
