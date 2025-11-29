import time
from PyQt6.QtCore import QThread, pyqtSignal
from api_manager import ApiManager


class WorkerThread(QThread):
    """
    Background thread.
    Updates:
    - Orders (MEXC)
    - Huidige Prijs (Kraken - Live)
    - Open Prijs (Kraken - Historisch, Cached)
    """
    # Signaal update: uid, orders, current_prices_dict, historical_prices_dict
    data_fetched = pyqtSignal(str, list, dict, dict)

    def __init__(self, user_ids):
        super().__init__()
        self.user_ids = user_ids
        self.api = ApiManager()
        self.running = True

        # Cache voor historische prijzen: { "order_id": 123.45 }
        # Omdat de Open Time van een order nooit verandert, hoeven we dit maar 1x te halen.
        self.kraken_open_prices = {}

    def run(self):
        print(f"[Worker] Thread started. Monitoring {len(self.user_ids)} users.")

        while self.running:
            for uid in self.user_ids:
                if not self.running: break

                # 1. Haal orders op
                orders = self.api.fetch_mexc_orders(uid)

                # 2. Verzamel unieke coins
                unique_coins = set()
                for order in orders:
                    coin = order.get('baseCoinName')
                    if coin:
                        unique_coins.add(coin)

                # 3. Haal LIVE prijzen op (Current)
                current_prices = {}
                for coin in unique_coins:
                    price = self.api.fetch_kraken_price(coin)
                    current_prices[coin] = price

                # 4. Haal HISTORISCHE prijzen op (Open Time) - Met Cache Check
                for order in orders:
                    oid = str(order.get('id'))
                    base = order.get('baseCoinName')
                    ts = order.get('openTime')

                    # Als we hem nog niet hebben, haal hem op
                    if oid not in self.kraken_open_prices:
                        # Alleen ophalen als we geldige data hebben
                        if base and ts:
                            print(f"[Worker] Fetching Kraken entry for order {oid} ({base})...")
                            hist_price = self.api.get_price_at_time(base, ts)
                            self.kraken_open_prices[oid] = hist_price
                            # Korte sleep om API rate limits te respecteren bij opstarten
                            time.sleep(0.2)

                            # 5. Stuur alles naar de GUI (inclusief de cache)
                self.data_fetched.emit(uid, orders, current_prices, self.kraken_open_prices)

            # 6. Wacht 10 seconden
            for _ in range(100):
                if not self.running: break
                time.sleep(0.1)

        print("[Worker] Thread stopped.")

    def stop(self):
        self.running = False
        self.wait()