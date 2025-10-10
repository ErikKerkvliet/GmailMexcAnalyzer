# src/analyzer.py

import re
import sqlite3
from .llm_extractor import LLMDataExtractor


class Analyze:
    """
    Analyzes emails about MEXC Copy Trading and updates a database.
    """

    def __init__(self, email_data: dict, db_connection: sqlite3.Connection):
        self.email = email_data
        self.conn = db_connection
        self.cursor = self.conn.cursor()

    def process(self):
        """ Determines the email type and performs the appropriate action. """
        subject = self.email.get('subject', '')

        if "[MEXC][Copy Trade] Position Opened Successfully" in subject:
            self._handle_open_position()
        elif "[MEXC][Copy Trade] Position Closed Successfully" in subject:
            self._handle_close_position()
        else:
            return

    def _handle_open_position(self):
        """
        Now also extracts the entry_price and saves it to the database.
        """
        print("   -> Attempt 1: Extracting data with Regex...")
        # Regex is adjusted to capture the entry price as a separate group (group 3).
        pattern = r"opened a (\w+) (LONG|SHORT) position\. Entry Price: ([0-9.,]+); Trader: (\w+)"
        match = re.search(pattern, self.email['snippet'])

        if match:
            print("   -> Regex Success: Data found.")
            # Convert the price (replace comma with dot) to a float.
            price_str = match.group(3).replace(',', '.')
            trade_data = {
                "crypto_pair": match.group(1),
                "direction": match.group(2),
                "entry_price": float(price_str),
                "trader": match.group(4)  # Trader is now group 4
            }
        else:
            print("   -> Regex Failed. Starting Attempt 2: LLM Fallback...")
            try:
                extractor = LLMDataExtractor()
                trade_data = extractor.extract_trade_data(self.email['body'])
            except ValueError as e:
                print(f"   -> LLM Error: Cannot initialize extractor. {e}")
                return

        # Validate that all necessary data has been extracted
        if trade_data and all(
                trade_data.get(key) is not None for key in ["crypto_pair", "direction", "trader", "entry_price"]):
            crypto_pair = trade_data["crypto_pair"]
            direction = trade_data["direction"]
            trader = trade_data["trader"]
            entry_price = float(trade_data["entry_price"])  # Ensure it is a float
            open_time = self.email['date']
            timestamp = self.email['timestamp']

            self.cursor.execute(
                """SELECT id FROM trades
                   WHERE crypto_pair = ? AND trader = ? AND direction = ? AND status = 'OPEN'""",
                (crypto_pair, trader, direction)
            )
            existing_trade = self.cursor.fetchone()
            if existing_trade:
                # An open trade already exists, update it.
                trade_id = existing_trade[0]
                print(
                    f"🔄 Position UPDATED: Existing 'OPEN' trade (ID: {trade_id}) found for {crypto_pair}/{trader}.")
                self.cursor.execute(
                    """UPDATE trades SET entry_price = ?, open_time = ?, timestamp = ?
                       WHERE id = ?""",
                    (entry_price, open_time, timestamp, trade_id)
                )
                print("   -> Record successfully updated in the database.")
            else:
                print(
                    f"📈 Position OPENED: Pair={crypto_pair}, Direction={direction.upper()}, Price={entry_price}, Trader={trader}")

                # INSERT query is adjusted with the 'entry_price' column
                self.cursor.execute(
                    """INSERT INTO trades 
                       (crypto_pair, trader, entry_price, open_time, direction, status, timestamp) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (crypto_pair, trader, entry_price, open_time, direction.upper(), 'OPEN', timestamp)
                )
                self.conn.commit()
                print("   -> Record successfully added to the database.")
        else:
            print(
                f"   -> CRITICAL ERROR: Could not fully extract trade data from email with subject: '{self.email['subject']}'")

    def _handle_close_position(self):
        """
        Extracts data, finds the corresponding open trade (incl. direction),
        and updates it in the DB.
        """
        pattern = r"Your (\w+) position has been closed successfully\. Trader: (\w+)"
        match = re.search(pattern, self.email['snippet'])

        if not match:
            print(f"Could not extract data from 'close' email: {self.email['subject']}")
            return

        crypto_pair = match.group(1)
        trader = match.group(2)

        # Find the ID and direction of the most recent matching open trade.
        self.cursor.execute(
            """
            SELECT id, direction FROM trades
            WHERE crypto_pair = ? AND trader = ? AND status = 'OPEN'
            ORDER BY open_time DESC
            LIMIT 1
            """,
            (crypto_pair, trader)
        )
        trade_to_close = self.cursor.fetchone()  # Fetch one result

        # If we found a trade, update it.
        if trade_to_close:
            trade_id, trade_direction = trade_to_close

            # Now we use the 'direction' for a clear log message
            print(f"📉 Position CLOSED: Pair={crypto_pair}, Direction={trade_direction}, Trader={trader}")

            # Update the specific trade based on its unique ID.
            self.cursor.execute(
                "UPDATE trades SET status = 'CLOSED' WHERE id = ?",
                (trade_id,)
            )
            self.conn.commit()
            print("   -> Record updated in the database.")
        else:
            # If there is no corresponding open trade, issue a clear warning.
            print(f"   -> WARNING: No corresponding 'OPEN' position found for {crypto_pair}/{trader}.")