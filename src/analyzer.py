# src/analyzer.py

import re
import sqlite3
from .llm_extractor import LLMDataExtractor


class Analyze:
    """
    Analyseert e-mails over MEXC Copy Trading en werkt een database bij.
    """

    def __init__(self, email_data: dict, db_connection: sqlite3.Connection):
        self.email = email_data
        self.conn = db_connection
        self.cursor = self.conn.cursor()

    def process(self):
        """ Bepaalt het type e-mail en voert de juiste actie uit. """
        subject = self.email.get('subject', '')

        if "[MEXC][Copy Trade] Position Opened Successfully" in subject:
            self._handle_open_position()
        elif "[MEXC][Copy Trade] Position Closed Successfully" in subject:
            self._handle_close_position()
        else:
            return

    def _handle_open_position(self):
        """
        Extraheert nu ook de entry_price en slaat deze op in de database.
        """
        print("   -> Poging 1: Data extraheren met Regex...")
        # Regex is aangepast om de entry price als een aparte groep te vangen (groep 3).
        pattern = r"opened a (\w+) (LONG|SHORT) position\. Entry Price: ([0-9.,]+); Trader: (\w+)"
        match = re.search(pattern, self.email['snippet'])

        if match:
            print("   -> Regex Succes: Data gevonden.")
            # Converteer de prijs (vervang komma door punt) naar een float.
            price_str = match.group(3).replace(',', '.')
            trade_data = {
                "crypto_pair": match.group(1),
                "direction": match.group(2),
                "entry_price": float(price_str),
                "trader": match.group(4)  # Trader is nu groep 4
            }
        else:
            print("   -> Regex Mislukt. Starten van Poging 2: LLM Fallback...")
            try:
                extractor = LLMDataExtractor()
                trade_data = extractor.extract_trade_data(self.email['body'])
            except ValueError as e:
                print(f"   -> LLM Fout: Kan extractor niet initialiseren. {e}")
                return

        # Valideer dat alle benodigde data is geëxtraheerd
        if trade_data and all(
                trade_data.get(key) is not None for key in ["crypto_pair", "direction", "trader", "entry_price"]):
            crypto_pair = trade_data["crypto_pair"]
            direction = trade_data["direction"]
            trader = trade_data["trader"]
            entry_price = float(trade_data["entry_price"])  # Zorg ervoor dat het een float is
            open_time = self.email['date']
            timestamp = self.email['timestamp']

            self.cursor.execute(
                """SELECT id FROM trades
                   WHERE crypto_pair = ? AND trader = ? AND direction = ? AND status = 'OPEN'""",
                (crypto_pair, trader, direction)
            )
            existing_trade = self.cursor.fetchone()
            if existing_trade:
                # UPDATE PAD: Er is al een open trade, werk deze bij.
                trade_id = existing_trade[0]
                print(
                    f"🔄 Positie BIJGEWERKT: Bestaande 'OPEN' trade (ID: {trade_id}) gevonden voor {crypto_pair}/{trader}.")
                self.cursor.execute(
                    """UPDATE trades SET entry_price = ?, open_time = ?, timestamp = ?
                       WHERE id = ?""",
                    (entry_price, open_time, timestamp, trade_id)
                )
                print("   -> Record succesvol bijgewerkt in de database.")
            else:
                print(
                f"📈 Positie GEOPEND: Pair={crypto_pair}, Direction={direction.upper()}, Price={entry_price}, Trader={trader}")

                # INSERT query is aangepast met de 'entry_price' kolom
                self.cursor.execute(
                    """INSERT INTO trades 
                       (crypto_pair, trader, entry_price, open_time, direction, status, timestamp) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (crypto_pair, trader, entry_price, open_time, direction.upper(), 'OPEN', timestamp)
                )
                self.conn.commit()
                print("   -> Record succesvol toegevoegd aan de database.")
        else:
            print(
                f"   -> KRITISCHE FOUT: Kon trade-data niet volledig extraheren uit e-mail met onderwerp: '{self.email['subject']}'")

    def _handle_close_position(self):
        """
        Extraheert data, zoekt de corresponderende open trade (incl. richting),
        en werkt deze bij in de DB.
        """
        pattern = r"Your (\w+) position has been closed successfully\. Trader: (\w+)"
        match = re.search(pattern, self.email['snippet'])

        if not match:
            print(f"Kon de data niet extraheren uit 'close' e-mail: {self.email['subject']}")
            return

        crypto_pair = match.group(1)
        trader = match.group(2)

        # Zoek de ID en de richting van de meest recente openstaande trade die overeenkomt.
        self.cursor.execute(
            """
            SELECT id, direction FROM trades
            WHERE crypto_pair = ? AND trader = ? AND status = 'OPEN'
            ORDER BY open_time DESC
            LIMIT 1
            """,
            (crypto_pair, trader)
        )
        trade_to_close = self.cursor.fetchone()  # Haal één resultaat op

        # Als we een trade hebben gevonden, werk deze dan bij.
        if trade_to_close:
            trade_id, trade_direction = trade_to_close

            # Nu gebruiken we de 'direction' voor een duidelijke log-boodschap
            print(f"📉 Positie GESLOTEN: Pair={crypto_pair}, Direction={trade_direction}, Trader={trader}")

            # Werk de specifieke trade bij op basis van zijn unieke ID.
            self.cursor.execute(
                "UPDATE trades SET status = 'CLOSED' WHERE id = ?",
                (trade_id,)
            )
            self.conn.commit()
            print("   -> Record bijgewerkt in de database.")
        else:
            # Stap 4: Als er geen overeenkomstige open trade is, geef een duidelijke waarschuwing.
            print(f"   -> WAARSCHUWING: Geen overeenkomstige 'OPEN' positie gevonden voor {crypto_pair}/{trader}.")