# Gmail MEXC Trade Monitor

![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

An automated Python application that monitors a Gmail account for MEXC copy trading emails, tracks trades in a persistent SQLite database, and provides multi-stage, trader-specific stop-loss alerts via email. It includes a fallback LLM parser for robustness and a GUI for manual trade management.

## Key Features

- **Automatic Email Monitoring**: Periodically checks a specified Gmail account for new trade notification emails.
- **Intelligent Data Parsing**: Uses regular expressions to quickly parse trade details (pair, direction, entry price, trader).
- **LLM Fallback**: If regex parsing fails due to an unexpected email format, it uses an AI model (like GPT) to extract the data, ensuring high reliability.
- **Persistent Trade Database**: All trades are stored and managed in a local SQLite database.
- **Real-time Price Checking**: Fetches the current market price for all open positions from the public MEXC API.
- **Trader-Specific Stop-Loss**: Set a unique stop-loss percentage for each trader in a central configuration file.
- **Multi-Stage Email Alerts**: Configure a series of reminder intervals to send increasingly urgent follow-up emails if a losing position remains open.
- **Customizable Alert Schedules**: Define an initial monitoring delay and a sequence of reminder delays on a per-trader basis.
- **Manual Management GUI**: A simple Tkinter-based graphical user interface to view all open trades and manually close any that were missed by the automation.

## How It Works

The application is composed of several modular classes:

- **main.py**: The main orchestrator. It runs on a schedule, reads the configuration, and coordinates all components, including the complex alert scheduling logic.
- **GmailChecker**: Handles secure OAuth2 authentication and communication with the Gmail API to fetch new emails.
- **Analyze**: The core parsing engine. It receives an email, attempts to parse it with regex, and if that fails, it calls the LLMDataExtractor. It then instructs the DatabaseManager to update the trade status.
- **LLMDataExtractor**: A fallback class that uses the OpenAI API to extract trade data from email text when regex fails.
- **DatabaseManager**: A centralized class for all SQLite database operations. It now tracks the number of alerts sent for each trade.
- **MexcApiClient**: A client for fetching public market data (like current prices) from the MEXC exchange API.
- **PositionMonitor**: Now stateless, it calculates the P/L for open trades and checks if a given stop-loss has been triggered.
- **EmailNotifier**: Sends email alerts using Gmail's SMTP server, with increasingly urgent subject lines for reminders.
- **TraderConfig**: A powerful configuration manager that loads and interprets per-trader alert schedules and stop-loss thresholds from trader_config.json.
- **gui_manager.py**: A separate, standalone Tkinter application for manually viewing and closing trades in the database.

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

### 4. Set Up Google Cloud Project & Credentials

*(Refer to Google Cloud documentation for setting up OAuth2 credentials)*

### 5. Generate a Google App Password

*(Refer to Google Account settings for generating an App Password)*

## Configuration

Before running the application, you need to configure your settings in two files.

### 1. Environment Variables (.env)

Copy the `.env.example` file to `.env`. This file holds your secret keys and basic settings.

```env
# .env

# Gmail API scope (readonly is safest for monitoring)
SCOPES='https://www.googleapis.com/auth/gmail.readonly'

# Base Gmail search query. It will be appended with a timestamp.
# Use 'label:mexc' for better filtering if you auto-label your MEXC emails.
QUERY='is:unread in:inbox'

# --- Email Alert Configuration ---

# Email address FROM which alerts are sent (your Gmail address).
SENDER_EMAIL='your-email@gmail.com'

# The 16-character App Password you generated in the setup.
SENDER_APP_PASSWORD='abcdefghijklmnop'

# Email address TO which alerts are sent.
RECIPIENT_EMAIL='your-alert-recipient@example.com'

# --- LLM Fallback (Optional) ---
OPENAI_API_KEY='sk-your-openai-api-key'
```

**Note**: The global `STOPLOSS_PERCENTAGE` has been removed from this file and is now managed in `trader_config.json` to allow for per-trader settings.

### 2. Trader Configuration (trader_config.json)

This file is the core of the monitoring logic, allowing you to define a unique behavior for each trader.

```json
[
  {
    "trader": "Limer",
    "stoploss_percentage": -5.0,
    "initial_wait_time": "20m",
    "reminder_intervals": ["30m", "1h", "4h"]
  },
  {
    "trader": "SomeOtherTrader",
    "stoploss_percentage": -8.5,
    "initial_wait_time": "5m",
    "reminder_intervals": ["15m", "15m"]
  },
  {
    "trader": "DefaultStopLossTrader",
    "initial_wait_time": "15m",
    "reminder_intervals": []
  }
]
```

#### Parameter Breakdown

- **trader** (string, required): The exact name of the trader as it appears in the MEXC emails.
- **stoploss_percentage** (float, optional): The trader-specific P/L percentage that triggers an alert. Must be a negative number. If omitted, a default of -10.0 is used.
- **initial_wait_time** (string, required): The time the script should wait after a trade is opened before it performs the first stop-loss check.
- **reminder_intervals** (list of strings, required): A list of additional wait times for sending follow-up reminder emails if the stop-loss is still triggered. An empty list `[]` means no reminders will be sent.
- **Supported duration units**: `m` (minutes), `h` (hours).

#### Example Walkthrough

For the trader "Limer":

1. The first check happens **20 minutes** after the trade opens. If the loss is **-5.0%** or more, the first alert is sent.
2. The script then waits an additional **30 minutes**. If the position is still open and losing, a "Reminder #1" email is sent (at a total of 50 minutes after the open).
3. It then waits an additional **1 hour**. If the situation persists, "Reminder #2" is sent (at 1 hour 50 minutes total).
4. Finally, it waits an additional **4 hours** before sending "Reminder #3" (at 5 hours 50 minutes total). No more alerts will be sent after this.

## Usage

### 1. Running the Automated Monitor

This script is designed to be run on a schedule (e.g., every minute) by a system utility like cron (Linux/macOS) or Task Scheduler (Windows).

To run it manually for testing:

```bash
python main.py
```

**Note**: The first time you run it, a browser window will open asking you to authorize the application to access your Gmail. You only need to do this once.

### 2. Using the Manual Trade Manager GUI

If you miss a "close" email and a trade remains open in the database, you can use the GUI to manually close it. The trade table is sorted by the most recent open date by default.

Run the GUI from your terminal:

```bash
python gui_manager.py
```

A window will appear showing all open trades in a table. Select a trade and click "Close Selected Trade" to close it.

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
│   └── trader_config.py
├── .env
├── credentials.json
├── gui_manager.py
├── main.py
├── trader_config.json
└── README.md
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.