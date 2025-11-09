import requests
import json
import os
import time
from typing import Callable

class OrderDownloader:
    """
    Handles the downloading and saving of trader order history from the MEXC API.
    """
    BASE_URL = "https://www.mexc.com/api/platform/futures/copyFutures/api/v1/trader/ordersHis/v2"
    # The output directory is set relative to this file's location.
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'orders')
    DELAY_BETWEEN_REQUESTS = 1.0

    def __init__(self, uid: str, num_pages: int, logger: Callable[[str], None] = print):
        """
        Initializes the downloader.

        Args:
            uid (str): The unique identifier (UID) of the trader.
            num_pages (int): The total number of pages to download.
            logger (Callable): A function to log messages, suitable for GUI or console output.
        """
        if not uid or not num_pages > 0:
            raise ValueError("Trader UID must be provided and the number of pages must be a positive integer.")
        self.uid = uid
        self.num_pages = num_pages
        self.log = logger
        self.output_file_path = None

    def run_download(self) -> str | None:
        """
        Executes the entire download and saving process. It fetches order data page by page,
        combines it, and saves it to a JSON file named after the trader's nickname.

        Returns:
            The full path to the saved JSON file if the download is successful, otherwise None.
        """
        self.log(f"Attempting to download {self.num_pages} page(s) for trader UID: {self.uid}")

        try:
            # Step 1: Fetch the first page to identify the trader and get the first batch of orders.
            self.log("Fetching initial page to identify trader...")
            first_page_url = f"{self.BASE_URL}?limit=20&page=1&uid={self.uid}"
            response = requests.get(first_page_url, timeout=15)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            initial_data = response.json()

            # Validate the API response
            if not (initial_data.get("success") and initial_data.get("data", {}).get("content")):
                api_message = initial_data.get('message', 'No message provided by API.')
                self.log(f"Error: Could not fetch initial data or the trader has no public orders.")
                self.log(f"API Message: {api_message}")
                return None

            # Step 2: Extract the trader's nickname for the filename and prepare to collect all orders.
            first_order_list = initial_data["data"]["content"]
            trader_nickname = first_order_list[0].get("traderNickName")

            if not trader_nickname:
                self.log("Warning: Could not find 'traderNickName'. Using a fallback filename.")
                trader_nickname = f"trader_{self.uid}_orders"

            self.log(f"Found trader: '{trader_nickname}'. Proceeding to download...")
            all_orders_content = first_order_list
            self.log(f"  + Page 1 of {self.num_pages}: Success! Found {len(all_orders_content)} orders.")

            # Step 3: Loop through the remaining pages to fetch the rest of the orders.
            if self.num_pages > 1:
                for page_num in range(2, self.num_pages + 1):
                    self.log(f"Fetching page {page_num} of {self.num_pages}...")
                    url = f"{self.BASE_URL}?limit=20&page={page_num}&uid={self.uid}"
                    response = requests.get(url, timeout=15)
                    response.raise_for_status()
                    data = response.json()

                    if data.get("success") and "data" in data and "content" in data["data"]:
                        orders_on_page = data["data"]["content"]
                        if not orders_on_page:
                            self.log(f"  - No more orders found on page {page_num}. Stopping download early.")
                            break
                        all_orders_content.extend(orders_on_page)
                        self.log(f"  + Success! Found {len(orders_on_page)} orders on this page.")
                    else:
                        error_msg = data.get('message', 'Unknown API error')
                        self.log(f"  - API returned an error on page {page_num}: {error_msg}")
                        break
                    time.sleep(self.DELAY_BETWEEN_REQUESTS)

            if not all_orders_content:
                self.log("\nNo orders were downloaded. The output file will not be created.")
                return None

            # Step 4: Construct the final JSON structure and save it to a file.
            os.makedirs(self.OUTPUT_DIR, exist_ok=True)
            final_data_structure = {
                "success": True,
                "code": 0,
                "message": "Combined data from multiple pages.",
                "data": {
                    "pageSize": 20,
                    "totalPage": self.num_pages,
                    "currentPage": self.num_pages,
                    "content": all_orders_content
                }
            }

            self.output_file_path = os.path.join(self.OUTPUT_DIR, f"{trader_nickname}.json")
            with open(self.output_file_path, 'w') as f:
                json.dump(final_data_structure, f, indent=2)

            self.log("\n" + "=" * 50)
            self.log("Download complete!")
            self.log(f"Successfully saved a total of {len(all_orders_content)} orders.")
            self.log(f"File saved to: {self.output_file_path}")
            self.log("=" * 50)
            return self.output_file_path

        except requests.exceptions.RequestException as e:
            self.log(f"A critical network error occurred during download: {e}")
            return None
        except (IOError, json.JSONDecodeError, KeyError, IndexError) as e:
            self.log(f"An error occurred while processing or saving data: {e}")
            return None