import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function TicketsPage() {
  const navigate = useNavigate()
  const [tickets, setTickets] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'medium'
  })

  useEffect(() => {
    fetchTickets()
  }, [])

  const fetchTickets = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const response = await fetch('http://localhost:8000/tickets')
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      setTickets(data.tickets || [])
    } catch (err) {
      console.error('Error fetching tickets:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateTicket = async (e) => {
    e.preventDefault()
    
    try {
      const response = await fetch('http://localhost:8000/create-ticket', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      })
      
      if (!response.ok) {
        throw new Error('Failed to create ticket')
      }
      
      setShowModal(false)
      setFormData({ title: '', description: '', priority: 'medium' })
      fetchTickets()
    } catch (err) {
      console.error('Error creating ticket:', err)
      alert('Failed to create ticket')
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
          <h2 className="text-xl font-bold text-dark-text">Tickets</h2>
          <p className="text-sm text-dark-text-muted">Manage your tasks</p>
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
          <h2 className="text-xl font-bold text-dark-text">Tickets</h2>
          <p className="text-sm text-dark-text-muted">Manage your tasks</p>
        </header>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="text-6xl mb-4">❌</div>
            <p className="text-xl text-red-400">Error loading tickets</p>
            <p className="text-sm text-dark-text-muted mt-2">{error}</p>
            <button 
              onClick={fetchTickets}
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
          <h2 className="text-xl font-bold text-dark-text">Tickets</h2>
          <p className="text-sm text-dark-text-muted">
            {tickets.length} ticket{tickets.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={fetchTickets}
            className="p-2 rounded-lg bg-dark-bg hover:bg-dark-border text-dark-text-muted hover:text-dark-text transition-colors"
          >
            <span className="text-xl">🔄</span>
          </button>
          <button 
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center gap-2"
          >
            <span>➕</span> Create Ticket
          </button>
        </div>
      </header>

      {/* Tickets List */}
      <div className="flex-1 overflow-y-auto p-6">
        {tickets.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="text-6xl mb-4">🎫</div>
            <p className="text-xl text-dark-text">No tickets yet</p>
            <p className="text-sm text-dark-text-muted mt-2">
              Click "Create Ticket" to get started
            </p>
          </div>
        ) : (
          <div className="grid gap-4">
            {tickets.map((ticket) => (
              <div
                key={ticket.id}
                onClick={() => navigate(`/ticket/${ticket.id}`)}
                className="bg-dark-card rounded-xl border border-dark-border p-5 hover:border-blue-500/50 transition-colors cursor-pointer"
              >
                {/* Header with Ticket ID and Status */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                      #{ticket.ticket_id}
                    </span>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(ticket.status)}`}>
                      {ticket.status}
                    </span>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getPriorityColor(ticket.priority)}`}>
                    {ticket.priority}
                  </span>
                </div>
                
                {/* Title */}
                <h3 className="text-lg font-semibold text-dark-text mb-2">
                  {ticket.title}
                </h3>
                
                {/* Description */}
                <div className="mb-3">
                  <p className="text-sm text-dark-text-muted">
                    {ticket.description && ticket.description.length > 60 
                      ? ticket.description.slice(0, 60) + '...' 
                      : ticket.description || 'No description'}
                  </p>
                </div>
                
                {/* Footer with Created Time */}
                <div className="flex items-center justify-between pt-3 border-t border-dark-border">
                  <span className="text-xs text-gray-500">
                    Created: {ticket.created_at ? new Date(ticket.created_at).toLocaleString() : 'N/A'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Ticket Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-dark-card rounded-xl border border-dark-border w-full max-w-md p-6 m-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-dark-text">Create Ticket</h3>
              <button 
                onClick={() => setShowModal(false)}
                className="text-dark-text-muted hover:text-dark-text text-2xl"
              >
                ×
              </button>
            </div>
            <form onSubmit={handleCreateTicket}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-dark-text mb-1">
                    Title
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.title}
                    onChange={(e) => setFormData({...formData, title: e.target.value})}
                    className="w-full px-4 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:border-blue-500"
                    placeholder="Enter ticket title"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-dark-text mb-1">
                    Description
                  </label>
                  <textarea
                    required
                    rows={4}
                    value={formData.description}
                    onChange={(e) => setFormData({...formData, description: e.target.value})}
                    className="w-full px-4 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:border-blue-500 resize-none"
                    placeholder="Enter ticket description"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-dark-text mb-1">
                    Priority
                  </label>
                  <select
                    value={formData.priority}
                    onChange={(e) => setFormData({...formData, priority: e.target.value})}
                    className="w-full px-4 py-2 bg-dark-bg border border-dark-border rounded-lg text-dark-text focus:outline-none focus:border-blue-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 px-4 py-2 bg-dark-bg hover:bg-dark-border text-dark-text rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default TicketsPage
