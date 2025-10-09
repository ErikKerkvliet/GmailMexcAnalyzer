# src/position_monitor.py

from .email_notifier import EmailNotifier


class PositionMonitor:
    """
    Controleert openstaande posities en waarschuwt als een stop-loss drempel is bereikt.
    """
    def __init__(self, stop_loss_percentage: float, email_notifier: EmailNotifier | None = None):
        if stop_loss_percentage > 0:
            stop_loss_percentage = -stop_loss_percentage
        self.stop_loss_percentage = stop_loss_percentage
        self.notifier = email_notifier  # Sla de notifier op
        print(f"Position Monitor geïnitialiseerd met stop-loss drempel {self.stop_loss_percentage}%.")
        if self.notifier:
            print("E-mailwaarschuwingen zijn geactiveerd.")

    def check_position(self, crypto_pair: str, direction: str, entry_price: float, current_price: float):
        if entry_price == 0: return

        percentage_change = 0.0
        if direction.upper() == 'LONG':
            percentage_change = ((current_price - entry_price) / entry_price) * 100
        elif direction.upper() == 'SHORT':
            percentage_change = ((entry_price - current_price) / entry_price) * 100

        pnl_status = f"Winst: {percentage_change:+.2f}%" if percentage_change >= 0 else f"Verlies: {percentage_change:.2f}%"
        print(f"   -> Status {crypto_pair}: Entry=${entry_price:.4f}, Huidig=${current_price:.4f} | {pnl_status}")

        if percentage_change <= self.stop_loss_percentage:
            print("🚨" * 20)
            print(f"🚨 STOP-LOSS WAARSCHUWING voor {crypto_pair} ({direction})!")
            print(
                f"🚨 Verlies van {percentage_change:.2f}% heeft de drempel van {self.stop_loss_percentage:.2f}% bereikt.")
            print("🚨" * 20)

            # Roep de notifier aan als deze bestaat
            if self.notifier:
                self.notifier.send_stop_loss_alert(
                    crypto_pair=crypto_pair, direction=direction, entry_price=entry_price,
                    current_price=current_price, pnl_percentage=percentage_change
                )