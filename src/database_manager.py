# src/database_manager.py

import sqlite3


class DatabaseManager:
    """
    Manages all interactions with the SQLite database for trades.
    """

    def __init__(self, db_file: str):
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row  # For dictionary-like results
        self.cursor = self.conn.cursor()
        self._setup_database()

    def _setup_database(self):
        """Creates the table if it doesn't exist and adds the mail_send column."""
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
        # Add the column if it doesn't exist for backward compatibility
        try:
            self.cursor.execute("ALTER TABLE trades ADD COLUMN mail_send INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
        self.conn.commit()

    def get_open_trades_details(self) -> list[dict]:
        """
        Fetches a list of dictionaries with all details of open trades.
        """
        self.cursor.execute("""
            SELECT id, crypto_pair, direction, trader, entry_price, open_time, timestamp, mail_send
            FROM trades WHERE status = 'OPEN' ORDER BY timestamp DESC
        """)
        results = self.cursor.fetchall()
        return [dict(row) for row in results]

    def close_trade_manually(self, trade_id: int) -> bool:
        """Sets the status of a specific trade to 'CLOSED' based on its ID."""
        try:
            self.cursor.execute("UPDATE trades SET status = 'CLOSED' WHERE id = ?", (trade_id,))
            self.conn.commit()
            # rowcount > 0 means the update was successful
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Database error while closing trade {trade_id}: {e}")
            return False

    def mark_email_as_sent(self, trade_id: int) -> bool:
        """Marks that an email has been sent for a specific trade."""
        try:
            self.cursor.execute("UPDATE trades SET mail_send = 1 WHERE id = ?", (trade_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Database error while marking email for trade {trade_id}: {e}")
            return False

    def get_connection(self) -> sqlite3.Connection:
        """Returns the active database connection for use by other classes."""
        return self.conn

    def close_connection(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()