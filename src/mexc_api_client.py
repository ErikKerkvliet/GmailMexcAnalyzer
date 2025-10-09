# src/mexc_api_client.py

import requests


class MexcApiClient:
    """
    Een client om te communiceren met de openbare MEXC API.
    """
    API_BASE_URL = "https://api.mexc.com"

    def get_current_price(self, crypto_pair: str) -> float | None:
        """
        Haalt de huidige marktprijs op voor een specifiek handelspaar.

        Args:
            crypto_pair (str): De base currency, bijv. "BERA" of "BTC".

        Returns:
            De huidige prijs als een float, of None als er een fout optreedt.
        """
        # Formatteer het symbool zoals de MEXC API het verwacht (bv. "BERAUSDT")
        symbol = crypto_pair.upper()
        endpoint = "/api/v3/ticker/price"
        url = f"{self.API_BASE_URL}{endpoint}"
        params = {'symbol': symbol}

        try:
            print(f"   -> Opvragen van prijs voor {symbol} bij MEXC...")
            response = requests.get(url, params=params)

            # Controleert op HTTP-fouten (zoals 404 Not Found, 400 Bad Request)
            response.raise_for_status()

            data = response.json()

            # Valideer en retourneer de prijs
            if 'price' in data:
                return float(data['price'])
            else:
                print(f"   -> Fout: 'price' niet gevonden in API-antwoord voor {symbol}.")
                return None

        except requests.exceptions.HTTPError as http_err:
            # Specifieke fout voor als het symbool niet bestaat (400)
            if response.status_code == 400:
                print(f"   -> Fout: Symbool '{symbol}' niet gevonden op MEXC Exchange.")
            else:
                print(f"   -> Fout: HTTP-fout opgetreden voor {symbol}: {http_err}")
            return None
        except requests.exceptions.RequestException as req_err:
            # Algemene fout voor netwerkproblemen, timeouts, etc.
            print(f"   -> Fout: Netwerkfout bij het opvragen van prijs voor {symbol}: {req_err}")
            return None
        except (ValueError, KeyError) as e:
            # Fout voor als de prijs geen getal is of de data onverwacht is
            print(f"   -> Fout: Kon het antwoord van de API niet correct verwerken voor {symbol}: {e}")
            return None