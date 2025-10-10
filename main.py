# main.py

import os
import time
from pathlib import Path
from dotenv import load_dotenv
from src.gmail_checker import GmailChecker
from src.analyzer import Analyze
from src.mexc_api_client import MexcApiClient
from src.position_monitor import PositionMonitor
from src.database_manager import DatabaseManager
from src.trader_config import TraderConfig
from src.email_notifier import EmailNotifier

DB_FILE = "trades.db"
TIMESTAMP_FILE = "last_run_timestamp.txt"
TRADER_CONFIG_FILE = "trader_config.json"


def read_last_run_timestamp() -> int | None:
    """Reads the Unix timestamp of the last execution from the state file."""
    try:
        with open(TIMESTAMP_FILE, 'r') as f:
            content = f.read().strip()
            return int(content)
    except (FileNotFoundError, ValueError):
        return None


def write_current_timestamp():
    """Writes the current Unix timestamp to the state file."""
    current_timestamp = int(time.time())
    with open(TIMESTAMP_FILE, 'w') as f:
        f.write(str(current_timestamp))
    # Print at the beginning of a new line for clarity
    print(f"\nTimestamp {current_timestamp} saved for the next run.")


def main():
    """
    The main function of the application.
    """
    env_path = Path('.') / '.env'
    load_dotenv(dotenv_path=env_path)

    scopes = [os.getenv('SCOPES')]
    base_query = os.getenv('QUERY')

    db_manager = DatabaseManager(DB_FILE)

    # Dynamically build the search query
    last_timestamp = read_last_run_timestamp()
    full_query = base_query
    if last_timestamp:
        full_query += f" after:{last_timestamp}"
        print(f"Searching for emails after timestamp: {last_timestamp}")
    else:
        print("No previous timestamp found. First run or state file is new.")

    print(f"Full search query: '{full_query}'")

    checker = GmailChecker(scopes=scopes)
    new_emails = checker.get_new_emails(query=full_query)

    # The timestamp is written after processing
    write_current_timestamp()

    if not new_emails:
        print("No new emails found matching the query.")
    else:
        print(f"\n{len(new_emails)} unread email(s) found. Processing from old to new...")
        for email in reversed(new_emails):
            # Pass the database connection from the manager
            analyzer = Analyze(email_data=email, db_connection=db_manager.get_connection())
            analyzer.process()

    # --- Checking open positions ---
    print("\n--- Checking open positions ---")

    # Read email settings and create a notifier object
    sender = os.getenv('SENDER_EMAIL')
    password = os.getenv('SENDER_APP_PASSWORD')
    recipient = os.getenv('RECIPIENT_EMAIL')
    notifier = None  # Default no notifier

    if sender and password and recipient:
        notifier = EmailNotifier(sender_email=sender, app_password=password, recipient_email=recipient)
    else:
        print(
            "Email settings (SENDER_EMAIL, etc.) not fully found in .env. Alerts will only be shown in the console.")
    try:
        stop_loss = float(os.getenv('STOPLOSS_PERCENTAGE', -100.0))
    except (ValueError, TypeError):
        stop_loss = -100.0
        print("WARNING: STOPLOSS_PERCENTAGE in .env is invalid.")

    trader_config = TraderConfig(TRADER_CONFIG_FILE)
    open_trades = db_manager.get_open_trades_details()

    if not open_trades:
        print("No open positions found in the database.")
    else:
        print(f"{len(open_trades)} open position(s) found.")
        mexc_client = MexcApiClient()
        monitor = PositionMonitor(stop_loss_percentage=stop_loss, email_notifier=notifier, db_manager=db_manager)
        current_time = int(time.time())

        for trade in open_trades:
            trader_name = trade['trader']
            trade_timestamp = trade['timestamp']

            # Get the monitoring delay for this trader
            monitor_delay_seconds = trader_config.get_config_wait_time(trader_name)

            # ONLY check if the trade has been open long enough.
            if current_time > (trade_timestamp + monitor_delay_seconds):
                # The time has passed, so we can check the stop-loss.
                elapsed_time = current_time - trade_timestamp
                print(
                    f"   -> Check for {trade['crypto_pair']} ({trader_name}) is being performed (open for {elapsed_time // 60}m).")
                current_price = mexc_client.get_current_price(trade['crypto_pair'])
                if current_price is not None:
                    monitor.check_position(
                        trade_id=trade['id'],
                        crypto_pair=trade['crypto_pair'],
                        direction=trade['direction'],
                        entry_price=trade['entry_price'],
                        current_price=current_price,
                        mail_send=trade['mail_send']
                    )

    db_manager.close_connection()
    print("\nProcess completed. Database connection closed.")


if __name__ == '__main__':
    main()