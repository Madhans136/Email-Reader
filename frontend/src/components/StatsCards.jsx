import React from 'react'

function StatsCards({ stats }) {
  // Default values if stats are undefined
  const openedEmails = stats?.openedEmails ?? 0
  const unreadEmails = stats?.unreadEmails ?? 0
  const repliedEmails = stats?.repliedEmails ?? 0

  const statCards = [
    {
      id: 'opened',
      title: 'Opened Emails',
      value: openedEmails,
      icon: '📖',
      color: 'green',
      bgGradient: 'from-green-500/20 to-green-600/10',
      borderColor: 'border-green-500/30'
    },
    {
      id: 'unread',
      title: 'Unread Emails',
      value: unreadEmails,
      icon: '📩',
      color: 'amber',
      bgGradient: 'from-amber-500/20 to-amber-600/10',
      borderColor: 'border-amber-500/30'
    },
    {
      id: 'replied',
      title: 'Replied Emails',
      value: repliedEmails,
      icon: '💬',
      color: 'blue',
      bgGradient: 'from-blue-500/20 to-blue-600/10',
      borderColor: 'border-blue-500/30'
    }
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {statCards.map((card) => (
        <div
          key={card.id}
          className={`bg-gradient-to-br ${card.bgGradient} border ${card.borderColor} rounded-lg p-3 transition-all duration-300 hover:scale-105 hover:shadow-lg`}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xl">{card.icon}</span>
            <div className={`w-2 h-2 rounded-full bg-${card.color}-400 animate-pulse`}></div>
          </div>
          <h3 className="text-dark-text-muted text-sm font-medium mb-1">{card.title}</h3>
          <p className="text-xl font-bold text-dark-text">
            {card.value}
          </p>
        </div>
      ))}
    </div>
  )
}

export default StatsCards