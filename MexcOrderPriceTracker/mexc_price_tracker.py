import requests
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import time
import threading
import urllib.parse

ORDER_LIST_DIR = '/home/erik/PycharmProjects/GmailMexcAnalyzer/MexcOrderPriceTracker/order_lists'
ORDER_LIST_NAME = 'CopyTraderNormie'
EXPORT_DIR = '../PositionOptimizer/order_rates/'
FILENAME = f'{ORDER_LIST_DIR}/{ORDER_LIST_NAME}.json'


class MexcPriceTracker:
    def __init__(self):
        self.cache = {}
        self.rate_limit_delay = 0.25
        self.max_retries = 3
        self.mexc_api_url = "https://api.mexc.com"

    def get_kline_data(self, symbol, interval, start_time, end_time):
        """
        Public method to get k-line data. Acts as a caching layer.
        It checks the cache first and, if data is not present, calls a worker
        to fetch it. The result (successful or failed) is then cached.
        """
        cache_key = f"{symbol}_{interval}_{start_time}_{end_time}"
        if cache_key in self.cache:
            klines = self.cache[cache_key]
            # Reconstruct URL for the return signature, even for a cache hit
            start_ts_ms = int(start_time.timestamp() * 1000)
            end_ts_ms = int(end_time.timestamp() * 1000)
            params = {'symbol': symbol, 'interval': interval, 'startTime': start_ts_ms, 'endTime': end_ts_ms}
            full_url = f"{self.mexc_api_url}/api/v3/klines?{urllib.parse.urlencode(params)}"
            return klines, full_url

        # If not in cache, call the recursive worker to fetch the data
        klines, full_url = self._get_kline_data_recursive(symbol, interval, start_time, end_time)

        # Cache the result, whether it's data (klines) or None (failure)
        self.cache[cache_key] = klines
        return klines, full_url

    def _get_kline_data_recursive(self, symbol, interval, start_time, end_time):
        """
        Worker method that fetches k-line data with retries and interval adjustments.
        This method does not interact with the cache directly.
        """
        start_ts_ms = int(start_time.timestamp() * 1000)
        end_ts_ms = int(end_time.timestamp() * 1000)
        base_url = f"{self.mexc_api_url}/api/v3/klines"
        params = {'symbol': symbol, 'interval': interval, 'startTime': start_ts_ms, 'endTime': end_ts_ms}
        full_url = f"{base_url}?{urllib.parse.urlencode(params)}"

        for attempt in range(self.max_retries):
            try:
                time.sleep(self.rate_limit_delay)
                response = requests.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()
                if not data:
                    # If no data, try the next larger interval. Stop if we're already at the largest.
                    if interval == '1h': break
                    next_interval = '5m' if interval == '1m' else '15m' if interval == '5m' else '1h'
                    return self._get_kline_data_recursive(symbol, next_interval, start_time, end_time)

                # On success, format the data and return it
                formatted_klines = [[int(k[0]), k[1], k[2], k[3], k[4], k[5], int(k[0]) + 60000, k[6], 0, '0', '0', '0']
                                    for k in data]
                return formatted_klines, full_url

            except requests.exceptions.RequestException:
                # If the request fails, try the next larger interval. Stop if we're already at the largest.
                if interval == '1h': break
                time.sleep(1)
                next_interval = '5m' if interval == '1m' else '15m' if interval == '5m' else '1h'
                return self._get_kline_data_recursive(symbol, next_interval, start_time, end_time)

        # This point is reached only after all retries and intervals have failed.
        return None, full_url

    def determine_interval(self, duration_minutes):
        if duration_minutes <= 180:
            return '1m'
        elif duration_minutes <= 720:
            return '5m'
        else:
            return '1h'

    def parse_order_time(self, time_str):
        return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')


class OrderTrackerGUI:
    def __init__(self, root, tracker=None, main_app=None):
        self.root = root
        self.main_app = main_app
        self.tracker = tracker or MexcPriceTracker()
        self.orders = []
        self.current_order_kline_data = None
        self.current_selected_order = None
        try:
            with open(FILENAME, 'r') as f:
                self.orders = json.load(f).get('orders', [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading order file: {e}")
        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        left_frame = ttk.Frame(main_frame, width=720)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))

        title_label = ttk.Label(left_frame, text="Orders", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))

        columns = ('Symbol', 'Amount', 'Leverage', 'Direction', 'Open Time', 'Open Price', 'Close Price', 'P&L')
        self.tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=25)
        for col in columns: self.tree.heading(col, text=col)

        self.tree.column('Symbol', width=100);
        self.tree.column('Direction', width=70, anchor=tk.CENTER);
        self.tree.column('Leverage', width=70, anchor=tk.CENTER);
        self.tree.column('Open Time', width=140);
        self.tree.column('Amount', width=100);
        self.tree.column('Open Price', width=90);
        self.tree.column('Close Price', width=90);
        self.tree.column('P&L', width=90)

        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set);
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for idx, order in enumerate(self.orders):
            pnl_str = f"{order['pnl']:+.4f}"
            tags = ['profit' if order['pnl'] > 0 else 'loss']
            direction = order.get('direction', 'N/A')
            tags.append(direction)
            self.tree.insert('', tk.END, iid=idx, values=(
                order['symbol'], order['amount'], order.get('leverage', 'N/A'), direction.title(), order['open_time'],
                f"{order['open_price']:.6f}", f"{order['close_price']:.6f}", pnl_str), tags=tuple(tags))

        self.tree.tag_configure('profit', foreground='green');
        self.tree.tag_configure('loss', foreground='red')
        self.tree.tag_configure('long', foreground='green');
        self.tree.tag_configure('short', foreground='red')
        self.tree.bind('<<TreeviewSelect>>', self.on_order_select)

        self.right_frame = ttk.Frame(main_frame, width=800);
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.chart_frame = ttk.Frame(self.right_frame);
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))
        self.profit_info_frame = ttk.Frame(self.right_frame);
        self.profit_info_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        self.profit_label = ttk.Label(self.profit_info_frame, text="", font=('Arial', 12, 'bold'), anchor='center');
        self.profit_label.pack(pady=5)
        self.export_button_frame = ttk.Frame(self.right_frame);
        self.export_button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        self.export_all_btn = ttk.Button(self.export_button_frame, text="Load All Orders Data",
                                         command=self.load_all_orders_data)
        self.export_all_btn.pack(pady=2, fill=tk.X)
        if not self.orders:
            self.export_all_btn.config(state=tk.DISABLED)

        self.export_cached_btn = ttk.Button(self.export_button_frame, text="Export All Cached Orders",
                                            command=self.export_all_cached_orders)
        self.export_cached_btn.pack(pady=2, fill=tk.X)

        self.export_current_btn = ttk.Button(self.export_button_frame, text="Export Current Order Data",
                                             state=tk.DISABLED, command=self.export_single_order_data)
        self.export_current_btn.pack(pady=2, fill=tk.X)

        self.info_label = ttk.Label(self.chart_frame, text="Select an order to view its chart", font=('Arial', 12));
        self.info_label.pack(expand=True)

    def on_order_select(self, event):
        if not self.tree.selection(): return
        self.profit_label.config(text="")
        # Reset current data
        self.current_order_kline_data = None
        self.current_selected_order = None
        self.export_current_btn.config(state=tk.DISABLED)

        order_idx = int(self.tree.selection()[0])
        order = self.orders[order_idx]
        self.current_selected_order = order

        for widget in self.chart_frame.winfo_children(): widget.destroy()
        loading_label = ttk.Label(self.chart_frame, text="Loading chart...", font=('Arial', 12));
        loading_label.pack(expand=True)
        self.root.update()
        self.plot_order_chart(order)

    def _simulate_single_trade_roi(self, order, kline_data, sl_roi_pct, tp_roi_pct):
        """Calculates the ROI of a single trade based on provided SL/TP levels."""
        direction = order.get("direction", "long")
        leverage = float(order.get('leverage', '1x').replace('x', '')) or 1

        # --- BUG FIX HERE ---
        # The key for entry price in this context is 'open_price'
        entry_price = order['open_price']

        sl_price_pct = sl_roi_pct / leverage
        tp_price_pct = tp_roi_pct / leverage

        if direction == 'long':
            sl_price = entry_price * (1 - sl_price_pct / 100.0)
            tp_price = entry_price * (1 + tp_price_pct / 100.0)
            for _, _, high, low, *_ in kline_data:
                if float(low) <= sl_price: return -sl_roi_pct
                if float(high) >= tp_price: return tp_roi_pct
        else:  # Short
            sl_price = entry_price * (1 + sl_price_pct / 100.0)
            tp_price = entry_price * (1 - tp_price_pct / 100.0)
            for _, _, high, low, *_ in kline_data:
                if float(high) >= sl_price: return -sl_roi_pct
                if float(low) <= tp_price: return tp_roi_pct

        actual_price_pnl_pct = ((order['close_price'] - order['open_price']) / order['open_price']) * 100
        if direction == 'short': actual_price_pnl_pct *= -1
        return actual_price_pnl_pct * leverage

    def plot_order_chart(self, order, interval=None):
        open_time = self.tracker.parse_order_time(order['open_time'])
        close_time = self.tracker.parse_order_time(order['close_time'])
        duration_minutes = (close_time - open_time).total_seconds() / 60
        interval = interval or self.tracker.determine_interval(duration_minutes)
        for widget in self.chart_frame.winfo_children(): widget.destroy()

        params = {'capital': 1000.0, 'cost': 0.0, 'sl_roi': None, 'tp_roi': None, 'ratio': 10.0}
        if self.main_app:
            try:
                params['capital'] = float(self.main_app.capital_entry.get())
            except (ValueError, TypeError):
                pass
            try:
                params['cost'] = float(self.main_app.cost_entry.get())
            except (ValueError, TypeError):
                pass
            try:
                params['sl_roi'] = float(self.main_app.stoploss_entry.get())
            except (ValueError, TypeError):
                pass
            try:
                params['tp_roi'] = float(self.main_app.takeprofit_entry.get())
            except (ValueError, TypeError):
                pass
            try:
                params['ratio'] = float(self.main_app.max_ratio_entry.get())
            except (ValueError, TypeError):
                pass

        kline_data, _ = self.tracker.get_kline_data(order['symbol'], interval, open_time, close_time)
        self.current_order_kline_data = kline_data

        if not kline_data:
            ttk.Label(self.chart_frame, text="No k-line data available.", foreground='red').pack()
            return

        df = pd.DataFrame(kline_data, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'ct', 'qav', 'not', 'tbav', 'tqav', 'i'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        for col in ['o', 'h', 'l', 'c']: df[col] = df[col].astype(float)

        entry_price = order['open_price']
        df['pct_change'] = ((df['c'] - entry_price) / entry_price) * 100

        fig, ax = plt.subplots(figsize=(10, 5))  # <-- Changed: Figure height reduced
        ax.plot(df['ts'], df['pct_change'], label='Price', linewidth=2)
        ax.fill_between(df['ts'], df['pct_change'], 0, where=(df['pct_change'] >= 0), color='green', alpha=0.2)
        ax.fill_between(df['ts'], df['pct_change'], 0, where=(df['pct_change'] < 0), color='red', alpha=0.2)

        exit_pct = ((order['close_price'] - entry_price) / entry_price) * 100

        # <-- Changed: Legend labels now show the actual prices
        ax.scatter([df['ts'].iloc[0]], [0], c='g', s=150, zorder=5, label=f"{order['open_price']:.6f}")
        ax.scatter([df['ts'].iloc[-1]], [exit_pct], c='k', s=150, zorder=5, label=f"{order['close_price']:.6f}")

        direction = order.get("direction", "long")
        leverage = float(order.get('leverage', '1x').replace('x', '')) or 1

        if params['sl_roi'] is not None:
            sl_price_pct = -abs(params['sl_roi']) / leverage
            if direction == 'short': sl_price_pct *= -1
            ax.axhline(y=sl_price_pct, color='red', linestyle='--', label=f'SL ROI: {params["sl_roi"]}%')
        if params['tp_roi'] is not None:
            tp_price_pct = abs(params['tp_roi']) / leverage
            if direction == 'short': tp_price_pct *= -1
            ax.axhline(y=tp_price_pct, color='green', linestyle='--', label=f'TP ROI: {params["tp_roi"]}%')

        ax.axhline(y=0, color='gray', linestyle='-')

        leverage_info = order.get('leverage', '')
        direction_info = f" ({direction.upper()})"
        price_total = float(order['amount'].split(' ')[0]) * order['close_price']
        title = f"{order['symbol']}{direction_info} - {leverage_info} | Total Price: {price_total:.2f} USDT\n"
        title += f"{order['open_time']} to {order['close_time']}\n"

        ax.set_title(title, fontsize=11, fontweight='bold')

        ax.legend();
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:+.2f}%'))
        plt.tight_layout()

        FigureCanvasTkAgg(fig, master=self.chart_frame).get_tk_widget().pack(fill=tk.BOTH, expand=True)

        sl_to_sim = abs(params['sl_roi']) if params['sl_roi'] is not None else float('inf')
        tp_to_sim = abs(params['tp_roi']) if params['tp_roi'] is not None else float('inf')

        simulated_roi = self._simulate_single_trade_roi(order, kline_data, sl_to_sim, tp_to_sim)

        capital_at_risk = params['capital'] * (params.get('ratio', 10.0) / 100.0)
        gross_pnl = capital_at_risk * (simulated_roi / 100.0)
        net_pnl = gross_pnl - params['cost']

        self.profit_label.config(text=f"Simulated Net Profit: {net_pnl:+.4f} USDT",
                                 foreground="green" if net_pnl > 0 else "red")
        self.export_current_btn.config(state=tk.NORMAL)

        # Explicitly close the figure to prevent memory leak
        plt.close(fig)

    def load_all_orders_data(self):
        """
        Initiates the process of fetching k-line data for all orders in a background thread.
        """
        if not self.orders:
            messagebox.showwarning("No Orders", "There are no orders to load.")
            return

        if not self.main_app or not self.main_app.selected_file_name:
            messagebox.showerror("Error", "Application context is missing. Cannot determine output filename.")
            return

        self.export_all_btn.config(state=tk.DISABLED)
        self.main_app.log("Starting to load k-line data for all orders...")

        threading.Thread(
            target=self._load_all_data_thread,
            daemon=True
        ).start()

    def _load_all_data_thread(self):
        """
        Worker thread to fetch k-line data for all orders and save it to a file
        compatible with the Position Optimizer.
        """
        all_orders_data = []
        total = len(self.orders)

        for i, order in enumerate(self.orders):
            self.main_app.log(f"Processing order {i + 1}/{total}: {order['symbol']}...")

            open_time = self.tracker.parse_order_time(order['open_time'])
            close_time = self.tracker.parse_order_time(order['close_time'])
            duration_minutes = (close_time - open_time).total_seconds() / 60
            interval = self.tracker.determine_interval(duration_minutes)

            kline_data, _ = self.tracker.get_kline_data(order['symbol'], interval, open_time, close_time)

            if not kline_data:
                self.main_app.log(f"  -> Warning: No k-line data found for order {order['symbol']}. Skipping.")
                continue

            price_data_formatted = []
            for k in kline_data:
                price_data_formatted.append({
                    "timestamp": datetime.fromtimestamp(k[0] / 1000).isoformat(),
                    "open": float(k[1]), "high": float(k[2]),
                    "low": float(k[3]), "close": float(k[4]),
                    "volume": float(k[5])
                })

            pnl_pct = ((order['close_price'] - order['open_price']) / order['open_price']) * 100
            direction = order.get('direction', 'long')
            if direction == 'short':
                pnl_pct *= -1

            optimizer_order = {
                "symbol": order["symbol"], "direction": direction,
                "leverage": order.get("leverage", "1x"), "entry": order["open_price"],
                "exit": order["close_price"], "pnl_pct": pnl_pct,
                "price_data": price_data_formatted
            }
            all_orders_data.append(optimizer_order)

        if not all_orders_data:
            self.main_app.log("Could not process any orders. No data file created.")
            self.root.after(0, lambda: self.export_all_btn.config(state=tk.NORMAL))
            return

        try:
            output_dir = os.path.join(self.main_app.project_root, 'PositionOptimizer', 'order_rates')
            if not os.path.exists(output_dir): os.makedirs(output_dir)
            output_filename = f"{self.main_app.selected_file_name}.json"
            output_path = os.path.join(output_dir, output_filename)

            final_data_structure = {"total_orders": len(all_orders_data), "orders": all_orders_data}

            with open(output_path, 'w') as f:
                json.dump(final_data_structure, f, indent=2)

            self.main_app.log("\n" + "=" * 50)
            self.main_app.log("Successfully loaded and saved all order data.")
            self.main_app.log(f"Optimizer data file created at:\n{output_path}")
            self.main_app.log("=" * 50)

        except Exception as e:
            self.main_app.log(f"Error saving optimizer data file: {e}")
        finally:
            self.root.after(0, lambda: self.export_all_btn.config(state=tk.NORMAL))

    def export_all_cached_orders(self):
        """
        Initiates the process of exporting k-line data for all cached orders in a background thread.
        """
        if not self.tracker.cache:
            messagebox.showinfo("No Cached Data",
                                "There is no cached order data to export. Please view some orders first.")
            return

        if not self.main_app or not self.main_app.selected_file_name:
            messagebox.showerror("Error", "Application context is missing. Cannot determine output filename.")
            return

        self.export_cached_btn.config(state=tk.DISABLED)
        self.main_app.log("Starting to export all cached order data...")

        threading.Thread(
            target=self._export_cached_thread,
            daemon=True
        ).start()

    def _export_cached_thread(self):
        """
        Worker thread that finds all cached orders, formats their data, and saves it
        to a file compatible with the Position Optimizer.
        """
        cached_orders_data = []
        total_orders = len(self.orders)

        # Iterate through all orders to find their corresponding entry in the cache
        for i, order in enumerate(self.orders):
            open_time = self.tracker.parse_order_time(order['open_time'])
            close_time = self.tracker.parse_order_time(order['close_time'])

            # Check potential cache keys for this order, as interval might have been upgraded
            found_kline_data = None
            # Check from largest interval to smallest, as that's the final attempt
            for interval in ['1h', '15m', '5m', '1m']:
                # The cache key needs to match exactly how it was created
                duration_minutes = (close_time - open_time).total_seconds() / 60
                initial_interval = self.tracker.determine_interval(duration_minutes)

                # Check the specific cache key that would have been generated
                cache_key = f"{order['symbol']}_{initial_interval}_{open_time}_{close_time}"

                # This logic is flawed. The original recursive function handles interval changes.
                # A simpler way is to check all possible intervals for a key.
                cache_key_try = f"{order['symbol']}_{interval}_{open_time}_{close_time}"

                if cache_key_try in self.tracker.cache:
                    # Found an entry. If it's not None, it's successful data.
                    if self.tracker.cache[cache_key_try] is not None:
                        found_kline_data = self.tracker.cache[cache_key_try]
                        break  # Stop checking intervals once data is found

            if found_kline_data:
                # If we found valid k-line data in the cache, process it for export
                self.main_app.log(f"Found cached data for order {i + 1}/{total_orders}: {order['symbol']}")

                price_data_formatted = []
                for k in found_kline_data:
                    price_data_formatted.append({
                        "timestamp": datetime.fromtimestamp(k[0] / 1000).isoformat(),
                        "open": float(k[1]), "high": float(k[2]),
                        "low": float(k[3]), "close": float(k[4]),
                        "volume": float(k[5])
                    })

                pnl_pct = ((order['close_price'] - order['open_price']) / order['open_price']) * 100
                direction = order.get('direction', 'long')
                if direction == 'short':
                    pnl_pct *= -1

                optimizer_order = {
                    "symbol": order["symbol"], "direction": direction,
                    "leverage": order.get("leverage", "1x"), "entry": order["open_price"],
                    "exit": order["close_price"], "pnl_pct": pnl_pct,
                    "price_data": price_data_formatted
                }
                cached_orders_data.append(optimizer_order)

        if not cached_orders_data:
            self.main_app.log("No valid cached order data was found to export.")
            self.root.after(0, lambda: self.export_cached_btn.config(state=tk.NORMAL))
            return

        # Save the collected data to a file
        try:
            output_dir = os.path.join(self.main_app.project_root, 'PositionOptimizer', 'order_rates')
            if not os.path.exists(output_dir): os.makedirs(output_dir)

            # Use a distinct filename for cached exports
            output_filename = f"{self.main_app.selected_file_name}_cached.json"
            output_path = os.path.join(output_dir, output_filename)

            final_data_structure = {"total_orders": len(cached_orders_data), "orders": cached_orders_data}

            with open(output_path, 'w') as f:
                json.dump(final_data_structure, f, indent=2)

            self.main_app.log("\n" + "=" * 50)
            self.main_app.log(f"Successfully exported {len(cached_orders_data)} cached orders.")
            self.main_app.log(f"Optimizer data file created at:\n{output_path}")
            self.main_app.log("=" * 50)

        except Exception as e:
            self.main_app.log(f"Error saving cached optimizer data file: {e}")
        finally:
            # Re-enable the button on the main thread
            self.root.after(0, lambda: self.export_cached_btn.config(state=tk.NORMAL))

    def export_single_order_data(self):
        """
        Saves the k-line data for the currently selected order to a file
        compatible with the Position Optimizer.
        """
        if not self.current_selected_order or not self.current_order_kline_data:
            messagebox.showerror("Error", "No order data is currently loaded to export.")
            return

        order = self.current_selected_order
        kline_data = self.current_order_kline_data
        self.main_app.log(f"Exporting data for single order: {order['symbol']}...")

        price_data_formatted = []
        for k in kline_data:
            price_data_formatted.append({
                "timestamp": datetime.fromtimestamp(k[0] / 1000).isoformat(),
                "open": float(k[1]), "high": float(k[2]),
                "low": float(k[3]), "close": float(k[4]),
                "volume": float(k[5])
            })

        pnl_pct = ((order['close_price'] - order['open_price']) / order['open_price']) * 100
        direction = order.get('direction', 'long')
        if direction == 'short': pnl_pct *= -1

        optimizer_order = {
            "symbol": order["symbol"], "direction": direction,
            "leverage": order.get("leverage", "1x"), "entry": order["open_price"],
            "exit": order["close_price"], "pnl_pct": pnl_pct,
            "price_data": price_data_formatted
        }

        try:
            output_dir = os.path.join(self.main_app.project_root, 'PositionOptimizer', 'order_rates')
            if not os.path.exists(output_dir): os.makedirs(output_dir)

            open_time_str = order['open_time'].replace(':', '-').replace(' ', '_')
            output_filename = f"order_{order['symbol']}_{open_time_str}.json"
            output_path = os.path.join(output_dir, output_filename)

            final_data_structure = {"total_orders": 1, "orders": [optimizer_order]}

            with open(output_path, 'w') as f:
                json.dump(final_data_structure, f, indent=2)

            self.main_app.log(f"Successfully exported single order data to:\n{output_path}")
            messagebox.showinfo("Export Successful", f"Order data saved to:\n{output_path}")

        except Exception as e:
            self.main_app.log(f"Error exporting single order data: {e}")
            messagebox.showerror("Export Error", f"An error occurred: {e}")