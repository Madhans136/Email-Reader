import React, { useState, useEffect } from 'react'
import StatsCards from './StatsCards'
import EmailList from './EmailList'
import EmailDetail from './EmailDetail'
import TicketsPage from './TicketsPage'

function Dashboard({ activeMenu }) {
  const [emails, setEmails] = useState([])
  const [selectedEmail, setSelectedEmail] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [apiData, setApiData] = useState({ threads: [], total_threads: 0, unread_count: 0, replied_count: 0 })

  // Fetch emails from API on component mount
  useEffect(() => {
    fetchEmails()
  }, [])

  const fetchEmails = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      // Use /emails/by-thread to get threads with replies
      const response = await fetch('http://localhost:8000/emails/by-thread')
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      
      // Store API data in state for use throughout component
      setApiData(data)
      
      // Get threads from by-thread API - each thread has title, description, command
      const threads = data.threads || []
      
      // Debug: show what's coming from backend
      console.log('Threads from backend:', threads.length)
      console.log('Sample thread:', threads[0])
      
      // Debug: Log command for each thread
      threads.forEach((thread, idx) => {
        console.log(`Thread ${idx}: ${thread.title}`)
        console.log('Command:', thread.command)
      })
      
      // Convert threads to email format for EmailList
      // Using raw email data: id, subject, from, date, body
      const formattedEmails = threads.map((thread, idx) => ({
        id: thread.id || String(idx + 1),
        subject: thread.subject || 'No Subject',
        from: thread.from || thread.from_email || '',
        date: thread.date || '',
        body: thread.body || '',
        is_replied: false,
        is_read: true
      }))
      
      // Sort by subject alphabetically
      const sortedEmails = [...formattedEmails].sort((a, b) => {
        return a.subject.localeCompare(b.subject)
      })
      
      setEmails(sortedEmails)
      
      // Auto-select first email
      if (sortedEmails.length > 0) {
        setSelectedEmail(sortedEmails[0])
      }
    } catch (err) {
      console.error('Error fetching emails:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelectEmail = (email) => {
    setSelectedEmail(email)
  }

  const handleCreateTicket = async (prefillData = null) => {
    const title = prefillData?.title || selectedEmail?.subject || ''
    const description = prefillData?.description || selectedEmail?.summary || selectedEmail?.body || 'No description'
    
    try {
      const response = await fetch('http://localhost:8000/create-ticket', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title,
          description,
          priority: 'medium'
        })
      })
      
      if (!response.ok) {
        throw new Error('Failed to create ticket')
      }
      
      // Mark the selected email as having a ticket created
      if (selectedEmail) {
        setEmails(prevEmails => 
          prevEmails.map(email => 
            email.id === selectedEmail.id 
              ? { ...email, has_ticket: true }
              : email
          )
        )
        setSelectedEmail(prev => ({ ...prev, has_ticket: true }))
      }
      
      alert('Ticket created successfully!')
    } catch (err) {
      console.error('Error creating ticket:', err)
      alert('Failed to create ticket')
    }
  }

  // Use backend counts from API data
  const emailStats = {
    openedEmails: apiData.total_threads,
    unreadEmails: apiData.unread_count,
    repliedEmails: apiData.replied_count
  }

  // Debug logging for email classification
  if (emails.length > 0) {
    console.log('Email classification debug:')
    emails.forEach(e => {
      console.log({
        subject: e.subject,
        is_read: e.is_read,
        is_replied: e.is_replied,
        classification: e.is_replied === true ? 'REPLIED' : e.is_read === true ? 'OPENED' : 'UNREAD'
      })
    })
    console.log('Stats:', emailStats)
  }

  if (activeMenu === 'Tickets') {
    return <TicketsPage />
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="h-full flex flex-col">
        <header className="bg-dark-card border-b border-dark-border px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-dark-text">
              {activeMenu === 'Dashboard' ? 'Dashboard Overview' : 'Email Management'}
            </h2>
            <p className="text-sm text-dark-text-muted">
              {activeMenu === 'Dashboard' 
                ? 'Monitor your AI email processing system' 
                : 'Manage and view your emails'}
            </p>
          </div>
        </header>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="text-6xl mb-4 animate-pulse">📧</div>
            <p className="text-xl text-dark-text">Loading...</p>
            <p className="text-sm text-dark-text-muted mt-2">Fetching emails from server</p>
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="h-full flex flex-col">
        <header className="bg-dark-card border-b border-dark-border px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-dark-text">
              {activeMenu === 'Dashboard' ? 'Dashboard Overview' : 'Email Management'}
            </h2>
            <p className="text-sm text-dark-text-muted">
              {activeMenu === 'Dashboard' 
                ? 'Monitor your AI email processing system' 
                : 'Manage and view your emails'}
            </p>
          </div>
        </header>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="text-6xl mb-4">❌</div>
            <p className="text-xl text-red-400">Error loading emails</p>
            <p className="text-sm text-dark-text-muted mt-2">{error}</p>
            <button 
              onClick={fetchEmails}
              className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
  <div className="h-full flex flex-col bg-[#0B0F1A]">
    {/* Refined Top Bar */}
    <header className="bg-[#111622] border-b border-[#262D3D] px-8 py-5 flex items-center justify-between">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">
          {activeMenu === 'Dashboard' ? 'System Overview' : 'Thread Manager'}
        </h2>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-widest mt-1">
          {activeMenu === 'Dashboard' ? 'AI Processing Metrics' : 'Inbox Activity'}
        </p>
      </div>
      <div className="flex items-center gap-4">
        <button className="p-2 rounded-xl bg-[#1C2230] text-gray-400 hover:text-white transition-colors border border-[#262D3D]">
          <span className="text-lg">🔔</span>
        </button>
        <button className="p-2 rounded-xl bg-[#1C2230] text-gray-400 hover:text-white transition-colors border border-[#262D3D]">
          <span className="text-lg">⚙️</span>
        </button>
      </div>
    </header>

    {/* Main Content Area */}
    <div className="flex-1 flex flex-col p-8 overflow-hidden">
      {activeMenu === 'Dashboard' && <StatsCards stats={emailStats} />}

      <div className="flex-1 flex bg-[#111622] rounded-3xl border border-[#262D3D] overflow-hidden shadow-2xl">
        {/* Left Side: Email List */}
        <div className="w-1/3 border-r border-[#262D3D]">
          <EmailList 
            emails={emails} 
            selectedEmailId={selectedEmail?.id} 
            onSelectEmail={handleSelectEmail} 
            totalInbox={apiData.total_threads}
          />
        </div>

        {/* Right Side: Detail View */}
        <div className="w-2/3 bg-[#0B0F1A]/50 backdrop-blur-sm">
          <EmailDetail email={selectedEmail} />
        </div>
      </div>
    </div>
  </div>
)
}

export default Dashboard
