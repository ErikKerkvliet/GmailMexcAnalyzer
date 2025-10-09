# src/email_notifier.py

import smtplib
from email.message import EmailMessage


class EmailNotifier:
    """
    Verstuurt e-mailwaarschuwingen via de SMTP-server van Gmail.
    """
    def __init__(self, sender_email: str, app_password: str, recipient_email: str):
        self.sender_email = sender_email
        self.app_password = app_password
        self.recipient_email = recipient_email

    def send_stop_loss_alert(self, crypto_pair: str, direction: str, entry_price: float, current_price: float,
                             pnl_percentage: float):
        """
        Stelt een e-mail op en verstuurt deze met de details van de stop-loss waarschuwing.
        """
        subject = f"🚨 Stop-Loss Waarschuwing: {crypto_pair} ({direction})"

        body = f"""
        Hallo,

        Dit is een automatische waarschuwing van je MEXC Trade Monitor.
        Een van je openstaande posities heeft de ingestelde stop-loss drempel bereikt.

        Details van de positie:
        ---------------------------------
        - Handelspaar: {crypto_pair}
        - Richting:    {direction}
        - Entry Prijs: ${entry_price:.4f}
        - Huidige Prijs: ${current_price:.4f}
        - Verlies:     {pnl_percentage:.2f}%
        ---------------------------------

        Het is aanbevolen om deze positie te controleren op de MEXC exchange.

        Met vriendelijke groet,
        Je Python Trade Monitor
        """

        # Maak het e-mailbericht object
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = self.sender_email
        msg['To'] = self.recipient_email
        msg.set_content(body)

        print(f"   -> Poging om stop-loss e-mail te versturen naar {self.recipient_email}...")

        try:
            # Maak verbinding met de Gmail SMTP server
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.sender_email, self.app_password)
                server.send_message(msg)
            print("   -> E-mailwaarschuwing succesvol verzonden!")
        except smtplib.SMTPAuthenticationError:
            print(
                "   -> FOUT BIJ VERSTUREN: Authenticatie mislukt. Controleer SENDER_EMAIL en SENDER_APP_PASSWORD in je .env-bestand.")
        except Exception as e:
            print(f"   -> FOUT BIJ VERSTUREN: Er is een onverwachte fout opgetreden: {e}")