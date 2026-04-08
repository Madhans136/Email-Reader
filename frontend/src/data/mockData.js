// Mock data for the email reader dashboard
export const mockEmails = [
  {
    id: "1",
    subject: "Meeting Update",
    body: "Hi team,\n\nPlease attend the meeting at 10AM tomorrow. We will discuss the new project timeline and resource allocation.\n\nLooking forward to seeing everyone there.\n\nBest regards,\nJohn",
    thread_id: "abc123",
    sender: "john@company.com",
    timestamp: "2026-03-31 09:30 AM"
  },
  {
    id: "2",
    subject: "Project Budget Review",
    body: "Hello,\n\nI have attached the Q1 budget review document. Please review the highlighted sections and provide your feedback by end of week.\n\nKey highlights:\n- 15% under budget\n- New vendor contracts approved\n- Q2 projections look promising\n\nThanks,\nSarah",
    thread_id: "def456",
    sender: "sarah@company.com",
    timestamp: "2026-03-30 03:45 PM"
  },
  {
    id: "3",
    subject: "Weekly Status Report",
    body: "Team,\n\nHere is our weekly status update:\n\n- Frontend: 80% complete\n- Backend: 65% complete\n- Testing: Scheduled for next week\n- Documentation: In progress\n\nPlease review and let me know if you have any concerns.\n\nRegards,\nMike",
    thread_id: "ghi789",
    sender: "mike@company.com",
    timestamp: "2026-03-30 11:20 AM"
  },
  {
    id: "4",
    subject: "New Client Onboarding",
    body: "Hi team,\n\nExciting news! We have a new client joining us next month. They are in the fintech sector and require:\n\n- Custom API integration\n- Real-time data processing\n- 24/7 support\n\nI will schedule a kickoff meeting soon.\n\nBest,\nEmily",
    thread_id: "jkl012",
    sender: "emily@company.com",
    timestamp: "2026-03-29 04:15 PM"
  },
  {
    id: "5",
    subject: "Code Review Request",
    body: "Hi,\n\nI have pushed the new authentication module for code review. Main changes include:\n\n- OAuth 2.0 integration\n- JWT token handling\n- Session management\n\nPlease review by Thursday.\n\nThanks,\nAlex",
    thread_id: "mno345",
    sender: "alex@company.com",
    timestamp: "2026-03-29 02:30 PM"
  },
  {
    id: "6",
    subject: "Server Maintenance Notice",
    body: "Dear All,\n\nPlease note that server maintenance is scheduled for this Saturday from 2 AM to 6 AM EST.\n\nDuring this window:\n- Email services may be intermittent\n- Deployments will be disabled\n- Monitoring alerts will be silenced\n\nPlan accordingly.\n\nIT Team",
    thread_id: "pqr678",
    sender: "it-support@company.com",
    timestamp: "2026-03-28 10:00 AM"
  }
]

export const mockStats = {
  emailsInQueue: 12,
  emailsProcessed: 847,
  tokensGenerated: "2.4M",
  commandsExecuted: 156
}
