# src/position_monitor.py

from .email_notifier import EmailNotifier
from .database_manager import DatabaseManager


class PositionMonitor:
    """
    Monitors open positions and alerts if a stop-loss threshold is reached.
    """

    def __init__(self, stop_loss_percentage: float, email_notifier: EmailNotifier | None = None,
                 db_manager: DatabaseManager | None = None):
        if stop_loss_percentage > 0:
            stop_loss_percentage = -stop_loss_percentage
        self.stop_loss_percentage = stop_loss_percentage
        self.notifier = email_notifier
        self.db_manager = db_manager
        print(f"Position Monitor initialized with stop-loss threshold {self.stop_loss_percentage}%.")
        if self.notifier:
            print("Email alerts are activated.")

    def check_position(self, trade_id: int, crypto_pair: str, direction: str, entry_price: float, current_price: float,
                       mail_send: int):
        if entry_price == 0: return

        percentage_change = 0.0
        if direction.upper() == 'LONG':
            percentage_change = ((current_price - entry_price) / entry_price) * 100
        elif direction.upper() == 'SHORT':
            percentage_change = ((entry_price - current_price) / entry_price) * 100

        pnl_status = f"Profit: {percentage_change:+.2f}%" if percentage_change >= 0 else f"Loss: {percentage_change:.2f}%"
        print(f"   -> Status {crypto_pair}: Entry=${entry_price:.4f}, Current=${current_price:.4f} | {pnl_status}")

        # Check if the stop-loss has been reached AND if no email has been sent yet.
        if percentage_change <= self.stop_loss_percentage and mail_send == 0:
            print("🚨" * 20)
            print(f"🚨 STOP-LOSS ALERT for {crypto_pair} ({direction})!")
            print(
                f"🚨 Loss of {percentage_change:.2f}% has reached the threshold of {self.stop_loss_percentage:.2f}%.")
            print("🚨" * 20)

            # Call the notifier if it exists
            if self.notifier:
                self.notifier.send_stop_loss_alert(
                    crypto_pair=crypto_pair, direction=direction, entry_price=entry_price,
                    current_price=current_price, pnl_percentage=percentage_change
                )
                # Mark the email as sent in the database
                if self.db_manager:
                    self.db_manager.mark_email_as_sent(trade_id)
        elif mail_send == 1:
            print(f"   -> Info: Stop-loss for {crypto_pair} has already been reached, email has already been sent.")