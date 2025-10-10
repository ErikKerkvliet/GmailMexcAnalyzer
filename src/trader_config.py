# src/trader_config.py

import json
import re


class TraderConfig:
    """
    Reads and manages the configuration per trader from a configuration file.
    """

    def __init__(self, config_file: str):
        self.config_file = config_file
        self.default_delay_seconds = 0
        self.trader_delays = self._load_config()

    def _parse_duration(self, duration_str: str) -> int:
        """Converts a duration string (e.g., '20m', '1h') to seconds."""
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
        """Loads the trader configuration from the JSON file."""
        delays = {}
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                for item in data:
                    trader = item.get('trader')
                    monitor_delay = item.get('wait_for_monitoring')
                    if trader and monitor_delay:
                        delays[trader] = self._parse_duration(monitor_delay)
            print("Trader wait times loaded successfully.")
        except FileNotFoundError:
            print(
                f"Info: Configuration file '{self.config_file}' not found. Default delay (0s) will be used.")
        except json.JSONDecodeError:
            print(
                f"Error: Configuration file '{self.config_file}' contains invalid JSON. Default delay will be used.")
        return delays

    def get_config_wait_time(self, trader_name: str) -> int:
        """
        Gets the wait time in seconds before monitoring starts for a trader.
        """
        return self.trader_delays.get(trader_name, self.default_delay_seconds)