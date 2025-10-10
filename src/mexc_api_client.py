# src/mexc_api_client.py

import requests


class MexcApiClient:
    """
    A client to communicate with the public MEXC API.
    """
    API_BASE_URL = "https://api.mexc.com"

    def get_current_price(self, crypto_pair: str) -> float | None:
        """
        Fetches the current market price for a specific trading pair.

        Args:
            crypto_pair (str): The base currency, e.g., "BERA" or "BTC".

        Returns:
            The current price as a float, or None if an error occurs.
        """
        # Format the symbol as the MEXC API expects it (e.g., "BERAUSDT")
        response = None
        symbol = crypto_pair.upper() + "USDT"
        endpoint = "/api/v3/ticker/price"
        url = f"{self.API_BASE_URL}{endpoint}"
        params = {'symbol': symbol}

        try:
            print(f"   -> Requesting price for {symbol} from MEXC...")
            response = requests.get(url, params=params)

            # Checks for HTTP errors (like 404 Not Found, 400 Bad Request)
            response.raise_for_status()

            data = response.json()

            # Validate and return the price
            if 'price' in data:
                return float(data['price'])
            else:
                print(f"   -> Error: 'price' not found in API response for {symbol}.")
                return None

        except requests.exceptions.HTTPError as http_err:
            # Specific error for when the symbol does not exist (400)
            if response.status_code == 400:
                print(f"   -> Error: Symbol '{symbol}' not found on MEXC Exchange.")
            else:
                print(f"   -> Error: HTTP error occurred for {symbol}: {http_err}")
            return None
        except requests.exceptions.RequestException as req_err:
            # General error for network issues, timeouts, etc.
            print(f"   -> Error: Network error while fetching price for {symbol}: {req_err}")
            return None
        except (ValueError, KeyError) as e:
            # Error for when the price is not a number or the data is unexpected
            print(f"   -> Error: Could not correctly process the API response for {symbol}: {e}")
            return None