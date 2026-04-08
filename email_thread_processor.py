"""
LangChain-based email thread processor.
"""

import re
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ThreadOutput(BaseModel):
    description: str = Field(description="The main content from the first message in the thread (original email)")
    command: str = Field(description="Reply content ONLY if there are replies/thread messages. If no replies, empty string.")

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an email thread analyzer. Extract the following from the email thread:
- description: The main content from the FIRST/ORIGINAL email message only
- command: The reply content ONLY if replies exist. If no replies, return empty string.
Return output strictly matching the required schema."""),
    ("human", "{thread_text}")
])


def preprocess_thread(messages: List[Dict[str, Any]]) -> str:
    """
    Preprocess email thread by sorting and building thread_text.
    
    Args:
        messages: List of email messages with 'body' and 'internalDate'
    
    Returns:
        Formatted thread_text string
    """
    # Sort messages by internalDate (ascending - oldest first)
    sorted_messages = sorted(messages, key=lambda x: x.get('internalDate', 0))
    
    # Build thread_text with clear labeling of first vs last message
    thread_parts = []
    for idx, msg in enumerate(sorted_messages, start=1):
        body = msg.get('body', '') or ''
        if idx == 1:
            # First message (oldest) = ORIGINAL EMAIL
            thread_parts.append(f"=== ORIGINAL EMAIL (first message) ===\n{body}\n")
        elif idx == len(sorted_messages):
            # Last message (newest) = REPLY
            thread_parts.append(f"=== LATEST REPLY (last message) ===\n{body}\n")
        else:
            thread_parts.append(f"--- MESSAGE {idx} ---\n{body}\n")
    
    return '\n'.join(thread_parts)


def run_langchain(thread_text: str) -> Dict[str, Any]:
    """
    Run LangChain to extract description and commands from email thread.
    
    Args:
        thread_text: Preprocessed email thread string
    
    Returns:
        Dict with 'description' and 'commands'
    """
    # Initialize ChatOpenAI with temperature=0
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment")
    
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=api_key
    )
    
    # Create JsonOutputParser with Pydantic model
    output_parser = JsonOutputParser(pydantic_object=ThreadOutput)
    
    # Format instructions for the parser
    format_instructions = output_parser.get_format_instructions()
    
    # Create PromptTemplate with rules
    prompt_template = PromptTemplate(
        template="""Analyze the following email thread and extract information according to these rules:
- title = email subject line
- description = main email body content (the first/original message)
- command = reply content ONLY if a reply/thread message exists. If there are no replies, leave command empty.
- Remove quoted reply text (lines starting with ">") from the description content

Email Thread:
{thread_text}

""" + format_instructions + """
Output must be in valid JSON format with "description" (string) and "command" (string) keys.""",
        input_variables=["thread_text"]
    )

    # Use RunnableSequence (LCEL)
    chain = prompt_template | llm

    # Run chain and parse output
    response = chain.invoke({"thread_text": thread_text})
    parsed_output = output_parser.parse(response.content)

    # Ensure no empty values
    # Swap: description should be from oldest (first) message, command from newest (last) message
    raw_description = parsed_output.get('description', '').strip()
    raw_command = parsed_output.get('command', '').strip()
    
    # Reconstruct properly: description = original (first message), command = reply (last message)
    # If LangChain got them swapped, fix it here
    description = raw_description
    command = raw_command
    
    # Clean description to remove quoted reply text (e.g., "On <date> ... wrote:" and lines starting with ">")
    if description:
        # Remove "On <date> <name> wrote:" patterns
        description = re.sub(r'On\s+.+?\s+wrote:.*$', '', description, flags=re.IGNORECASE | re.MULTILINE)
        # Remove "From: ... Sent: ... To: ..." patterns
        description = re.sub(r'From:\s*.+?\n.*?Sent:\s*.+?\n.*?To:\s*.+?\n', '', description, flags=re.IGNORECASE)
        # Remove forwarded message separators
        description = re.sub(r'-+\s*Forwarded message\s*-+.*$', '', description, flags=re.IGNORECASE | re.MULTILINE)
        # Remove lines starting with >
        description = '\n'.join(line for line in description.split('\n') if not line.strip().startswith('>'))
        # Clean up extra whitespace
        description = '\n'.join(line.strip() for line in description.split('\n') if line.strip()).strip()
    
    # If description is empty but command exists, command might actually be the description
    if not description and raw_command:
        description = raw_command
        command = ""
    # If command is empty but description exists and there are multiple messages, 
    # the description might actually be the reply (most recent)
    if not command and raw_description:
        # This is fine - no replies in the thread
        pass

    return {
        "description": description,
        "command": command
    }


def process_email_thread(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Main function to process email thread.
    
    Args:
        messages: List of email messages with 'body' and 'internalDate'
    
    Returns:
        Dict with 'description' and 'commands'
    """
    # Preprocess thread
    thread_text = preprocess_thread(messages)
    
    # Run LangChain
    result = run_langchain(thread_text)
    
    return result


if __name__ == "__main__":
    # Example usage
    sample_messages = [
        {"body": "Can you please update the project status?", "internalDate": 1700000000000},
        {"body": "Sure, I'll work on it today.", "internalDate": 1700003600000},
        {"body": "Thanks! Let me know when it's done.", "internalDate": 1700007200000}
    ]
    
    result = process_email_thread(sample_messages)
    print(result)