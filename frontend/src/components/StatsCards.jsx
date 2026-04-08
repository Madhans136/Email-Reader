import React from 'react'

function StatsCards({ stats }) {
  const cards = [
    { label: 'Opened', value: stats?.openedEmails || 0, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    { label: 'Unread', value: stats?.unreadEmails || 0, color: 'text-amber-400', bg: 'bg-amber-500/10' },
    { label: 'Replied', value: stats?.repliedEmails || 0, color: 'text-indigo-400', bg: 'bg-indigo-500/10' }
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      {cards.map((card, i) => (
        <div key={i} className="bg-[#161B26] border border-[#262D3D] p-6 rounded-2xl hover:border-gray-700 transition-all">
          <div className="flex justify-between items-center mb-4">
            <p className="text-xs font-bold uppercase tracking-widest text-gray-500">{card.label}</p>
            <div className={`w-2 h-2 rounded-full ${card.color.replace('text', 'bg')}`} />
          </div>
          <p className="text-3xl font-bold text-white">{card.value}</p>
          <p className="text-[10px] text-gray-500 mt-2 font-medium">REAL-TIME UPDATE</p>
        </div>
      ))}
    </div>
  )
}

export default StatsCards