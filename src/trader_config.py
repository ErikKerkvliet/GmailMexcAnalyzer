# src/trader_config.py

import json
import re


class TraderConfig:
    """
    Reads and manages the alert schedule configuration for each trader.
    """

    def __init__(self, config_file: str):
        self.config_file = config_file
        self.default_schedule = {'initial': 0, 'reminders': []}
        self.trader_schedules = self._load_config()

    def _parse_duration(self, duration_str: str) -> int:
        """Converts a duration string (e.g., '20m', '1h') to seconds."""
        if not isinstance(duration_str, str): return 0
        match = re.match(r"(\d+)([mhds])", duration_str.lower())
        if not match: return 0

        value, unit = int(match.group(1)), match.group(2)
        if unit == 'm': return value * 60
        if unit == 'h': return value * 3600
        if unit == 'd': return value * 86400
        return value

    def _load_config(self) -> dict:
        """Loads the trader alert schedules from the JSON file."""
        schedules = {}
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                for item in data:
                    trader = item.get('trader')
                    if not trader: continue

                    # For backward compatibility with `monitor_na`
                    initial_wait_str = item.get('initial_wait_time') or item.get('monitor_na')
                    initial_wait_sec = self._parse_duration(initial_wait_str)

                    reminder_intervals_str = item.get('reminder_intervals', [])
                    reminder_intervals_sec = [self._parse_duration(d) for d in reminder_intervals_str]

                    schedules[trader] = {
                        'initial': initial_wait_sec,
                        'reminders': reminder_intervals_sec
                    }
            print("Trader alert schedules loaded successfully.")
        except FileNotFoundError:
            print(f"Info: Config file '{self.config_file}' not found. No delays will be used.")
        except json.JSONDecodeError:
            print(f"Error: Config file '{self.config_file}' contains invalid JSON.")
        return schedules

    def get_trader_schedule(self, trader_name: str) -> dict:
        """
        Gets the full alert schedule (initial wait and reminders in seconds) for a trader.
        """
        return self.trader_schedules.get(trader_name, self.default_schedule)