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


def clean_command_reply(body: str) -> str:
    """
    Keep only the new reply text from a thread reply.
    This is stricter than clean_reply because command should not include
    the quoted original email content.
    """
    cleaned = clean_reply(body)
    if not cleaned:
        return ""

    cut_patterns = [
        r'\n_{5,}.*$',
        r'\n-{5,}.*$',
        r'\nSubject:\s.*$',
        r'\nFrom:\s.*$',
        r'\nOn\s+.+?\s+wrote:.*$',
    ]

    for pattern in cut_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)

    return cleaned.strip()


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
# DATABASE_URL = "sqlite:////tmp/tickets.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy Ticket model
class TicketDB(Base):
    __tablename__ = "tickets"
    id = Column(String, primary_key=True)
    ticket_id = Column(String, nullable=True)
    thread_id = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    commands = Column(String, nullable=True)
    priority = Column(String, default="medium")
    status = Column(String, default="open")
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    message_id = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False)
    source_email_id = Column(String, nullable=True)
    sender_name = Column(String, nullable=True)
    sender_email = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

# Add columns if they don't exist (migration for existing databases)
def migrate_database():
    """Add missing columns to existing tickets table."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # Check if column exists
            result = conn.execute(text("PRAGMA table_info(tickets)"))
            columns = [row[1] for row in result]
            
            # Add thread_id if missing
            if 'thread_id' not in columns:
                conn.execute(text("ALTER TABLE tickets ADD COLUMN thread_id VARCHAR"))
                print("Database migrated: added thread_id column")

            if 'commands' not in columns:
                conn.execute(text("ALTER TABLE tickets ADD COLUMN commands VARCHAR"))
                print("Database migrated: added commands column")
            
            # Add source_email_id if missing
            if 'source_email_id' not in columns:
                conn.execute(text("ALTER TABLE tickets ADD COLUMN source_email_id VARCHAR"))
                print("Database migrated: added source_email_id column")
            
            # Add sender_name if missing
            if 'sender_name' not in columns:
                conn.execute(text("ALTER TABLE tickets ADD COLUMN sender_name VARCHAR"))
                print("Database migrated: added sender_name column")
            
            # Add sender_email if missing
            if 'sender_email' not in columns:
                conn.execute(text("ALTER TABLE tickets ADD COLUMN sender_email VARCHAR"))
                print("Database migrated: added sender_email column")
            
            if 'source_email_id' in columns and 'sender_name' in columns and 'sender_email' in columns:
                print("Database check: all columns already exist")
            
            conn.commit()
    except Exception as e:
        print(f"Database migration warning: {e}")

# Run migration on startup
migrate_database()

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
            cleaned_reply = clean_command_reply(reply_body)
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


def parse_sender(from_header: str) -> tuple:
    """
    Parse sender name and email from "From" header.
    
    Args:
        from_header: The From header string (e.g., "Name <email@example.com>" or "Name [email@example.com](mailto:email@example.com)")
    
    Returns:
        Tuple of (sender_name, sender_email)
    """
    if not from_header:
        return '', ''
    
    # Clean up the from_header - remove markdown link format if present
    # Pattern: "Name [email@example.com](mailto:email@example.com)"
    markdown_match = re.match(r'^"?(.+?)"?\s*\[([^\]]+)\]\(mailto:[^)]+\)', from_header)
    if markdown_match:
        name = markdown_match.group(1).strip()
        email = markdown_match.group(2).strip()
        return name, email
    
    # Pattern: "Name <email@example.com>"
    angle_match = re.match(r'^"?(.+?)"?\s*<(.+?)>$', from_header)
    if angle_match:
        name = angle_match.group(1).strip()
        email = angle_match.group(2).strip()
        print("++++++++++++++")
        print(name, email, "I am the name of the sender")
        return name, email
    
    # If no match, try to extract just the email
    email_match = re.search(r'[\w.-]+@[\w.-]+\.\w+', from_header)
    if email_match:
        # Try to extract name before email
        parts = from_header.split(email_match.group(0))
        name = parts[0].strip().strip('"<>')
        return name, email_match.group(0)
    
    # If no match, just return the whole thing as email
    return '', from_header.strip()


def check_ticket_exists(source_email_id: str, thread_id: str) -> bool:
    try:
        db = SessionLocal()

        existing = None

        if source_email_id and source_email_id != "unknown":
            existing = db.query(TicketDB).filter(
                TicketDB.source_email_id == source_email_id
            ).first()

        if not existing and thread_id and thread_id != "unknown":
            existing = db.query(TicketDB).filter(
                TicketDB.thread_id == thread_id
            ).first()

        db.close()
        return existing is not None

    except Exception as e:
        print("check_ticket_exists error:", e)
        return False


def create_ticket_from_email(email_data: dict) -> Optional[TicketDB]:
    import uuid
    try:
        db = SessionLocal()

        source_email_id = email_data.get('id', '')
        thread_id = email_data.get('thread_id', '')

        existing_ticket = None

        if source_email_id and source_email_id != "unknown":
            existing_ticket = db.query(TicketDB).filter(
                TicketDB.source_email_id == source_email_id
            ).first()

        if not existing_ticket:
            if thread_id and thread_id != "unknown":
                existing_ticket = db.query(TicketDB).filter(
                    TicketDB.thread_id == thread_id
                ).first()

        if existing_ticket:
            new_command = email_data.get('command', '')
            if new_command:
                existing_ticket.commands = new_command
                db.commit()
                print(f"Updated commands for ticket: {existing_ticket.ticket_id}")
            if not existing_ticket.sender_name and not existing_ticket.sender_email:
                from_field = email_data.get('from', '') or email_data.get('from_email', '') or ''
                sender_name, sender_email = parse_sender(from_field)
                if sender_name or sender_email:
                    existing_ticket.sender_name = sender_name
                    existing_ticket.sender_email = sender_email
                    db.commit()
                    print(f"Updated sender for ticket: {existing_ticket.ticket_id}")
            db.close()
            return existing_ticket

        # Debug log
        email_subject = email_data.get('subject', 'No Subject')
        print("Creating ticket for email:", email_subject)

        # Create new ticket
        db_id = str(uuid.uuid4())
        ticket_count = db.query(TicketDB).count()
        short_ticket_id = str(ticket_count + 1).zfill(3)

        subject = email_data.get('subject', 'No Subject')
        title = subject.replace('Re: ', '').replace('re: ', '').strip()

        body = email_data.get('body', '') or 'No content'

        from_field = email_data.get('from', '') or email_data.get('from_email', '') or ''
        sender_name, sender_email = parse_sender(from_field)

        db_ticket = TicketDB(
            id=db_id,
            ticket_id=short_ticket_id,
            thread_id=thread_id,
            title=title,
            description=body[:5000] if body else 'No content',
            commands=email_data.get('command', ''),
            priority="medium",
            status="open",
            created_at=datetime.utcnow().isoformat(),
            message_id=None,
            source_email_id=source_email_id if source_email_id != "unknown" else None,
            sender_name=sender_name,
            sender_email=sender_email
        )

        db.add(db_ticket)
        db.commit()
        db.refresh(db_ticket)
        db.close()

        print(f"Successfully created ticket: #{short_ticket_id} - {title}")
        return db_ticket

    except Exception as e:
        print(f"Error creating ticket from email: {e}")
        return None
    
def is_ticket_email(email: dict) -> bool:
    subject = (email.get('subject') or '').lower()
    body = (email.get('body') or '').lower()

    # reject promotional/newsletter mails
    blocked_keywords = [
        'welcome',
        'lovable',
        'cline',
        'gemini',
        'composio',
        'credits',
        'improve',
        'workflow',
        'kanban',
        'ship',
        'using',
        'how to',
        'announcement'
    ]

    if any(word in subject for word in blocked_keywords):
        return False

    # allow only issue/request mails
    allowed_keywords = [
        'issue',
        'error',
        'request',
        'problem',
        'unable',
        'not working',
        'failed',
        'access',
        'wifi',
        'battery',
        'login'
    ]

    return any(word in subject or word in body for word in allowed_keywords)

# FastAPI app
app = FastAPI(title="Email Reader API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
email_reader = None

# ============ CACHE LAYER FOR PERFORMANCE OPTIMIZATION ============
import time

# Cache configuration
CACHE_TTL_SECONDS = 300  # Cache valid for 60 seconds

# In-memory cache storage
cache = {
    "emails": [],  # Cached email threads
    "tickets": [],  # Cached tickets list
    "last_fetch_time": 0,  # Timestamp of last Gmail fetch
    "last_tickets_time": 0,  # Timestamp of last tickets fetch
    "processed_thread_ids": set()  # Track which thread IDs have been processed
}

def is_cache_valid(last_time: float) -> bool:
    """Check if cache is still valid based on TTL."""
    return (time.time() - last_time) < CACHE_TTL_SECONDS

def get_cached_emails():
    """Get cached emails if available and valid."""
    if is_cache_valid(cache["last_fetch_time"]):
        print(f"[CACHE HIT] Returning {len(cache['emails'])} cached emails")
        return cache["emails"]
    return None

def set_cached_emails(emails: list):
    """Set cached emails with current timestamp."""
    cache["emails"] = emails
    cache["last_fetch_time"] = time.time()
    print(f"[CACHE SET] Cached {len(emails)} emails at {time.time()}")

def get_cached_tickets():
    """Get cached tickets if available and valid."""
    if is_cache_valid(cache["last_tickets_time"]):
        print(f"[CACHE HIT] Returning {len(cache['tickets'])} cached tickets")
        return cache["tickets"]
    return None

def set_cached_tickets(tickets: list):
    """Set cached tickets with current timestamp."""
    cache["tickets"] = tickets
    cache["last_tickets_time"] = time.time()
    print(f"[CACHE SET] Cached {len(tickets)} tickets at {time.time()}")

def is_thread_processed(thread_id: str) -> bool:
    """Check if a thread has already been processed."""
    return thread_id in cache["processed_thread_ids"]

def mark_thread_processed(thread_id: str):
    """Mark a thread as processed."""
    cache["processed_thread_ids"].add(thread_id)

def clear_cache():
    """Clear all cache (for testing/reset)."""
    cache["emails"] = []
    cache["tickets"] = []
    cache["last_fetch_time"] = 0
    cache["last_tickets_time"] = 0
    cache["processed_thread_ids"] = set()
    print("[CACHE] Cache cleared")

@app.on_event("startup")
async def startup_event():
    # Keep startup fast. Gmail/Composio is initialized only when an email sync is requested.
    return


def ensure_email_reader() -> bool:
    global email_reader
    if email_reader:
        return True

    api_key, base_url = load_environment()
    if not api_key:
        return False
    if not base_url:
        base_url = "https://agent.composio.io"
    try:
        email_reader = EmailReader(api_key=api_key, base_url=base_url)
        return True
    except Exception:
        email_reader = None
        return False

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
    if not ensure_email_reader():
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
async def get_emails_by_thread(max_results: int = 50, force: bool = False):
    """
    Get emails organized by threadId with proper filtering.
    Uses caching to avoid repeated Gmail API calls within 60 seconds.
    """
    cached = get_cached_emails()
    if cached is not None and not force:
        return {
            "threads": cached,
            "total_threads": len(cached),
            "unread_count": 0,
            "replied_count": 0
        }

    if not force:
        return {"threads": [], "total_threads": 0, "unread_count": 0, "replied_count": 0}

    if not ensure_email_reader():
        if cached is not None:
            return {
                "threads": cached,
                "total_threads": len(cached),
                "unread_count": 0,
                "replied_count": 0
            }
        return {"threads": [], "total_threads": 0, "unread_count": 0, "replied_count": 0}
    
    try:
        print("[CACHE CHECK] Fetching emails from Gmail for new threads...")
        
        # Always fetch at least 50 emails from Gmail
        fetch_count = max(max_results, 50)
        raw_emails = email_reader.read_emails(max_results=fetch_count)
        
        if not raw_emails:
            if cached is not None:
                print("[CACHE FALLBACK] Gmail fetch returned no emails, returning cached threads")
                return {
                    "threads": cached,
                    "total_threads": len(cached),
                    "unread_count": 0,
                    "replied_count": 0
                }
            return {"threads": [], "total_threads": 0}
        
        # Sort fetched email threads by newest message date first
        try:
            raw_emails = sorted(raw_emails, key=lambda e: safe_parse_date(e), reverse=True)
        except Exception:
            pass

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
            thread_id = email.get('thread_id', 'unknown')
            subject = primary_email.get('subject', '') or email.get('subject', '')
            print(f"[THREAD] fetched subject='{subject}' thread_id='{thread_id}' id='{email.get('id', 'unknown')}'")
            
            # Filter out irrelevant emails
            if not is_relevant_email(primary_email):
                print("  skipped irrelevant primary email")
                continue
            
            # Process this thread - direct description/command assignment
            # Sort thread_messages by date (oldest first) using safe date parsing
            try:
                sorted_messages = sorted(thread_messages, key=safe_parse_date)
            except Exception:
                # Skip this email if date parsing fails
                print(f"  skipped due to date parse failure for thread_id='{thread_id}'")
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
                        cleaned = clean_command_reply(raw_body)
                        if cleaned:
                            cleaned_replies.append(cleaned)
                command = "\n\n".join(cleaned_replies)
            
            # Return raw email data: id, subject, from, date, body
            thread_output = {
                'id': email.get('id', 'unknown'),   # actual email id
                'thread_id': email.get('thread_id', 'unknown'),
                'subject': title,
                'from': primary_email.get('from_email', email.get('from_email', '')),
                'date': primary_email.get('date', email.get('date', '')),
                'body': description if description else email.get('body', ''),
                'command': command 
            }

            thread_id = email.get('thread_id', 'unknown')
            print(f"[THREAD] processing subject='{title}' thread_id='{thread_id}' id='{thread_output['id']}'")
            if not is_ticket_email(thread_output):
                print("  skipped non-ticket thread based on is_ticket_email")
            else:
                if is_thread_processed(thread_id):
                    print("  thread already processed, checking for command update")
                ticket = create_ticket_from_email(thread_output)
                if ticket:
                    if not is_thread_processed(thread_id):
                        mark_thread_processed(thread_id)
                        print("  marked thread as processed")
                    print(f"  ticket created/updated: ticket_id={ticket.ticket_id} source_email_id={ticket.source_email_id}")
                else:
                    print("  ticket creation/update failed or skipped")

            processed_threads.append(thread_output)
        
        # Sort threads by date (most recent first) using safe date parsing
        try:
            # processed_threads.sort(key=lambda t: safe_parse_date({'date': t.get('description', ''), 'internal_date': t.get('thprocessed_threads.sortread_messages', [{}])[0].get('internal_date') if t.get('thread_messages') else None}), reverse=True)

            processed_threads.sort(
                key=lambda t: safe_parse_date({'date': t.get('date', '')}),
                reverse=True
            )
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
        
        # Cache the results
        set_cached_emails(processed_threads)
        
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
    """Get lightweight ticket list - only returns essential fields for list display."""
    try:
        db = SessionLocal()
        if include_deleted:
            # Only select needed columns for faster query
            tickets = db.query(
                TicketDB.id,
                TicketDB.ticket_id,
                TicketDB.thread_id,
                TicketDB.title,
                TicketDB.description,
                TicketDB.status,
                TicketDB.created_at
            ).all()
        else:
            tickets = db.query(
                TicketDB.id,
                TicketDB.ticket_id,
                TicketDB.thread_id,
                TicketDB.title,
                TicketDB.description,
                TicketDB.status,
                TicketDB.created_at
            ).filter(TicketDB.is_deleted == False).all()
        db.close()

        thread_dates = {
            email.get('thread_id'): email.get('date', '')
            for email in cache.get("emails", [])
            if email.get('thread_id')
        }

        def ticket_sort_time(ticket):
            thread_date = thread_dates.get(ticket.thread_id)
            if thread_date:
                return safe_parse_date({'date': thread_date}).timestamp()
            try:
                return datetime.fromisoformat(ticket.created_at).timestamp()
            except Exception:
                return 0

        tickets = sorted(tickets, key=ticket_sort_time, reverse=True)
        
        filtered_tickets = []
        for t in tickets:
            title = (t.title or "").strip().lower()
            desc = (t.description or "").strip().lower()
        
            # skip junk tickets
            if title in ["hi", "hello", "test"] or desc in ["hi", "hello", "test"]:
                continue
            
            filtered_tickets.append({
                "id": t.id,
                "ticket_id": t.ticket_id,
                "title": t.title,
                "description": t.description[:100] if t.description else "",
                "status": t.status,
                "created_at": t.created_at
            })
        
        return {"tickets": filtered_tickets}
                
        # Return lightweight data for list display
        # return {}
    except Exception:
        return {"tickets": []}

@app.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    """Get a single ticket by ID or ticket_id."""
    try:
        db = SessionLocal()
        ticket = db.query(TicketDB).filter(
            (TicketDB.id == ticket_id) | (TicketDB.ticket_id == ticket_id)
        ).first()
        db.close()
        
        if not ticket:
            return {"error": "Ticket not found"}
        
        # Get stored sender info
        sender_name = ticket.sender_name or ''
        sender_email = ticket.sender_email or ''
        
        # If no stored sender info, try to get from cached emails
        if not sender_name and not sender_email:
            try:
                # Check cached emails for sender info
                cached_emails = cache.get("emails", [])
                for email in cached_emails:
                    source_matches = ticket.source_email_id and email.get('id') == ticket.source_email_id
                    thread_matches = ticket.thread_id and email.get('thread_id') == ticket.thread_id
                    if source_matches or thread_matches:
                        from_field = email.get('from', '') or ''
                        sender_name, sender_email = parse_sender(from_field)
                        print(f"Found sender from cached email: {sender_name} <{sender_email}>")
                        break
            except Exception as e:
                print(f"Error getting sender from cache: {e}")
        
        return {
            "ticket": {
                "id": ticket.id,
                "ticket_id": ticket.ticket_id,
                "title": ticket.title,
                "description": ticket.description,
                "commands": ticket.commands,
                "priority": ticket.priority,
                "status": ticket.status,
                "message_id": ticket.message_id,
                "is_deleted": ticket.is_deleted,
                "created_at": ticket.created_at,
                "source_email_id": ticket.source_email_id,
                "sender_name": sender_name,
                "sender_email": sender_email
            }
        }
    except Exception as e:
        return {"error": str(e)}

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

@app.post("/cache/clear")
async def clear_cache_endpoint():
    """Clear the in-memory cache (for testing/reset)."""
    clear_cache()
    return {"success": True, "message": "Cache cleared"}

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("Starting Email Reader API Server")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
