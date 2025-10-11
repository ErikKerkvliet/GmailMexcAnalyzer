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
    trader_config = TraderConfig(TRADER_CONFIG_FILE)
    open_trades = db_manager.get_open_trades_details()

    if not open_trades:
        print("No open positions found in the database.")
    else:
        print(f"{len(open_trades)} open position(s) found. Checking against schedules...")
        mexc_client = MexcApiClient()
        # Initialize the monitor WITHOUT the global stop_loss
        monitor = PositionMonitor(email_notifier=notifier, db_manager=db_manager)
        current_time = int(time.time())

        for trade in open_trades:
            trader_name = trade['trader']
            trade_timestamp = trade['timestamp']
            alerts_sent = trade['alerts_sent']

            # Get the full configuration for this specific trader
            config = trader_config.get_trader_config(trader_name)
            schedule = config['schedule']
            trader_stop_loss = config['stoploss']

            initial_wait = schedule['initial']
            reminder_intervals = schedule['reminders']

            # ... (logic for max_alerts and total_wait_seconds remains the same)

            max_alerts = 1 + len(reminder_intervals)
            if alerts_sent >= max_alerts:
                print(
                    f"   -> Skipping {trade['crypto_pair']} ({trader_name}): All {max_alerts} scheduled alerts have been sent.")
                continue

            # Calculate the total time that must pass before the *next* alert
            if alerts_sent == 0:
                # This is the first check
                total_wait_seconds = initial_wait
            else:
                # This is a reminder check
                # We sum the initial wait + all reminder intervals up to the previous alert
                reminders_to_sum = reminder_intervals[:alerts_sent]
                total_wait_seconds = initial_wait + sum(reminders_to_sum)

            next_alert_time = trade_timestamp + total_wait_seconds

            # Check if it's time to perform the check
            if current_time >= next_alert_time:
                elapsed_time = current_time - trade_timestamp
                print(
                    f"   -> Checking {trade['crypto_pair']} ({trader_name}), open for {elapsed_time // 60}m. (Alert level: {alerts_sent}, SL: {trader_stop_loss}%)")
                current_price = mexc_client.get_current_price(trade['crypto_pair'])

                if current_price is not None:
                    # The monitor will now check the P/L and send an email if the SL is hit
                    monitor.check_position(
                        trade_id=trade['id'],
                        crypto_pair=trade['crypto_pair'],
                        direction=trade['direction'],
                        entry_price=trade['entry_price'],
                        current_price=current_price,
                        alerts_sent=alerts_sent,
                        stop_loss_percentage=trader_stop_loss  # Pass the specific stop-loss here
                    )
            else:
                # It's not yet time to check this trade for its next alert
                wait_remaining = next_alert_time - current_time
                print(f"   -> Skipping {trade['crypto_pair']} ({trader_name}): Next check in {wait_remaining // 60}m.")

    db_manager.close_connection()
    print("\nProcess completed. Database connection closed.")


if __name__ == '__main__':
    main()