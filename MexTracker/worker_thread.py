import time
from PyQt6.QtCore import QThread, pyqtSignal
from api_manager import ApiManager


class WorkerThread(QThread):
    """
    Background thread die:
    1. MEXC Orders ophaalt
    2. Kraken Prijzen ophaalt
    3. Dit elke 10 seconden update
    """
    data_fetched = pyqtSignal(str, list, dict)

    def __init__(self, user_ids):
        super().__init__()
        self.user_ids = user_ids
        self.api = ApiManager()
        self.running = True

    def run(self):
        print(f"[Worker] Thread started. Monitoring {len(self.user_ids)} users.")

        while self.running:
            print(f"[Worker] --- Start Update Cycle ---")

            for uid in self.user_ids:
                if not self.running: break

                print(f"[Worker] Fetching data for UID {uid}...")

                # 1. Haal orders op
                orders = self.api.fetch_mexc_orders(uid)

                # 2. Verzamel unieke coins
                unique_coins = set()
                for order in orders:
                    coin = order.get('baseCoinName')
                    if coin:
                        unique_coins.add(coin)

                if unique_coins:
                    print(f"[Worker] Fetching prices for: {', '.join(unique_coins)}")

                # 3. Haal prijzen op
                prices = {}
                for coin in unique_coins:
                    price = self.api.fetch_kraken_price(coin)
                    prices[coin] = price

                # 4. Stuur naar GUI
                self.data_fetched.emit(uid, orders, prices)

            if self.running:
                print(f"[Worker] Cycle done. Sleeping 10 seconds...")

            # 5. Wacht 10 seconden
            for _ in range(100):
                if not self.running: break
                time.sleep(0.1)

        print("[Worker] Thread stopped.")

    def stop(self):
        print("[Worker] Stopping requested...")
        self.running = False
        self.wait()