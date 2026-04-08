# Gmail Email Reader using Composio SDK

A Python project that connects to Gmail using Composio MCP server to fetch and display emails.

## Features

- Connect to Gmail via Composio MCP server
- Fetch latest 5 emails from your Gmail account
- Extract and display:
  - Email subject
  - Email body
  - Thread ID
- Clean, formatted output in the terminal
- Modular code structure
- Error handling for edge cases

## Project Structure

```
Email_Reader/
├── main.py              # Entry point
├── email_reader.py      # Email fetching logic
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create from .env.example)
├── .env.example         # Environment variables template
└── README.md           # This file
```

## Prerequisites

- Python 3.8 or higher
- A Composio API key
- Gmail connected to your Composio account

## Setup

### 1. Install Dependencies

```bash
# Create a virtual environment (recommended)
python -m venv venv

# Activate the virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project directory:

```bash
cp .env.example .env
```

Edit the `.env` file and add your Composio API key:

```env
COMPOSIO_API_KEY=your_api_key_here
COMPOSIO_BASE_URL=https://agent.composio.io
```

### 3. Get Composio API Key

1. Sign up at [Composio](https://www.composio.ai/)
2. Navigate to your dashboard
3. Generate an API key
4. Make sure Gmail is connected/integrated in your Composio account

## Usage

Run the email reader:

```bash
python main.py
```

Expected output format:

```
==================================================
Gmail Email Reader using Composio SDK
==================================================

Connecting to Composio server...
Base URL: https://agent.composio.io

Fetching latest 5 emails from Gmail...

Subject: <email subject>
Thread ID: <thread_id>
Body: <email body>
------------
Subject: <email subject>
Thread ID: <thread_id>
Body: <email body>
------------
...
```

## Edge Cases Handled

- **No emails**: Displays appropriate message if inbox is empty
- **Empty body**: Shows "N/A" when email body is not available
- **Missing fields**: Safely handles missing subject or thread_id with "N/A"
- **Missing data key**: Gracefully handles if response structure is different
- **API errors**: Catches and displays connection/permission errors

## Code Architecture

### `main.py`
- Entry point of the application
- Handles environment variable loading from .env
- Creates EmailReader instance
- Calls `read_emails()` method
- Loops through `response["data"]`
- Formats and displays output

### `email_reader.py`
- Contains the `EmailReader` class
- Initializes `Composio` client (new SDK, NOT ComposioToolSet)
- `read_emails()` method calls `client.tools.execute(...)`
- Processes API response and extracts email data
- Safely extracts fields using `.get()` with default values

## Implementation Details

### New Composio SDK Usage

```python
# Import new SDK
from composio import Composio

# Initialize client
client = Composio(api_key=api_key, base_url=base_url)

# Execute Gmail tool
response = client.tools.execute(
    tool_name="gmail_read_emails",
    arguments={"max_results": 5}
)
```

### Response Processing

```python
# Handle different response structures
if "data" in response:
    email_list = response["data"]
else:
    email_list = [response]

# Safely extract fields
subject = email.get('subject', 'N/A')
body = email.get('body', 'N/A')
thread_id = email.get('thread_id', 'N/A')
```

## Troubleshooting

### Common Issues

1. **"COMPOSIO_API_KEY not found"**
   - Make sure you created the `.env` file
   - Verify the API key is correctly set in `.env`

2. **"No emails found"**
   - Check if Gmail is properly connected to Composio
   - Verify your API key is valid
   - Check your internet connection

3. **Import errors**
   - Make sure all dependencies are installed: `pip install -r requirements.txt`
   - Verify you're using the latest composio-core SDK

4. **Connection errors**
   - Verify the Composio base URL is correct
   - Check if Composio services are operational

## Dependencies

- **composio-core**: Latest Composio SDK with `from composio import Composio`
- **python-dotenv**: Environment variable management from .env file

## License

MIT License
