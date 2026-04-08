import React from 'react'

function EmailDetail({ email }) {
  if (!email) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-gray-500 p-10 text-center">
        <div className="w-16 h-16 bg-[#161B26] rounded-full flex items-center justify-center mb-4 border border-[#262D3D]">
          <svg className="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
        </div>
        <p className="text-sm font-medium">Select a thread to view activity</p>
      </div>
    )
  }

  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    try {
      const date = new Date(dateStr)
      if (isNaN(date.getTime())) return dateStr
      return date.toLocaleString('en-US', {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateStr
    }
  }

  return (
    <div className="h-full flex flex-col bg-[#0B0F1A]">
      {/* Header Section */}
      <div className="p-8 border-b border-[#262D3D]">
        <h1 className="text-xl font-bold text-white leading-tight mb-2">{email.subject || 'No Subject'}</h1>
        <div className="space-y-1 text-sm text-gray-400">
          {email.from && (
            <div className="flex items-center gap-2">
              <span className="text-gray-500 font-medium">From:</span>
              <span>{email.from}</span>
            </div>
          )}
          {email.date && (
            <div className="flex items-center gap-2">
              <span className="text-gray-500 font-medium">Date:</span>
              <span>{formatDate(email.date)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Email Body Section */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-8">
        <div className="bg-[#161B26] border border-[#262D3D] rounded-2xl p-6">
          <pre className="text-gray-300 whitespace-pre-wrap font-mono text-[14px] leading-relaxed">
            {email.body || 'No content'}
          </pre>
        </div>
      </div>
    </div>
  )
}

export default EmailDetail