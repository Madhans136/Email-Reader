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
      // Now using command field instead of replies array
      const formattedEmails = threads.map((thread, idx) => ({
        id: String(idx + 1),
        subject: thread.title || 'No Subject',
        thread_id: thread.thread_id,
        body: thread.description,
        description: thread.description,
        title: thread.title,
        command: thread.command || '',  // Reply content from subsequent messages
        from_email: thread.from_email,
        is_replied: !!(thread.command && thread.command.length > 0),
        is_read: true
      }))
      
      // Sort by has command (replies > 0 first)
      const sortedEmails = [...formattedEmails].sort((a, b) => {
        const aReplied = (a.command && a.command.length > 0) ? 1 : 0
        const bReplied = (b.command && b.command.length > 0) ? 1 : 0
        return bReplied - aReplied || a.subject.localeCompare(b.subject)
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
    <div className="h-full flex flex-col">
      {/* Top Bar */}
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
        <div className="flex items-center gap-3">
          <button className="p-2 rounded-lg bg-dark-bg hover:bg-dark-border text-dark-text-muted hover:text-dark-text transition-colors">
            <span className="text-xl">🔔</span>
          </button>
          <button className="p-2 rounded-lg bg-dark-bg hover:bg-dark-border text-dark-text-muted hover:text-dark-text transition-colors">
            <span className="text-xl">⚙️</span>
          </button>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 flex flex-col min-h-0 p-6">
        {/* Stats Cards - Only show on Dashboard */}
        {activeMenu === 'Dashboard' && (
          <StatsCards stats={emailStats} />
        )}

        {/* Email Section */}
        <div className="flex h-[calc(100vh-120px)] bg-dark-card rounded-xl border border-dark-border overflow-hidden">
          {/* Left - Email List */}
          <div className="w-1/2 border-r border-dark-border flex flex-col">
            <EmailList
              emails={emails}
              selectedEmailId={selectedEmail?.id}
              onSelectEmail={handleSelectEmail}
              totalInbox={apiData.total_threads}
            />
          </div>

          {/* Right - Email Detail */}
          <div className="w-1/2 flex flex-col bg-dark-bg/30">
            <EmailDetail email={selectedEmail} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
