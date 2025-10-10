# src/email_notifier.py

import smtplib
from email.message import EmailMessage


class EmailNotifier:
    """
    Sends email alerts via Gmail's SMTP server.
    """

    def __init__(self, sender_email: str, app_password: str, recipient_email: str):
        self.sender_email = sender_email
        self.app_password = app_password
        self.recipient_email = recipient_email

    def send_stop_loss_alert(self, crypto_pair: str, direction: str, entry_price: float, current_price: float,
                             pnl_percentage: float):
        """
        Composes and sends an email with the details of the stop-loss alert.
        """
        subject = f"🚨 Stop-Loss Alert: {crypto_pair} ({direction})"

        body = f"""
        Hello,

        This is an automatic alert from your Trade Monitor.
        One of your open positions has reached the configured stop-loss threshold.

        Position Details:
        ---------------------------------
        - Trading Pair:  {crypto_pair}
        - Direction:     {direction}
        - Entry Price:   ${entry_price:.4f}
        - Current Price: ${current_price:.4f}
        - Loss:          {pnl_percentage:.2f}%
        ---------------------------------

        It is recommended to check this position on the exchange.

        Best regards,
        Your Python Trade Monitor
        """

        # Create the email message object
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = self.sender_email
        msg['To'] = self.recipient_email
        msg.set_content(body)

        print(f"   -> Attempting to send stop-loss email to {self.recipient_email}...")

        try:
            # Connect to the Gmail SMTP server
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.sender_email, self.app_password)
                server.send_message(msg)
            print("   -> Email alert sent successfully!")
        except smtplib.SMTPAuthenticationError:
            print(
                "   -> SENDING ERROR: Authentication failed. Check SENDER_EMAIL and SENDER_APP_PASSWORD in your .env file.")
        except Exception as e:
            print(f"   -> SENDING ERROR: An unexpected error occurred: {e}")