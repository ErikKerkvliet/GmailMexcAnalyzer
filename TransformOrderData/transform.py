import json
from datetime import datetime

INPUT_FILE_DIR = 'orders'
OUTPUT_FILE_DIR = '/home/erik/PycharmProjects/GmailMexcAnalyzer/MexcOrderPriceTracker/order_lists'

FILE_NAME = 'gw_management'

def transform_and_save_data(input_file_path, output_file_path):
    """
    Transforms raw order data, including extracting the trade direction, and saves it.
    """
    try:
        with open(input_file_path, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        with open(output_file_path, 'w') as f:
            json.dump({"orders": []}, f, indent=2)
        print(f"Error reading {input_file_path} or file not found. Created an empty {output_file_path}.")
        return

    transformed_orders = []
    # Use .get() to safely access nested keys
    for order in data.get("data", {}).get("content", []):
        open_time = datetime.fromtimestamp(order['openTime'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        close_time = datetime.fromtimestamp(order['closeTime'] / 1000).strftime('%Y-%m-%d %H:%M:%S')

        # Determine direction: 1 for Buy (Long), 2 for Sell (Short)
        direction = "long" if order.get('positionType') == 1 else "short"

        transformed_order = {
            "symbol": order["symbol"].replace('_', ''),
            "amount": f"{order['amount']} {order['symbol'].split('_')[0]}",
            "leverage": f"{order['leverage']}x",
            "direction": direction,  # Add the direction field
            "open_time": open_time,
            "close_time": close_time,
            "open_price": order["openAvgPrice"],
            "close_price": order["closeAvgPrice"],
            "pnl": order["released"]
        }
        transformed_orders.append(transformed_order)

    output_data = {"orders": transformed_orders}

    with open(output_file_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"Data successfully transformed and saved to {output_file_path}")

# Example of how to run this script
# transform_and_save_data(f'{INPUT_FILE_DIR}/{FILE_NAME}.json', f'{OUTPUT_FILE_DIR}/{FILE_NAME}.json')