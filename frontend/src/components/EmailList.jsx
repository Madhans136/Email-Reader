import React from 'react'

function EmailList({ emails, selectedEmailId, onSelectEmail, totalInbox }) {
  const getPreview = (body) => {
    if (!body || body === 'No Body') return 'No preview available'
    const preview = body.split('\n')[0]
    return preview.length > 60 ? preview.substring(0, 60) + '...' : preview
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-dark-border flex-shrink-0">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-dark-text flex items-center gap-2">
            <span>📥</span> Inbox
          </h2>
        </div>
        <p className="text-sm text-dark-text-muted mt-1">{totalInbox || emails.length} emails</p>
      </div>  

      {/* Email List */}
      <div className="flex-1 overflow-y-auto min-h-0 scrollbar-thin">
        {emails.map((email) => (
          <div
            key={email.id}
            onClick={() => onSelectEmail(email)}
            className={`p-4 border-b border-dark-border cursor-pointer transition-all duration-200 ${
              selectedEmailId === email.id
                ? 'bg-white-600/20 border-l-4 border-l-blue-500'
                : 'hover:bg-dark-card border-l-4 border-l-transparent'
            }`}
          >
            <div className="flex items-start justify-between mb-1">
              <h3 className={`font-medium truncate flex-1 ${
                selectedEmailId === email.id ? 'text-blue-400' : 'text-dark-text'
              }`}>
                {email.subject}
              </h3>
            </div>
            {email.from && (
              <p className="text-xs text-gray-500 mt-1">
                From: {email.from}
              </p>
            )}
            <p className="text-sm text-dark-text-muted/70 mt-1 line-clamp-1">
              {getPreview(email.body)}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default EmailList
