# src/database_manager.py

import sqlite3


class DatabaseManager:
    """
    Beheert alle interacties met de SQLite-database voor de trades.
    """
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row  # Voor dictionary-achtige resultaten
        self.cursor = self.conn.cursor()
        self._setup_database()

    def _setup_database(self):
        """Maakt de tabel aan als deze niet bestaat en voegt de mail_send kolom toe."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT, crypto_pair TEXT NOT NULL,
                trader TEXT NOT NULL, entry_price REAL NOT NULL, open_time TEXT NOT NULL,
                direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT')),
                status TEXT NOT NULL CHECK(status IN ('OPEN', 'CLOSED')),
                timestamp INTEGER NOT NULL,
                mail_send INTEGER NOT NULL DEFAULT 0
            )
        """)
        # Voeg de kolom toe als deze niet bestaat voor achterwaartse compatibiliteit
        try:
            self.cursor.execute("ALTER TABLE trades ADD COLUMN mail_send INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Kolom bestaat al
        self.conn.commit()

    def get_open_trades_details(self) -> list[dict]:
        """
        Haalt een lijst van dictionaries op met alle details van openstaande trades.
        """
        self.cursor.execute("""
            SELECT id, crypto_pair, direction, trader, entry_price, open_time, timestamp, mail_send
            FROM trades WHERE status = 'OPEN' ORDER BY timestamp DESC
        """)
        results = self.cursor.fetchall()
        return [dict(row) for row in results]

    def close_trade_manually(self, trade_id: int) -> bool:
        """Zet de status van een specifieke trade op 'CLOSED' op basis van zijn ID."""
        try:
            self.cursor.execute("UPDATE trades SET status = 'CLOSED' WHERE id = ?", (trade_id,))
            self.conn.commit()
            # rowcount > 0 betekent dat de update succesvol was
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Databasefout bij het sluiten van trade {trade_id}: {e}")
            return False

    def mark_email_as_sent(self, trade_id: int) -> bool:
        """Markeert dat er een e-mail is verzonden voor een specifieke trade."""
        try:
            self.cursor.execute("UPDATE trades SET mail_send = 1 WHERE id = ?", (trade_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Databasefout bij het markeren van e-mail voor trade {trade_id}: {e}")
            return False

    def get_connection(self) -> sqlite3.Connection:
        """Geeft de actieve databaseverbinding terug voor gebruik door andere klassen."""
        return self.conn

    def close_connection(self):
        """Sluit de databaseverbinding."""
        if self.conn:
            self.conn.close()