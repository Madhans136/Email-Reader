"""
FastAPI backend server for Email Reader application.
Serves email data from Gmail via Composio SDK with CORS support.
"""

import os
import sys
import smtplib
import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import parsedate_to_datetime
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Integer, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
import logging

# Import email thread processor
try:
    from email_thread_processor import process_email_thread
    EMAIL_THREAD_PROCESSOR_AVAILABLE = True
except ImportError:
    EMAIL_THREAD_PROCESSOR_AVAILABLE = False
    logging.warning("email_thread_processor module not available")

# Load environment variables at startup
load_dotenv()

# Helper function to clean reply body by removing quoted text
def clean_reply(body: str) -> str:
    """
    Remove quoted previous email content from reply body.
    Removes patterns like 'On <date> ... wrote:' and everything after.
    """
    if not body:
        return ""
    
    patterns = [
        r'On\s+.+?\s+wrote:.*$',
        r'From:\s*.+?\n.*?Sent:\s*.+?\n.*?To:\s*.+?\n',
        r'-+\s*Forwarded message\s*-+.*$',
        r'^>.*$',
    ]
    
    result = body
    for pattern in patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
    
    result = '\n'.join(line.strip() for line in result.split('\n') if line.strip())
    return result.strip()


def safe_parse_date(msg: dict) -> datetime:
    """
    Safely parse date from email message, handling multiple formats.
    Returns epoch 0 if all parsing fails.
    """
    # Try internal_date (Unix timestamp)
    internal_date = msg.get('internal_date')
    if internal_date:
        try:
            return datetime.fromtimestamp(int(internal_date) / 1000)
        except (ValueError, TypeError):
            pass
    
    # Try timestamp
    timestamp = msg.get('timestamp')
    if timestamp:
        try:
            return datetime.fromtimestamp(int(timestamp))
        except (ValueError, TypeError):
            pass
    
    # Try date string with parsedate_to_datetime
    date_str = msg.get('date')
    if date_str:
        try:
            return parsedate_to_datetime(date_str)
        except Exception:
            pass
    
    # Return epoch if all fail
    return datetime.fromtimestamp(0)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the EmailReader class
from email_reader import EmailReader

# Database setup
DATABASE_URL = "sqlite:///tickets.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy Ticket model
class TicketDB(Base):
    __tablename__ = "tickets"
    id = Column(String, primary_key=True)
    ticket_id = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    priority = Column(String, default="medium")
    status = Column(String, default="open")
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    message_id = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)

# Pydantic models
class Email(BaseModel):
    id: str
    subject: str
    thread_id: str
    body: str
    is_read: bool = False
    is_replied: bool = False
    has_ticket: bool = False

class EmailsResponse(BaseModel):
    inbox: List[Email]
    replied: List[Email]
    total_inbox: int
    total_replied: int

class Ticket(BaseModel):
    id: str
    title: str
    description: str
    priority: str
    status: str
    ticket_id: Optional[str] = None
    message_id: Optional[str] = None
    is_deleted: Optional[bool] = False

class CreateTicketRequest(BaseModel):
    title: str
    description: str
    priority: str = "medium"
    status: str = "open"
    user_email: str = ""
    original_message_id: Optional[str] = None

class ReplyRequest(BaseModel):
    ticket_id: str
    reply_body: str
    user_email: str = ""

# Email notification settings
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "")

def is_relevant_email(email: dict) -> bool:
    """
    Filter out irrelevant emails like Google security alerts.
    
    Args:
        email: Email dictionary with subject, from_email, etc.
    
    Returns:
        True if email is relevant, False if should be filtered out
    """
    if not email:
        return False
    
    subject = (email.get('subject') or '').lower()
    from_email = (email.get('from_email') or '').lower()
    body = (email.get('body') or '').lower()
    
    # Filter out Google security alerts
    if 'security' in subject and ('google' in from_email or 'google' in body):
        return False
    
    # Filter out Gmail/Calendar notifications
    if 'noreply@google.com' in from_email:
        return False
    
    # Filter out calendar invitations that are just notifications
    if 'calendar' in subject and 'invitation' in subject:
        # Keep calendar invites that require action, filter pure notifications
        if 'updated' in subject or 'notification' in subject:
            return False
    
    # Filter out Google Drive notifications
    if 'noreply@drive.google.com' in from_email:
        return False
    
    # Filter out password reset/security verification emails
    if 'password' in subject and ('reset' in subject or 'verification' in subject):
        return False
    
    # Filter out 2FA/verification codes
    if 'verification' in subject or '2-step' in subject:
        return False
    
    return True


def get_thread_output(email: dict) -> dict:
    """
    Get structured output for a single email thread.
    
    Args:
        email: Email dictionary with thread_messages
    
    Returns:
        Dict with thread_id, title, description, command
    """
    thread_messages = email.get('thread_messages', [])
    
    # Sort by date (oldest first)
    def get_date(msg):
        date_str = msg.get('date') or msg.get('internal_date') or msg.get('timestamp') or '0'
        try:
            return int(date_str)
        except:
            return 0
    
    thread_messages = sorted(thread_messages, key=get_date)
    
    # Get title from first message
    original = thread_messages[0] if thread_messages else {}
    title = (original.get('subject') or email.get('subject') or '').replace('Re: ', '').replace('re: ', '').strip()
    
    # DEBUG: Print thread details
    print(f"\n{'='*50}")
    print(f"Title: {title}")
    print(f"{'='*50}")
    print(f"Thread has {len(thread_messages)} messages")
    
    # Use email_thread_processor if available, otherwise fall back to manual processing
    if EMAIL_THREAD_PROCESSOR_AVAILABLE and thread_messages:
        try:
            # Process using LangChain-based processor
            result = process_email_thread(thread_messages)
            
            # The result now has:
            # - description = main email body content (first message)
            # - command = reply content ONLY if there are replies
            
            return {
                'thread_id': email.get('thread_id', 'unknown'),
                'title': title,
                'description': result.get('description', ''),
                'command': result.get('command', ''),
                'from_email': original.get('from_email', email.get('from_email', ''))
            }
        except Exception as e:
            logging.warning(f"email_thread_processor failed: {e}, falling back to manual processing")
    
    # Fallback: Manual processing (original logic)
    # DESCRIPTION = FIRST message (oldest, index 0) = original email
    # COMMAND = LAST message (newest) = reply
    raw_description = original.get('body') or email.get('body') or ''
    # Clean description to remove quoted reply text
    description = clean_reply(raw_description)
    
    print(f"Description (first/original message): {description[:200] if description else 'None'}...")
    
    # If there are messages, get the LAST message as command (reply)
    command = ''
    if len(thread_messages) > 1:
        print("Commands (latest reply):")
        # Get the LAST message as the command/reply
        last_message = thread_messages[-1]
        reply_body = last_message.get('body', '')
        print(f"  Raw reply: {reply_body[:100] if reply_body else 'Empty'}...")
        
        if reply_body:
            # Clean the reply body to remove quoted content
            cleaned_reply = clean_reply(reply_body)
            print(f"  Cleaned reply: {cleaned_reply[:100] if cleaned_reply else 'Empty'}...")
            command = cleaned_reply
    else:
        print("No replies in this thread")
    
    print(f"Final command length: {len(command)}")
    
    return {
        'thread_id': email.get('thread_id', 'unknown'),
        'title': title,
        'description': description,
        'command': command,
        'from_email': original.get('from_email', email.get('from_email', ''))
    }


def send_admin_notification(ticket: TicketDB):
    if not SMTP_HOST or not SMTP_USER or not NOTIFICATION_EMAIL:
        return
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = NOTIFICATION_EMAIL
        msg['Subject'] = f"New Ticket Created: {ticket.title}"
        body = f"Title: {ticket.title}\nDescription: {ticket.description}\nPriority: {ticket.priority}\nStatus: {ticket.status}\nID: {ticket.id}"
        msg.attach(MIMEText(body, 'plain'))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception:
        pass

def send_user_confirmation(ticket: TicketDB, user_email: str, original_message_id: str = None):
    if not SMTP_HOST or not SMTP_USER or not user_email:
        return None
    try:
        short_ticket_id = ticket.ticket_id if ticket.ticket_id else ticket.id[:8]
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = user_email
        msg['Subject'] = f"[Ticket #{short_ticket_id}] {ticket.title}"
        if original_message_id:
            msg['In-Reply-To'] = original_message_id
            msg['References'] = original_message_id
        body = f"Your ticket has been created!\nTitle: {ticket.title}\nDescription: {ticket.description}\nTicket ID: {short_ticket_id}"
        msg.attach(MIMEText(body, 'plain'))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return msg.get('Message-ID')
    except Exception:
        return None

def send_ticket_reply(ticket: TicketDB, user_email: str, reply_body: str, original_message_id: str = None):
    if not SMTP_HOST or not SMTP_USER or not user_email:
        return None
    try:
        short_ticket_id = ticket.ticket_id if ticket.ticket_id else ticket.id[:8]
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = user_email
        msg['Subject'] = f"[Ticket #{short_ticket_id}] {ticket.title}"
        if original_message_id:
            msg['In-Reply-To'] = original_message_id
            msg['References'] = original_message_id
        body = f"Reply to ticket #{short_ticket_id}:\n\n{reply_body}"
        msg.attach(MIMEText(body, 'plain'))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return msg.get('Message-ID')
    except Exception:
        return None

def load_environment():
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    api_key = os.getenv('COMPOSIO_API_KEY')
    base_url = os.getenv('COMPOSIO_BASE_URL')
    return api_key, base_url

# FastAPI app
app = FastAPI(title="Email Reader API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
email_reader = None

@app.on_event("startup")
async def startup_event():
    global email_reader
    api_key, base_url = load_environment()
    if not api_key:
        return
    if not base_url:
        base_url = "https://agent.composio.io"
    try:
        email_reader = EmailReader(api_key=api_key, base_url=base_url)
    except Exception:
        email_reader = None

@app.get("/")
async def root():
    return {"status": "ok", "message": "Email Reader API is running"}

@app.get("/emails", response_model=EmailsResponse)
async def get_emails(max_results: int = 50):
    """
    Get emails with filtering and proper thread handling.
    
    Each email is now processed with:
    - Filtering out irrelevant emails (Google security alerts, etc.)
    - Thread-level data included for separate processing
    """
    if not email_reader:
        return {"inbox": [], "replied": [], "total_inbox": 0, "total_replied": 0}
    
    try:
        raw_emails = email_reader.read_emails(max_results=max_results)
        
        # Debug: Print email counts
        total_count = len(raw_emails)
        unread_count = 0
        replied_count = 0
        
        # Filter out irrelevant emails first
        filtered_emails = []
        for email in raw_emails:
            # Check unread using labelIds - Gmail marks unread with "UNREAD" label
            label_ids = email.get('labelIds', email.get('label_ids', []))
            is_unread = 'UNREAD' in label_ids if label_ids else False
            
            if is_unread:
                unread_count += 1
            
            if is_relevant_email(email):
                filtered_emails.append(email)
        
        emails = []
        for idx, email in enumerate(filtered_emails, start=1):
            thread_id = email.get('thread_id', 'N/A')
            is_replied = email.get('has_user_reply', False)
            
            if is_replied:
                replied_count += 1
            
            # Get unread status from labelIds (Gmail API)
            label_ids = email.get('labelIds', email.get('label_ids', []))
            is_read = not ('UNREAD' in label_ids) if label_ids else True
            
            emails.append(Email(
                id=str(idx),
                subject=email.get('subject', 'No Subject'),
                thread_id=thread_id,
                body=email.get('body', 'No Body'),
                is_read=is_read,
                is_replied=is_replied,
                has_ticket=email.get('has_ticket', False)
            ))

        inbox_emails = [e for e in emails if not e.is_replied]
        replied_emails = [e for e in emails if e.is_replied]
        
        # Debug print counts
        print(f"Total emails fetched: {total_count}")
        print(f"Unread emails: {unread_count}")
        print(f"Replied emails: {replied_count}")
        
        return {
            "inbox": inbox_emails,
            "replied": replied_emails,
            "total_inbox": len(inbox_emails),
            "total_replied": len(replied_emails)
        }
    
    except Exception as e:
        logger.error(f"Error fetching emails: {str(e)}")
        return {"inbox": [], "replied": [], "total_inbox": 0, "total_replied": 0}


class ThreadEmailResponse(BaseModel):
    threads: List[Dict[str, Any]]
    total_threads: int
    unread_count: int = 0
    replied_count: int = 0


@app.get("/emails/by-thread", response_model=ThreadEmailResponse)
async def get_emails_by_thread(max_results: int = 50):
    """
    Get emails organized by threadId with proper filtering.
    
    - Each thread is processed separately
    - First message = description
    - Remaining messages = commands
    - Filters out irrelevant emails (Google security alerts, etc.)
    """
    if not email_reader:
        return {"threads": [], "total_threads": 0, "unread_count": 0, "replied_count": 0}
    
    try:
        # Always fetch at least 50 emails from Gmail
        fetch_count = max(max_results, 50)
        raw_emails = email_reader.read_emails(max_results=fetch_count)
        
        if not raw_emails:
            return {"threads": [], "total_threads": 0}
        
        # DEBUG: Check what's in raw_emails
        print(f"\n=== DEBUG: raw_emails count: {len(raw_emails)} ===")
        for idx, email in enumerate(raw_emails[:5]):
            has_tm = 'thread_messages' in email
            tm_count = len(email.get('thread_messages', [])) if has_tm else 0
            print(f"Email {idx}: thread_id={email.get('thread_id')}, has_thread_messages={has_tm}, thread_messages count={tm_count}")
        
        # Process each email - each email already has thread_messages with ALL messages in the thread!
        processed_threads = []
        
        for email in raw_emails:
            # Get thread_messages from the email (contains ALL messages in that thread)
            thread_messages = email.get('thread_messages', [])
            
            # Skip if no thread messages or irrelevant
            if not thread_messages:
                continue
            
            # Use first message for filtering check
            primary_email = thread_messages[0]
            
            # Filter out irrelevant emails
            if not is_relevant_email(primary_email):
                continue
            
            # Process this thread - direct description/command assignment
            # Sort thread_messages by date (oldest first) using safe date parsing
            try:
                sorted_messages = sorted(thread_messages, key=safe_parse_date)
            except Exception:
                # Skip this email if date parsing fails
                continue
            
            # Get subject from first message
            subject = primary_email.get('subject', '') or email.get('subject', '')
            title = subject.replace('Re: ', '').replace('re: ', '').strip() if subject else 'No Subject'
            
            # If only 1 message: description = first message, command = empty
            # If more than 1 message: description = first message (messages[0]), command = last message (messages[-1])
            if len(sorted_messages) == 1:
                raw_description = sorted_messages[0].get('body', '') or email.get('body', '')
                description = clean_reply(raw_description)
                command = ""
            else:
                raw_description = sorted_messages[0].get('body', '') or email.get('body', '')
                description = clean_reply(raw_description)
                # Collect all reply messages (messages[1:]) and join with "\n\n"
                cleaned_replies = []
                for msg in sorted_messages[1:]:
                    raw_body = msg.get('body', '')
                    if raw_body:
                        cleaned = clean_reply(raw_body)
                        if cleaned:
                            cleaned_replies.append(cleaned)
                command = "\n\n".join(cleaned_replies)
            
            thread_output = {
                'thread_id': email.get('thread_id', 'unknown'),
                'title': title,
                'description': description,
                'command': command,
                'from_email': primary_email.get('from_email', email.get('from_email', ''))
            }
            
            processed_threads.append(thread_output)
        
        # Sort threads by date (most recent first) using safe date parsing
        try:
            processed_threads.sort(key=lambda t: safe_parse_date({'date': t.get('description', ''), 'internal_date': t.get('thread_messages', [{}])[0].get('internal_date') if t.get('thread_messages') else None}), reverse=True)
        except Exception:
            pass  # Keep original order if sorting fails
        
        # Calculate unread and replied counts
        total_threads = len(processed_threads)
        unread_count = 0
        replied_count = 0
        
        for email in raw_emails:
            thread_messages = email.get('thread_messages', [])
            if thread_messages:
                # Check unread using labelIds from first message
                label_ids = thread_messages[0].get('labelIds', thread_messages[0].get('label_ids', []))
                if 'UNREAD' in label_ids:
                    unread_count += 1
                
                # Check replied - if thread has more than 1 message, count as replied
                if len(thread_messages) > 1:
                    replied_count += 1
        
        response_data = {
            "threads": processed_threads,
            "total_threads": total_threads,
            "unread_count": unread_count,
            "replied_count": replied_count
        }
        
        # Debug: Print counts
        print(f"Total: {total_threads}, Unread: {unread_count}, Replied: {replied_count}")
        
        return response_data
    
    except Exception as e:
        logger.error(f"Error fetching emails by thread: {str(e)}")
        return {"threads": [], "total_threads": 0}


@app.get("/tickets")
async def get_tickets(include_deleted: bool = False):
    try:
        db = SessionLocal()
        if include_deleted:
            tickets = db.query(TicketDB).all()
        else:
            tickets = db.query(TicketDB).filter(TicketDB.is_deleted == False).all()
        db.close()
        return {"tickets": [{"id": t.id, "ticket_id": t.ticket_id, "title": t.title, "description": t.description, "priority": t.priority, "status": t.status, "message_id": t.message_id, "is_deleted": t.is_deleted, "created_at": t.created_at} for t in tickets]}
    except Exception:
        return {"tickets": []}

@app.post("/create-ticket")
async def create_ticket(request: CreateTicketRequest):
    import uuid
    try:
        db = SessionLocal()
        db_id = str(uuid.uuid4())
        ticket_count = db.query(TicketDB).count()
        short_ticket_id = str(ticket_count + 1).zfill(3)
        db_ticket = TicketDB(id=db_id, ticket_id=short_ticket_id, title=request.title, description=request.description, priority=request.priority, status=request.status, message_id=None)
        db.add(db_ticket)
        db.commit()
        db.refresh(db_ticket)
        send_admin_notification(db_ticket)
        if request.user_email:
            sent_msg_id = send_user_confirmation(db_ticket, request.user_email, request.original_message_id)
            if sent_msg_id:
                db_ticket.message_id = sent_msg_id
                db.commit()
        db.close()
        return {"ticket": {"id": db_ticket.id, "ticket_id": db_ticket.ticket_id, "title": db_ticket.title, "description": db_ticket.description, "priority": db_ticket.priority, "status": db_ticket.status, "message_id": db_ticket.message_id}}
    except Exception as e:
        return {"error": str(e)}

@app.post("/reply-ticket")
async def reply_to_ticket(request: ReplyRequest):
    try:
        db = SessionLocal()
        ticket = db.query(TicketDB).filter((TicketDB.id == request.ticket_id) | (TicketDB.ticket_id == request.ticket_id)).first()
        if not ticket:
            db.close()
            return {"error": "Ticket not found"}
        sent_msg_id = send_ticket_reply(ticket, request.user_email, request.reply_body, ticket.message_id)
        if sent_msg_id:
            ticket.message_id = sent_msg_id
        reply_content = f"\n\n--- Reply to {request.user_email} ---\n{request.reply_body}"
        ticket.description = (ticket.description or "") + reply_content
        db.commit()
        db.close()
        return {"success": True, "ticket": {"id": ticket.id, "ticket_id": ticket.ticket_id, "title": ticket.title, "status": ticket.status}}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/tickets/{ticket_id}")
async def delete_ticket(ticket_id: str):
    try:
        db = SessionLocal()
        ticket = db.query(TicketDB).filter((TicketDB.id == ticket_id) | (TicketDB.ticket_id == ticket_id)).first()
        if not ticket:
            db.close()
            return {"error": "Ticket not found"}
        ticket.is_deleted = True
        ticket.status = "closed"
        db.commit()
        db.close()
        return {"success": True, "message": f"Ticket {ticket_id} marked as deleted"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/mark-ticket-created")
async def mark_ticket_created(email_id: str):
    return {"success": True, "message": "Email marked as ticket created"}

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("Starting Email Reader API Server")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
