# src/position_monitor.py

from .email_notifier import EmailNotifier
from .database_manager import DatabaseManager


class PositionMonitor:
    """
    Monitors open positions and alerts if a stop-loss threshold is reached.
    """
    def __init__(self, email_notifier: EmailNotifier | None = None,
                 db_manager: DatabaseManager | None = None):
        # self.stop_loss_percentage is removed from here
        self.notifier = email_notifier
        self.db_manager = db_manager
        print("Position Monitor initialized.") # Updated print statement
        if self.notifier:
            print("Email alerts are activated.")

    def check_position(self, trade_id: int, crypto_pair: str, direction: str, entry_price: float, current_price: float,
                       alerts_sent: int, stop_loss_percentage: float):  # New parameter added
        if entry_price == 0: return

        percentage_change = 0.0
        if direction.upper() == 'LONG':
            percentage_change = ((current_price - entry_price) / entry_price) * 100
        elif direction.upper() == 'SHORT':
            percentage_change = ((entry_price - current_price) / entry_price) * 100

        pnl_status = f"Profit: {percentage_change:+.2f}%" if percentage_change >= 0 else f"Loss: {percentage_change:.2f}%"
        print(f"   -> Status {crypto_pair}: Entry=${entry_price:.4f}, Current=${current_price:.4f} | {pnl_status}")

        # Use the passed-in stop_loss_percentage instead of self.stop_loss_percentage
        if percentage_change <= stop_loss_percentage:
            print("🚨" * 20)
            print(f"🚨 STOP-LOSS TRIGGERED for {crypto_pair} ({direction})! Alert level: {alerts_sent}")
            print(
                f"🚨 Loss of {percentage_change:.2f}% has reached the threshold of {stop_loss_percentage:.2f}%.")  # Use the new variable here
            print("🚨" * 20)

            # Call the notifier if it exists
            if self.notifier:
                self.notifier.send_stop_loss_alert(
                    crypto_pair=crypto_pair, direction=direction, entry_price=entry_price,
                    current_price=current_price, pnl_percentage=percentage_change,
                    alert_level=alerts_sent
                )
                # Increment the alert count in the database
                if self.db_manager:
                    self.db_manager.increment_alert_count(trade_id)