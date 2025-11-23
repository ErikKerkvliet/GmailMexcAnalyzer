import requests
import time


class ApiManager:
    def __init__(self):
        self.mexc_url = "https://www.mexc.com/api/platform/futures/copyFutures/api/v1/trader/orders/v2"
        self.kraken_url = "https://api.kraken.com/0/public/Ticker"
        self.kraken_ohlc_url = "https://api.kraken.com/0/public/OHLC"

        # Mapping van MEXC/Standaard namen naar Kraken specifieke namen
        self.ticker_map = {
            "BTC": "XBT",
            "DOGE": "XDG",
        }

    def fetch_mexc_orders(self, uid):
        """Haalt orders op van MEXC voor een specifieke UID."""
        params = {
            "limit": 10,
            "orderListType": "ORDER",
            "page": 1,
            "uid": uid
        }
        try:
            response = requests.get(self.mexc_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                results = data.get("data", {}).get("content", [])
                return results
            else:
                print(f"[API ERROR] MEXC Logic Error: {data.get('message')}")
                return []
        except Exception as e:
            print(f"[API ERROR] Connection error MEXC ({uid}): {e}")
            return []

    def fetch_kraken_price(self, base_coin):
        """Huidige prijs ophalen."""
        kraken_coin = self.ticker_map.get(base_coin, base_coin)
        pairs_to_try = [f"{kraken_coin}USDC", f"{kraken_coin}USD"]

        for pair in pairs_to_try:
            try:
                response = requests.get(self.kraken_url, params={"pair": pair}, timeout=3)
                data = response.json()
                if data.get("error"): continue

                result = data.get("result", {})
                if not result: continue

                first_key = list(result.keys())[0]
                price = result[first_key]['c'][0]
                return float(price)
            except:
                continue
        return "N/A"

    def fetch_kraken_history(self, base_coin, start_ts_ms):
        """
        Haalt historische data op (OHLC) van Kraken vanaf start_ts_ms.
        Geeft terug: (list_of_timestamps, list_of_prices)
        """
        kraken_coin = self.ticker_map.get(base_coin, base_coin)

        # Kraken verwacht 'since' in seconden. MEXC geeft ms.
        start_ts_sec = int(start_ts_ms / 1000)

        # Fallback: Als de order héél oud is, of API faalt, pakken we default pairs
        pairs_to_try = [f"{kraken_coin}USDC", f"{kraken_coin}USD"]

        for pair in pairs_to_try:
            try:
                # Interval 15 of 60 minuten afhankelijk van hoe lang geleden het was?
                # We pakken standaard 5 of 15 minuten candles voor detail.
                # 'since' parameter zorgt dat we alleen data na de starttijd krijgen.
                params = {
                    "pair": pair,
                    "interval": 15,
                    "since": start_ts_sec
                }

                response = requests.get(self.kraken_ohlc_url, params=params, timeout=5)
                data = response.json()

                if data.get("error"): continue

                result = data.get("result", {})
                if not result: continue

                # De key is de pair naam (bijv XXBTZUSD), niet 'last'.
                # We zoeken de key die een lijst is.
                ohlc_data = []
                for key, val in result.items():
                    if key != "last":
                        ohlc_data = val
                        break

                if not ohlc_data: continue

                times = []
                prices = []

                for candle in ohlc_data:
                    # Kraken candle: [time, open, high, low, close, vwap, volume, count]
                    t = float(candle[0])
                    c = float(candle[4])

                    # Filter voor de zekerheid, soms geeft 'since' ook de candle net ervoor terug
                    if t >= start_ts_sec:
                        times.append(datetime.fromtimestamp(t))
                        prices.append(c)

                return times, prices

            except Exception as e:
                print(f"[API HISTORY ERROR] {e}")
                continue

        return [], []


from datetime import datetime