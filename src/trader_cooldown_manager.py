# src/trader_cooldown_manager.py

import json
import re


class TraderCooldownManager:
    """
    Leest en beheert de monitoring-vertraging per trader uit een configuratiebestand.
    """
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.default_delay_seconds = 0
        self.trader_delays = self._load_config()

    def _parse_duration(self, duration_str: str) -> int:
        """Converteert een duration string (bv. '20m', '1h') naar seconden."""
        match = re.match(r"(\d+)([mhds])", duration_str.lower())
        if not match:
            return self.default_delay_seconds

        value, unit = int(match.group(1)), match.group(2)

        if unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 3600
        elif unit == 'd':
            return value * 86400
        elif unit == 's':
            return value
        return self.default_delay_seconds

    def _load_config(self) -> dict:
        """Laadt de trader-configuratie uit het JSON-bestand."""
        delays = {}
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                for item in data:
                    trader = item.get('trader')
                    monitor_delay = item.get('monitor_na')
                    if trader and monitor_delay:
                        delays[trader] = self._parse_duration(monitor_delay)
            print("Trader monitoring-vertragingen succesvol geladen.")
        except FileNotFoundError:
            print(
                f"Info: Configuratiebestand '{self.config_file}' niet gevonden. Standaard vertraging (0s) wordt gebruikt.")
        except json.JSONDecodeError:
            print(
                f"Fout: Configuratiebestand '{self.config_file}' bevat ongeldige JSON. Standaard vertraging wordt gebruikt.")
        return delays

    def get_monitor_delay_seconds(self, trader_name: str) -> int:
        """
        Hernoemd voor duidelijkheid. Haalt de vertraging in seconden op
        voordat monitoring voor een trader start.
        """
        return self.trader_delays.get(trader_name, self.default_delay_seconds)