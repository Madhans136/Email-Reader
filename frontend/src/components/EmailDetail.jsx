import React from 'react'

// Helper function to clean reply content (remove quoted text)
function cleanReply(body) {
  if (!body) return ''
  
  // Remove common email quote patterns
  let result = body
  
  // Remove "On <date> ... wrote:" patterns
  result = result.replace(/On\s+.+?\s+wrote:.*$/gim, '')
  
  // Remove "From: ... Sent: ... To: ..." patterns
  result = result.replace(/From:\s*.+?\n.*?Sent:\s*.+?\n.*?To:\s*.+?\n/gi, '')
  
  // Remove forwarded message separators
  result = result.replace(/-+\s*Forwarded message\s*-+.*$/gi, '')
  
  // Remove lines starting with >
  result = result.split('\n').filter(line => !line.trim().startsWith('>')).join('\n')
  
  // Clean up extra whitespace
  result = result.split('\n').map(line => line.trim()).filter(line => line).join('\n')
  
  return result.trim()
}

function EmailDetail({ email }) {
  if (!email) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-dark-text-muted">
        <span className="text-6xl mb-4">📧</span>
        <p className="text-lg">Select an email to view details</p>
        <p className="text-sm mt-2">Click on any email from the list</p>
      </div>
    )
  }

  // Remove "Re:" prefix from title
  let title = email.title || email.subject || ''
  title = title.replace(/^Re:\s*/i, '').trim()

  // Get description - from email object or fallback to body
  const description = email.description || email.body || ''

  // Get command - reply content from subsequent messages in thread
  // command is now a single string, not an array
  const command = email.command || ''
  
  // Debug: log command to verify data is coming
  console.log('EmailDetail - command:', command)

  return (
    <div className="h-full flex flex-col">
      {/* Title Section */}
      <div className="p-6 border-b border-dark-border flex-shrink-0">
        <div className="flex items-center gap-2 text-sm text-dark-text-muted mb-1">
          <span>🎫</span>
          <span>Ticket</span>
        </div>
        <h1 className="text-xl font-bold text-dark-text leading-tight">
          {title}
        </h1>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto min-h-0 scrollbar-thin">
        {/* Description Section */}
        <div className="p-6 border-b border-dark-border">
          <div className="flex items-center gap-2 text-sm font-semibold text-dark-text mb-3">
            <span>📝</span>
            <span>Description</span>
          </div>
          <div className="bg-dark-card rounded-xl p-4">
            <div className="text-xs text-dark-text-muted mb-2">
              From: {email.from_email || 'Unknown Sender'}
            </div>
            <p className="text-dark-text whitespace-pre-wrap leading-relaxed">
              {description}
            </p>
          </div>
        </div>

        {/* Commands Section - Only show if there is command (reply content) */}
        {command && command.length > 0 && (
          <div className="p-6">
            <div className="flex items-center gap-2 text-sm font-semibold text-dark-text mb-3">
              <span>⚡</span>
              <span>Commands</span>
            </div>
            
            {/* Split command by "\n\n" to get individual replies */}
            {command.split('\n\n').map((reply, index) => (
              <div 
                key={index} 
                className="bg-dark-card rounded-lg p-4 border-l-4 border-l-blue-500 mb-3 last:mb-0"
              >
                <p className="text-dark-text leading-relaxed">
                  {cleanReply(reply) || 'No content'}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default EmailDetail
