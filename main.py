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
from src.trader_cooldown_manager import TraderCooldownManager
from src.email_notifier import EmailNotifier

DB_FILE = "trades.db"
TIMESTAMP_FILE = "last_run_timestamp.txt"
TRADER_CONFIG_FILE = "trader_config.json"


def read_last_run_timestamp() -> int | None:
    """Leest de Unix-timestamp van de laatste uitvoering uit het state-bestand."""
    try:
        with open(TIMESTAMP_FILE, 'r') as f:
            content = f.read().strip()
            return int(content)
    except (FileNotFoundError, ValueError):
        return None

def write_current_timestamp():
    """Schrijft de huidige Unix-timestamp naar het state-bestand."""
    current_timestamp = int(time.time())
    with open(TIMESTAMP_FILE, 'w') as f:
        f.write(str(current_timestamp))
    # Print aan het begin van een nieuwe regel voor duidelijkheid
    print(f"\nTimestamp {current_timestamp} opgeslagen voor de volgende run.")

def main():
    """
    De hoofdfunctie van de applicatie.
    """
    env_path = Path('.') / '.env'
    load_dotenv(dotenv_path=env_path)

    scopes = [os.getenv('SCOPES')]
    base_query = os.getenv('QUERY')

    db_manager = DatabaseManager(DB_FILE)

    # Bouw de zoekopdracht dynamisch op (uw logica is behouden)
    last_timestamp = read_last_run_timestamp()
    full_query = base_query
    if last_timestamp:
        full_query += f" after:{last_timestamp}"
        print(f"Zoeken naar e-mails na timestamp: {last_timestamp}")
    else:
        print("Geen vorige timestamp gevonden. Eerste run of state-bestand is nieuw.")

    print(f"Volledige zoekopdracht: '{full_query}'")

    checker = GmailChecker(scopes=scopes)
    new_emails = checker.get_new_emails(query=full_query)

    if not new_emails:
        print("Geen nieuwe e-mails gevonden die aan de query voldoen.")
    else:
        print(f"\n{len(new_emails)} ongelezen e-mail(s) gevonden. Verwerken van oud naar nieuw...")
        for email in reversed(new_emails):
            # Geef de databaseverbinding door vanuit de manager
            analyzer = Analyze(email_data=email, db_connection=db_manager.get_connection())
            analyzer.process()

    # De timestamp wordt na de verwerking geschreven,
    # zodat gemiste e-mails bij een fout opnieuw worden geprobeerd.
    write_current_timestamp()

    # --- Controle van openstaande posities ---
    print("\n--- Controleren van openstaande posities ---")

    # Lees e-mailinstellingen en maak een notifier object aan
    sender = os.getenv('SENDER_EMAIL')
    password = os.getenv('SENDER_APP_PASSWORD')
    recipient = os.getenv('RECIPIENT_EMAIL')
    notifier = None  # Standaard geen notifier

    if sender and password and recipient:
        notifier = EmailNotifier(sender_email=sender, app_password=password, recipient_email=recipient)
    else:
        print(
            "E-mailinstellingen (SENDER_EMAIL, etc.) niet volledig gevonden in .env. Waarschuwingen worden alleen in de console getoond.")
    try:
        stop_loss = float(os.getenv('STOPLOSS_PERCENTAGE', -100.0))
    except (ValueError, TypeError):
        stop_loss = -100.0
        print("WAARSCHUWING: STOPLOSS_PERCENTAGE in .env is ongeldig.")

    trader_config_manager = TraderCooldownManager(TRADER_CONFIG_FILE)
    open_trades = db_manager.get_open_trades_details()

    if not open_trades:
        print("Geen openstaande posities gevonden in de database.")
    else:
        print(f"{len(open_trades)} openstaande positie(s) gevonden.")
        mexc_client = MexcApiClient()
        monitor = PositionMonitor(stop_loss_percentage=stop_loss, email_notifier=notifier)
        current_time = int(time.time())

        for trade in open_trades:
            trader_name = trade['trader']
            trade_timestamp = trade['timestamp']

            # Haal de monitoring-vertraging op voor deze trader
            monitor_delay_seconds = trader_config_manager.get_monitor_delay_seconds(trader_name)

            elapsed_time = current_time - trade_timestamp

            # Controleer ALLEEN als de trade lang genoeg open staat.
            if elapsed_time >= monitor_delay_seconds:
                # De tijd is verstreken, dus we mogen de stop-loss controleren.
                print(
                    f"   -> Controle voor {trade['crypto_pair']} ({trader_name}) wordt uitgevoerd (open voor {elapsed_time // 60}m).")
                current_price = mexc_client.get_current_price(trade['crypto_pair'])
                if current_price is not None:
                    monitor.check_position(
                        crypto_pair=trade['crypto_pair'], direction=trade['direction'],
                        entry_price=trade['entry_price'], current_price=current_price
                    )
            else:
                # De tijd is nog niet verstreken. Doe niets en log dit.
                remaining_time = monitor_delay_seconds - elapsed_time
                print(
                    f"   -> Monitoring voor {trade['crypto_pair']} ({trader_name}) is uitgesteld. Controle start over: {remaining_time // 60}m {remaining_time % 60}s.")

    db_manager.close_connection()
    print("\nProces voltooid. Databaseverbinding gesloten.")


if __name__ == '__main__':
    main()