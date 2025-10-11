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
        """Creates the table and adds columns for alerts if they don't exist."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT, crypto_pair TEXT NOT NULL,
                trader TEXT NOT NULL, entry_price REAL NOT NULL, open_time TEXT NOT NULL,
                direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT')),
                status TEXT NOT NULL CHECK(status IN ('OPEN', 'CLOSED')),
                timestamp INTEGER NOT NULL,
                mail_send INTEGER NOT NULL DEFAULT 0,
                alerts_sent INTEGER NOT NULL DEFAULT 0
            )
        """)
        # Add columns if they don't exist for backward compatibility
        try:
            self.cursor.execute("ALTER TABLE trades ADD COLUMN alerts_sent INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            # Check if 'mail_send' exists before trying to rename.
            self.cursor.execute("PRAGMA table_info(trades)")
            columns = [info[1] for info in self.cursor.fetchall()]
            if 'mail_send' in columns and 'alerts_sent' not in columns:
                # This part is for migration, but safer just to add and use the new one.
                pass
        except sqlite3.OperationalError:
            pass
        self.conn.commit()

    def get_open_trades_details(self) -> list[dict]:
        """
        Fetches a list of dictionaries with all details of open trades.
        """
        self.cursor.execute("""
            SELECT id, crypto_pair, direction, trader, entry_price, open_time, timestamp, alerts_sent
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

    def increment_alert_count(self, trade_id: int) -> bool:
        """Increments the alert counter for a specific trade."""
        try:
            self.cursor.execute("UPDATE trades SET alerts_sent = alerts_sent + 1 WHERE id = ?", (trade_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Database error while incrementing alert count for trade {trade_id}: {e}")
            return False

    # Add this method to your DatabaseManager class in src/database_manager.py
    def get_all_trades_details(self) -> list[dict]:
        """
        Fetches a list of dictionaries with all details of ALL trades (open and closed).
        """
        self.cursor.execute("""
            SELECT id, crypto_pair, direction, trader, entry_price, open_time, timestamp, mail_send, status
            FROM trades ORDER BY timestamp DESC
        """)
        results = self.cursor.fetchall()
        return [dict(row) for row in results]

    # Add this method too
    def get_unique_traders(self) -> list[str]:
        """Fetches a list of unique trader names from the database."""
        self.cursor.execute("SELECT DISTINCT trader FROM trades ORDER BY trader")
        # fetchall() returns a list of tuples, e.g., [('TraderA',), ('TraderB',)]
        results = self.cursor.fetchall()
        return [row['trader'] for row in results]

    def get_connection(self) -> sqlite3.Connection:
        """Returns the active database connection for use by other classes."""
        return self.conn

    def close_connection(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()