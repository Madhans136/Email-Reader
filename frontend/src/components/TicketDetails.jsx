import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'

function TicketDetails() {
  const { id } = useParams()
  const [ticket, setTicket] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchTicket()
  }, [id])

  const fetchTicket = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`http://localhost:8000/tickets/${id}`)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      
      if (data.error) {
        setError(data.error)
      } else if (data.ticket) {
        setTicket(data.ticket)
      } else {
        setError('Ticket not found')
      }
    } catch (err) {
      console.error('Error fetching ticket:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high':
        return 'bg-red-500/20 text-red-400 border-red-500/30'
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
      case 'low':
        return 'bg-green-500/20 text-green-400 border-green-500/30'
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'open':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
      case 'in-progress':
        return 'bg-purple-500/20 text-purple-400 border-purple-500/30'
      case 'closed':
        return 'bg-green-500/20 text-green-400 border-green-500/30'
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
  }


  if (isLoading) {
    return (
      <div className="h-full flex flex-col">
        <header className="bg-dark-card border-b border-dark-border px-6 py-4">
          <h2 className="text-xl font-bold text-dark-text">Ticket Details</h2>
        </header>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="text-6xl mb-4 animate-pulse">🎫</div>
            <p className="text-xl text-dark-text">Loading...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-full flex flex-col">
        <header className="bg-dark-card border-b border-dark-border px-6 py-4">
          <h2 className="text-xl font-bold text-dark-text">Ticket Details</h2>
        </header>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="text-6xl mb-4">❌</div>
            <p className="text-xl text-red-400">Error loading ticket</p>
            <p className="text-sm text-dark-text-muted mt-2">{error}</p>
            <Link 
              to="/tickets"
              className="mt-4 inline-block px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              Back to Tickets
            </Link>
          </div>
        </div>
      </div>
    )
  }

  if (!ticket) {
    return (
      <div className="h-full flex flex-col">
        <header className="bg-dark-card border-b border-dark-border px-6 py-4">
          <h2 className="text-xl font-bold text-dark-text">Ticket Details</h2>
        </header>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="text-6xl mb-4">🔍</div>
            <p className="text-xl text-dark-text">Ticket not found</p>
            <Link 
              to="/tickets"
              className="mt-4 inline-block px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              Back to Tickets
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Top Bar */}
      <header className="bg-dark-card border-b border-dark-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link 
              to="/tickets"
              className="p-2 rounded-lg bg-dark-bg hover:bg-dark-border text-dark-text-muted hover:text-dark-text transition-colors"
            >
              <span className="text-xl">←</span>
            </Link>
            <div>
              <h2 className="text-xl font-bold text-dark-text">Ticket Details</h2>
              <p className="text-sm text-dark-text-muted">
                #{ticket.ticket_id}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(ticket.status)}`}>
              {ticket.status}
            </span>
            <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getPriorityColor(ticket.priority)}`}>
              {ticket.priority}
            </span>
          </div>
        </div>
      </header>

      {/* Ticket Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">
          {/* Title */}
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-dark-text mb-2">
              {ticket.title}
            </h1>
          </div>

          {/* Metadata */}
          <div className="bg-dark-card rounded-xl border border-dark-border p-4 mb-6">
            <div className="space-y-3">
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Created</p>
                <p className="text-dark-text">
                  {ticket.created_at ? new Date(ticket.created_at).toLocaleString() : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Sender</p>
                <p className="text-dark-text">
                  {ticket.sender_name && ticket.sender_email
                    ? `${ticket.sender_name} (${ticket.sender_email})`
                    : ticket.sender_email || ticket.sender_name || 'N/A'}
                </p>
              </div>
            </div>
          </div>

          {/* Description */}
          <div className="bg-dark-card rounded-xl border border-dark-border p-6">
            <h2 className="text-lg font-semibold text-dark-text mb-4">Description</h2>
            <div className="bg-dark-bg rounded-lg p-4">
              <pre className="text-dark-text-muted whitespace-pre-wrap font-sans text-sm leading-relaxed">
                {ticket.description || 'No description provided'}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default TicketDetails
