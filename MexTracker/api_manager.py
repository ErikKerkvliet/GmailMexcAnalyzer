import os
import requests
import time
from datetime import datetime


class ApiManager:
    def __init__(self):
        self.mexc_url = "https://www.mexc.com/api/platform/futures/copyFutures/api/v1/trader/orders/v2"
        self.kraken_url = "https://api.kraken.com/0/public/Ticker"
        self.kraken_ohlc_url = "https://api.kraken.com/0/public/OHLC"

        # Keys laden uit .env (optioneel voor publieke data, maar nuttig voor limieten)
        self.api_key = os.getenv("KRAKEN_API_KEY")
        self.api_secret = os.getenv("KRAKEN_PRIVATE_KEY")

        # Mapping voor Kraken symbolen
        # Kraken gebruikt soms 'X' of 'Z' prefixes voor crypto (Legacy), maar modernere pairs zijn directer.
        self.ticker_map = {
            "BTC": "XBT",
            "DOGE": "XDG",
            # ETH niet naar XETH mappen, dat geeft vaak problemen met XETHUSD.
            # ETHUSD of ETHUSDC werkt meestal standaard.
        }

    def _get_headers(self):
        """Voegt API key toe indien aanwezig."""
        if self.api_key:
            return {"API-Key": self.api_key}
        return {}

    def fetch_mexc_orders(self, uid):
        """Haalt orders op van MEXC voor een specifieke UID."""
        params = {
            "limit": 20,
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
        """Huidige prijs ophalen (Live)."""
        kraken_coin = self.ticker_map.get(base_coin, base_coin)
        pairs_to_try = [f"{kraken_coin}USD", f"{kraken_coin}USDC", f"{kraken_coin}USDT"]

        for pair in pairs_to_try:
            try:
                response = requests.get(self.kraken_url, params={"pair": pair}, headers=self._get_headers(), timeout=3)
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
        """Haalt chart data op (voor de grafiek in popup)."""
        kraken_coin = self.ticker_map.get(base_coin, base_coin)
        start_ts_sec = int(start_ts_ms / 1000)

        # Voor de grafiek pakken we standaard 15 of 60 min data om verder terug te kunnen kijken
        # Interval 60 = 30 dagen historie (720 candles * 1 uur)
        interval = 60

        pairs_to_try = [f"{kraken_coin}USD", f"{kraken_coin}USDC", f"{kraken_coin}USDT"]

        for pair in pairs_to_try:
            try:
                params = {"pair": pair, "interval": interval, "since": start_ts_sec}
                response = requests.get(self.kraken_ohlc_url, params=params, headers=self._get_headers(), timeout=5)
                data = response.json()
                if data.get("error"): continue

                result = data.get("result", {})
                ohlc_data = []
                for key, val in result.items():
                    if key != "last":
                        ohlc_data = val
                        break

                if not ohlc_data: continue

                times, prices = [], []
                for candle in ohlc_data:
                    t, c = float(candle[0]), float(candle[4])
                    if t >= start_ts_sec:
                        times.append(datetime.fromtimestamp(t))
                        prices.append(c)

                if times: return times, prices
            except Exception as e:
                print(f"[API HISTORY ERROR] {e}")
                continue
        return [], []

    def get_price_at_time(self, base_coin, timestamp_ms):
        """
        Haalt de historische prijs op.
        Oplossing voor 'Time Mismatch': Probeert verschillende intervallen.
        Kraken geeft max 720 candles.
        - Interval 1 (min) = max 12 uur terug
        - Interval 5 (min) = max 2.5 dag terug
        - Interval 15 (min) = max 7.5 dag terug
        - Interval 60 (uur) = max 30 dagen terug
        - Interval 240 (4 uur) = max 120 dagen terug
        """
        kraken_coin = self.ticker_map.get(base_coin, base_coin)
        target_sec = int(timestamp_ms / 1000)

        readable_target = datetime.fromtimestamp(target_sec).strftime('%Y-%m-%d %H:%M')

        pairs_to_try = [f"{kraken_coin}USD", f"{kraken_coin}USDC", f"{kraken_coin}USDT"]

        # We proberen steeds grovere intervallen tot we de datum vinden
        intervals = [1, 5, 15, 60, 240]

        for pair in pairs_to_try:
            for interval in intervals:
                # Bereken starttijd iets voor de target, afhankelijk van interval
                # We pakken een ruime marge om zeker te zijn dat Kraken de candle geeft
                lookback_sec = interval * 60 * 10
                start_sec = target_sec - lookback_sec

                try:
                    params = {
                        "pair": pair,
                        "interval": interval,
                        "since": start_sec
                    }
                    response = requests.get(self.kraken_ohlc_url, params=params, headers=self._get_headers(), timeout=4)
                    data = response.json()

                    if data.get("error"):
                        # Als de pair niet bestaat, break de inner loop (intervals) en ga naar volgende pair
                        break

                    result = data.get("result", {})
                    ohlc_data = None
                    for key, val in result.items():
                        if key != "last":
                            ohlc_data = val
                            break

                    if not ohlc_data:
                        continue

                    # Zoek dichtstbijzijnde candle
                    closest_candle = min(
                        ohlc_data,
                        key=lambda c: abs(float(c[0]) - target_sec)
                    )

                    candle_time = float(closest_candle[0])
                    candle_open = float(closest_candle[1])

                    # Controleer of de datum klopt
                    time_diff = abs(candle_time - target_sec)

                    # Toegestane afwijking: 1 interval + beetje marge
                    max_diff = (interval * 60) * 1.5

                    if time_diff > max_diff:
                        # Als de tijd te veel afwijkt, betekent het dat Kraken 'recente' data stuurde
                        # in plaats van historie. Probeer dan een groter interval.
                        # print(f"[RETRY] {pair} int={interval}: Diff {time_diff:.0f}s too large for target {readable_target}")
                        continue

                    # Als we hier zijn, hebben we een match!
                    return candle_open

                except Exception as e:
                    print(f"[ERROR] {pair} int={interval}: {e}")
                    continue

        print(f"[NO HISTORY] Kon geen prijs vinden voor {base_coin} rond {readable_target}")
        return "N/A"