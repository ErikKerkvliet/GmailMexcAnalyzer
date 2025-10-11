# src/trader_config.py

import json
import re


class TraderConfig:
    """
    Reads and manages the alert schedule and stop-loss configuration for each trader.
    """
    # This default is used if a trader is not in the JSON at all,
    # or if a specific setting is missing for a trader.
    DEFAULT_STOPLOSS = -10.0
    DEFAULT_SCHEDULE = {'initial': 0, 'reminders': []}

    def __init__(self, config_file: str):
        self.config_file = config_file
        self.trader_configs = self._load_config()

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
        """Loads the trader alert schedules and stop-loss from the JSON file."""
        configs = {}
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

                    # Get stop-loss, using None as a placeholder if not present
                    stoploss = item.get('stoploss_percentage')

                    configs[trader] = {
                        'schedule': {
                            'initial': initial_wait_sec,
                            'reminders': reminder_intervals_sec
                        },
                        'stoploss': stoploss
                    }
            print("Trader configurations loaded successfully.")
        except FileNotFoundError:
            print(f"Info: Config file '{self.config_file}' not found. Default settings will be used.")
        except json.JSONDecodeError:
            print(f"Error: Config file '{self.config_file}' contains invalid JSON.")
        return configs

    def get_trader_config(self, trader_name: str) -> dict:
        """
        Gets the full configuration (schedule and stop-loss) for a specific trader.
        Applies defaults for any missing values.
        """
        config = self.trader_configs.get(trader_name, {})

        # Get schedule, fall back to default if not present
        schedule = config.get('schedule', self.DEFAULT_SCHEDULE)

        # Get stop-loss, fall back to default if not present or is None
        stoploss = config.get('stoploss')
        if stoploss is None:
            stoploss = self.DEFAULT_STOPLOSS
        # Ensure stop-loss is always negative
        elif stoploss > 0:
            stoploss = -stoploss

        return {
            'schedule': schedule,
            'stoploss': stoploss
        }