# Gmail MEXC Trade Monitor

![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

An automated Python application that monitors a Gmail account for MEXC copy trading emails, tracks trades in a persistent SQLite database, and provides real-time stop-loss alerts via email. It includes a fallback LLM parser for robustness and a GUI for manual trade management.

## Key Features

- **Automatic Email Monitoring**: Periodically checks a specified Gmail account for new trade notification emails
- **Intelligent Data Parsing**: Uses regular expressions to quickly parse trade details (pair, direction, entry price, trader)
- **LLM Fallback**: If regex parsing fails due to an unexpected email format, it uses an AI model (like GPT) to extract the data, ensuring high reliability
- **Persistent Trade Database**: All trades are stored and managed in a local SQLite database
- **Real-time Price Checking**: Fetches the current market price for all open positions from the public MEXC API
- **Configurable Stop-Loss Monitoring**: Calculates the profit/loss for each open position and compares it against a user-defined stop-loss percentage
- **Email Alerts**: Automatically sends a detailed email alert to a specified address when a stop-loss threshold is triggered
- **Trader-Specific Monitoring Delays**: Configure a "monitoring delay" for specific traders, preventing premature alerts for trades that need time to develop
- **Manual Management GUI**: A simple Tkinter-based graphical user interface to view all open trades and manually close any that were missed by the automation

## How It Works

The application is composed of several modular classes:

- **main.py**: The main orchestrator. It runs on a schedule (e.g., every minute), reads the configuration, and coordinates all other components
- **GmailChecker**: Handles secure OAuth2 authentication and communication with the Gmail API to fetch new emails
- **Analyze**: The core parsing engine. It receives an email, attempts to parse it with regex, and if that fails, it calls the LLMDataExtractor. It then instructs the DatabaseManager to update the trade status
- **LLMDataExtractor**: A fallback class that uses the OpenAI API to extract trade data from email text when regex fails
- **DatabaseManager**: A centralized class for all SQLite database operations (creating tables, inserting, updating, and querying trades)
- **MexcApiClient**: A client for fetching public market data (like current prices) from the MEXC exchange API
- **PositionMonitor**: Calculates the P/L for open trades and checks if the stop-loss has been triggered
- **EmailNotifier**: Sends email alerts using Gmail's SMTP server and a secure App Password
- **TraderCooldownManager**: Manages the monitoring delay for each trader based on the `trader_config.json` file
- **gui_manager.py**: A separate, standalone Tkinter application for manually viewing and closing trades in the database

## Prerequisites

- Python 3.9 or higher
- A Google Account with 2-Step Verification enabled
- An OpenAI API Key (optional, but required for the LLM fallback feature)

## Installation & Setup

### 1. Clone the Repository

Clone this project to your local machine or download and extract the source files into a folder.

```bash
git clone <repository_url>
cd GmailMexcAnalyzer
```

### 2. Create a Python Virtual Environment

It's highly recommended to use a virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
```

### 3. Install Dependencies

Install all the required Python libraries.

```bash
pip install -r requirements.txt
```

> **Note**: If you don't have a `requirements.txt` file, create one with `pip freeze > requirements.txt` after installing the packages mentioned in the previous steps: `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib`, `python-dotenv`, `openai`, `requests`

### 4. Set Up Google Cloud Project & Credentials

To read your Gmail, you need to grant permission via the Google Cloud Console.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project
2. Enable the **Gmail API** for your project
3. Configure the **OAuth consent screen**. Choose "External" and add your own email as a "Test user"
4. Create new credentials of type **"OAuth client ID"**. Select "Desktop app" as the application type
5. Download the credentials JSON file and rename it to `credentials.json`. Place this file in the root directory of the project

### 5. Generate a Google App Password

To send email alerts, you need a special password for the script.

1. Go to your [Google Account's Security settings](https://myaccount.google.com/security)
2. Make sure **2-Step Verification** is ON
3. Click on **"App passwords"** (it's located inside the 2-Step Verification settings)
4. Generate a new password for an app with a custom name (e.g., "Mexc Stoploss Script")
5. Copy the 16-character password that is generated. You will use this in the configuration file

## Configuration

Before running the application, you need to configure your settings.

### 1. Environment Variables

Copy the `.env.example` file to `.env` (or create it from scratch).

```env
# .env

# Gmail API scope (readonly is safest for monitoring)
SCOPES='https://www.googleapis.com/auth/gmail.readonly'

# Base Gmail search query. It will be appended with a timestamp.
# Use 'label:mexc' for better filtering if you auto-label your MEXC emails.
QUERY='is:unread in:inbox'

# --- Stop-Loss & Email Alert Configuration ---

# The P/L percentage that triggers an alert (use a negative number).
STOPLOSS_PERCENTAGE=-5.0

# Email address FROM which alerts are sent (your Gmail address).
SENDER_EMAIL='your-email@gmail.com'

# The 16-character App Password you generated in the setup.
SENDER_APP_PASSWORD='abcdefghijklmnop'

# Email address TO which alerts are sent.
RECIPIENT_EMAIL='your-alert-recipient@example.com'

# --- LLM Fallback (Optional) ---
OPENAI_API_KEY='sk-your-openai-api-key'
```

### 2. Trader Monitoring Delays

Edit the `trader_config.json` file to specify how long the script should wait after a trade is opened before it starts monitoring its stop-loss.

```json
[
  {
    "trader": "Limer",
    "monitor_na": "20m"
  },
  {
    "trader": "SomeOtherTrader",
    "monitor_na": "5m"
  }
]
```

**Supported units**: `m` (minutes), `h` (hours).

Traders not listed in this file will be monitored immediately (0 minute delay).

## Usage

The project has two main entry points: the automated monitor and the manual GUI.

### 1. Running the Automated Monitor

This script is designed to be run on a schedule (e.g., every minute) by a system utility like cron (Linux/macOS) or Task Scheduler (Windows).

To run it manually for testing:

```bash
python main.py
```

> **Note**: The first time you run it, a browser window will open asking you to authorize the application to access your Gmail. You only need to do this once.

### 2. Using the Manual Trade Manager GUI

If you miss a "close" email and a trade remains open in the database, you can use the GUI to manually close it.

Run the GUI from your terminal:

```bash
python gui_manager.py
```

A window will appear showing all open trades in a table. Select a trade and click **"Sluit Geselecteerde Trade"** to close it.

## Project Structure

```
GmailMexcAnalyzer/
├── .venv/
├── src/
│   ├── __init__.py
│   ├── analyzer.py
│   ├── database_manager.py
│   ├── email_notifier.py
│   ├── gmail_checker.py
│   ├── llm_extractor.py
│   ├── mexc_api_client.py
│   ├── position_monitor.py
│   └── trader_cooldown_manager.py
├── .env
├── credentials.json
├── gui_manager.py
├── main.py
├── trader_config.json
└── README.md
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.