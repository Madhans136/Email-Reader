"""
Email Reader module for fetching emails from Gmail using Composio SDK.
"""

from composio import Composio
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from typing import List, Dict, Optional
import logging
import base64
import json
import uuid
import os
from dotenv import load_dotenv

# Load environment variables at startup
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailReader:
    """Handles fetching emails from Gmail using Composio SDK."""
    
    def __init__(self, api_key: str, base_url: str = None):
        """
        Initialize EmailReader with Composio client.
        
        Args:
            api_key: Composio API key
            base_url: Optional Composio MCP server base URL (for MCP-based execution)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.user_id = self._extract_user_id(base_url)
        
        # Initialize Composio client
        self.client = Composio(api_key=api_key)
        
        # Dynamically discover Gmail tools
        self.fetch_emails_tool, self.fetch_emails_version = self._discover_tool('fetch', 'email')
        self.fetch_message_tool, self.fetch_message_version = self._discover_tool('fetch', 'message')
        
        # Initialize LangChain LLM
        self.llm = ChatOpenAI(
            temperature=0,
            model="gpt-4o-mini"
        )
        
        self.prompt = PromptTemplate(
            input_variables=["subject", "body"],
            template="""
            You are an AI email assistant.
            
            Analyze the email and return JSON:
            
            {{
            "summary": "...",
            "intent": "task | request | info | spam",
            "actions": ["..."]
            }}
            
            Subject: {subject}
            Body: {body}
            """
        )
        
        self.chain = self.prompt | self.llm
        
        # Initialize ticket storage
        self.tickets = []
        
        logger.info("EmailReader initialized successfully")
    
    def _extract_user_id(self, base_url: str) -> str:
        """
        Extract user_id from MCP URL if present.
        
        Args:
            base_url: MCP URL containing user_id parameter
            
        Returns:
            Extracted user_id or default value
        """
        if base_url and "user_id=" in base_url:
            try:
                user_id = base_url.split("user_id=")[1].split("&")[0]
                return user_id
            except IndexError:
                pass
        return "default-user"
    
    def _discover_tool(self, keyword1: str, keyword2: str = None) -> tuple:
        """
        Dynamically discover a specific Gmail tool.
        
        Args:
            keyword1: First keyword to search for
            keyword2: Second keyword to search for (optional)
            
        Returns:
            Tuple of (tool_name, tool_version) or (None, None) if not found
        """
        try:
            # Get all Gmail tools
            gmail_tools = self.client.tools.get_raw_composio_tools(toolkits=['gmail'])
            
            if not gmail_tools:
                return None, None
            
            # Find a tool matching the keywords
            for tool in gmail_tools:
                name = getattr(tool, 'name', '').lower()
                slug = getattr(tool, 'slug', '')
                
                # Check if both keywords are present in name or slug
                if keyword2:
                    if keyword1 in name and keyword2 in name:
                        version = self._get_toolkit_version(tool)
                        return slug, version
                    if keyword1 in slug and keyword2 in slug:
                        version = self._get_toolkit_version(tool)
                        return slug, version
                else:
                    if keyword1 in name or keyword1 in slug:
                        version = self._get_toolkit_version(tool)
                        return slug, version
            
            return None, None
            
        except Exception:
            return None, None
    
    def _get_toolkit_version(self, tool) -> str:
        """
        Extract toolkit version from a tool object.
        
        Args:
            tool: Tool object from Composio SDK
            
        Returns:
            Toolkit version string or default version
        """
        try:
            available_versions = getattr(tool, 'available_versions', None)
            if available_versions and len(available_versions) > 0:
                return available_versions[0]
            
            deprecated = getattr(tool, 'deprecated', None)
            if deprecated:
                version = getattr(deprecated, 'version', None)
                if version:
                    return version
            
            toolkit = getattr(tool, 'toolkit', None)
            if toolkit:
                version = getattr(toolkit, 'version', None)
                if version:
                    return version
            
            return '20260330_00'
            
        except Exception:
            return '20260330_00'
    
    def read_emails(self, max_results: int = 5) -> List[Dict[str, Optional[str]]]:
        """
        Read emails from Gmail using the GMAIL_FETCH_EMAILS tool with pagination.
        
        Args:
            max_results: Maximum number of emails to fetch (default: 5)
            
        Returns:
            List of dictionaries containing email details (subject, body, thread_id)
        """
        try:
            if not self.fetch_emails_tool:
                logger.error("Gmail tools not available. Gmail may not be connected.")
                return []
            
            MAX_EMAILS = 200
            actual_max = min(max_results, MAX_EMAILS)
            
            all_emails = []
            next_page_token = None
            batch_size = 50
            fetched_count = 0
            
            while fetched_count < actual_max:
                remaining = actual_max - fetched_count
                fetch_size = min(batch_size, remaining)
                
                arguments = {"max_results": fetch_size}
                if next_page_token:
                    arguments["page_token"] = next_page_token
                
                response = self.client.tools.execute(
                    self.fetch_emails_tool,
                    arguments=arguments,
                    user_id=self.user_id,
                    version=self.fetch_emails_version
                )
                
                batch_emails = self._process_email_list(response)
                
                if not batch_emails:
                    break
                
                all_emails.extend(batch_emails)
                fetched_count += len(batch_emails)
                
                next_page_token = self._extract_page_token(response)
                
                if not next_page_token:
                    break
            
            if not all_emails:
                return []
            
            # Filter to INBOX and SENT emails
            inbox_emails = [
                email for email in all_emails
                if any(label in email.get('label_ids', []) for label in ["INBOX", "SENT"])
            ]
            
            # Group by thread and detect replies
            thread_emails_map = {}
            thread_message_count = {}
            
            for email in inbox_emails:
                thread_id = email.get('thread_id', 'N/A')
                if not thread_id or thread_id == 'N/A':
                    thread_id = f"singleton_{email.get('message_id', id(email))}"
                
                if thread_id not in thread_emails_map:
                    thread_emails_map[thread_id] = []
                    thread_message_count[thread_id] = 0
                thread_emails_map[thread_id].append(email)
                thread_message_count[thread_id] += 1
            
            # Detect user replies
            user_email = os.getenv("SMTP_USER", "").lower()
            user_replied_threads = set()
            
            for thread_id, thread_emails in thread_emails_map.items():
                for email in thread_emails:
                    subject = (email.get('subject') or '').lower()
                    from_email = (email.get('from_email') or '').lower()
                    
                    if subject.startswith('re:') or subject.startswith('re '):
                        if user_email and from_email:
                            if user_email in from_email:
                                user_replied_threads.add(thread_id)
                                break
                            elif '<' in from_email:
                                try:
                                    email_part = from_email.split('<')[1].split('>')[0].strip()
                                    if user_email in email_part:
                                        user_replied_threads.add(thread_id)
                                        break
                                except:
                                    pass
            
            # Group by thread
            thread_map = {}
            for email in inbox_emails:
                thread_id = email.get('thread_id', 'N/A')
                if not thread_id or thread_id == 'N/A':
                    thread_id = f"singleton_{email.get('message_id', id(email))}"
                
                if thread_id not in thread_map:
                    thread_map[thread_id] = []
                thread_map[thread_id].append(email)
            
            # Select original email for display
            emails = []
            for thread_id, thread_emails in thread_map.items():
                def get_subject_prefix(subject):
                    s = (subject or '').lower().strip()
                    if s.startswith('re:') or s.startswith('re '):
                        return 'reply'
                    if s.startswith('fwd:') or s.startswith('fwd ') or s.startswith('fw:'):
                        return 'forward'
                    return 'original'
                
                for email in thread_emails:
                    email['_prefix_type'] = get_subject_prefix(email.get('subject'))
                
                original_emails = [e for e in thread_emails if e.get('_prefix_type') == 'original']
                
                if original_emails:
                    emails.append(original_emails[0])
                elif thread_emails:
                    emails.append(thread_emails[0])
            
            # Add thread info to each email
            for email in emails:
                thread_id = email.get('thread_id', 'N/A')
                if thread_id == 'N/A':
                    thread_id = f"singleton_{email.get('message_id', id(email))}"
                email['thread_message_count'] = thread_message_count.get(thread_id, 1)
                email['has_user_reply'] = thread_id in user_replied_threads
                
                # Include all messages in thread (sorted by date, oldest first)
                thread_messages = thread_map.get(thread_id, [])
                if thread_messages:
                    def get_email_date(msg):
                        date_str = msg.get('date') or msg.get('internal_date') or msg.get('timestamp') or '0'
                        try:
                            return int(date_str)
                        except:
                            return 0
                    thread_messages = sorted(thread_messages, key=get_email_date)
                    email['thread_messages'] = thread_messages
            
            # Process with LLM
            # processed_ids = set()
            # for email in emails:
            #     email_id = email.get('message_id') or email.get('id')
            #     if email_id in processed_ids:
            #         continue
            #     processed_ids.add(email_id)
                
            #     analysis = self.analyze_email_with_llm(
            #         email.get("subject", ""),
            #         email.get("body", "")
            #     )
                
            #     email["summary"] = analysis.get("summary")
            #     email["intent"] = analysis.get("intent")
            #     email["actions"] = analysis.get("actions")
            #     email["is_replied"] = False
            
            for email in emails:
                email["summary"] = "N/A"
                email["intent"] = "unknown"
                email["actions"] = []
                email["is_replied"] = False
            
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            return []
    
    def analyze_email_with_llm(self, subject: str, body: str) -> dict:
        """
        Analyze an email using LangChain LLM to extract summary, intent, and actions.
        """
        try:
            response = self.chain.invoke({
                "subject": subject,
                "body": body
            })
            
            if not response or not response.content:
                return {"summary": "N/A", "intent": "unknown", "actions": []}
            
            response_text = response.content.strip()
            if not response_text:
                return {"summary": "N/A", "intent": "unknown", "actions": []}
            
            return json.loads(response_text)
        except:
            return {"summary": "N/A", "intent": "unknown", "actions": []}
    
    def _extract_page_token(self, response) -> Optional[str]:
        """Extract nextPageToken from the API response."""
        try:
            if isinstance(response, dict):
                if "data" in response:
                    data = response["data"]
                    if isinstance(data, dict):
                        return data.get("nextPageToken") or data.get("next_page_token")
                return response.get("nextPageToken") or response.get("next_page_token")
            return None
        except:
            return None
    
    def _process_email_list(self, response) -> List[Dict[str, str]]:
        """Process the email list response and extract emails."""
        emails = []
        
        try:
            data = None
            
            if isinstance(response, dict):
                if "data" in response:
                    data = response["data"]
                    if isinstance(data, dict) and "messages" in data:
                        data = data["messages"]
                elif "result" in response:
                    data = response["result"]
                else:
                    data = response
            elif isinstance(response, list):
                data = response
            else:
                data = [response] if response else []
            
            if not isinstance(data, list):
                data = [data] if data else []
            
            for email in data:
                if email is None:
                    continue
                
                subject = self._safe_extract(email, 'subject')
                thread_id = self._safe_extract(email, 'thread_id') or self._safe_extract(email, 'threadId')
                message_id = self._safe_extract(email, 'message_id') or self._safe_extract(email, 'messageId')
                email_id = self._safe_extract(email, 'id')
                
                in_reply_to = None
                references = None
                payload = email.get('payload', {})
                headers = payload.get('headers', []) if isinstance(payload, dict) else []
                
                if isinstance(payload, dict):
                    in_reply_to = payload.get('inReplyTo') or payload.get('in_reply_to')
                    references = payload.get('references')
                
                if isinstance(headers, list):
                    for header in headers:
                        header_name = header.get('name', '').lower()
                        if header_name == 'in-reply-to':
                            in_reply_to = header.get('value', '')
                        elif header_name == 'references':
                            references = header.get('value', '')
                
                body = self._safe_extract(email, 'messageText')
                if body == 'N/A':
                    preview = email.get('preview', {})
                    if preview:
                        body = self._safe_extract(preview, 'body')
                
                if body == 'N/A':
                    body = self._extract_body_from_payload(email.get('payload', {}))
                
                label_ids = email.get('labelIds', [])
                is_read = 'UNREAD' not in label_ids
                
                from_email = None
                email_date = None
                if isinstance(headers, list):
                    for header in headers:
                        header_name = header.get('name', '').lower()
                        if header_name == 'from':
                            from_email = header.get('value', '')
                        elif header_name == 'date':
                            email_date = header.get('value', '')
                
                if subject and subject != 'N/A':
                    email_data = {
                        'id': email_id if email_id != 'N/A' else message_id,
                        'subject': subject,
                        'body': body if body != 'N/A' else 'No Body',
                        'thread_id': thread_id if thread_id != 'N/A' else 'N/A',
                        'message_id': message_id if message_id != 'N/A' else None,
                        'from_email': from_email,
                        'date': email_date,
                        'in_reply_to': in_reply_to if in_reply_to else None,
                        'references': references if references else None,
                        'label_ids': label_ids,
                        'is_read': is_read,
                        'has_ticket': False
                    }
                    emails.append(email_data)
                    
        except Exception:
            pass
        
        return emails
    
    def _extract_body_from_payload(self, payload: dict) -> str:
        """Extract body content from email payload structure."""
        try:
            if not payload:
                return "N/A"
            
            parts = payload.get('parts', [])
            if parts:
                for part in parts:
                    mime_type = part.get('mimeType', '')
                    if 'text/plain' in mime_type:
                        body_data = part.get('body', {}).get('data')
                        if body_data:
                            return self._decode_body(body_data)
            
            body = payload.get('body', {})
            body_data = body.get('data')
            if body_data:
                return self._decode_body(body_data)
            
            return "N/A"
            
        except:
            return "N/A"
    
    def _decode_body(self, encoded_data: str) -> str:
        """Decode base64url-encoded body content."""
        try:
            padding = 4 - len(encoded_data) % 4
            if padding != 4:
                encoded_data += '=' * padding
            
            decoded_bytes = base64.urlsafe_b64decode(encoded_data)
            decoded_string = decoded_bytes.decode('utf-8')
            
            return decoded_string.strip()
            
        except:
            return "No Body"
    
    def create_ticket(self, title: str, description: str, priority: str = "medium") -> dict:
        """Create a new ticket."""
        ticket = {
            "id": str(uuid.uuid4()),
            "title": title,
            "description": description,
            "priority": priority,
            "status": "open"
        }
        self.tickets.append(ticket)
        return ticket
    
    def get_tickets(self) -> List[dict]:
        """Get all tickets."""
        return self.tickets
    
    def _safe_extract(self, data: dict, field: str) -> str:
        """Safely extract a field from email data with default value."""
        try:
            if isinstance(data, dict):
                value = data.get(field)
                if value and isinstance(value, str) and value.strip():
                    return value.strip()
                if field == 'thread_id' and data.get('threadId'):
                    return str(data.get('threadId'))
                if field == 'message_id' and data.get('messageId'):
                    return str(data.get('messageId'))
            return "N/A"
        except:
            return "N/A"
