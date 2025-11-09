import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
import threading
import sys
from io import StringIO
import requests
import time

# Dynamically add project subdirectories to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(project_root, 'MexcOrderPriceTracker'))
sys.path.append(os.path.join(project_root, 'PositionOptimizer'))
sys.path.append(os.path.join(project_root, 'TransformOrderData'))

# Now we can import the necessary components
try:
    from transform import transform_and_save_data
    from mexc_price_tracker import OrderTrackerGUI, MexcPriceTracker
    from order_downloader import OrderDownloader
    import position_optimizer
except ImportError as e:
    messagebox.showerror("Import Error",
                         f"Failed to import a required module: {e}\nPlease ensure all project files are in the correct directory structure.")
    sys.exit(1)


class FrameAsRoot:
    """
    A shim/adapter class to make a Frame look like a Tk root window.
    """

    def __init__(self, master_frame):
        self._master = master_frame

    def title(self, text): pass

    def geometry(self, geo_string): pass

    def mainloop(self): pass

    def __getattr__(self, name):
        return getattr(self._master, name)


class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Trading Data Analysis Suite")
        self.geometry("1600x900")

        self.project_root = os.path.dirname(os.path.abspath(__file__)) # This line is added

        self.selected_file_name = None
        self.transformed_file_path = None
        self.price_tracker_gui = None
        self.price_tracker = MexcPriceTracker()

        # --- Main Layout ---
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(main_frame, width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)

        self.right_panel = ttk.Frame(main_frame)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # --- UI Sections ---
        self._create_download_section(left_panel)
        self._create_file_selection_section(left_panel)
        self._create_actions_section(left_panel)
        self._create_log_section(left_panel)

    def _create_download_section(self, parent):
        download_frame = ttk.LabelFrame(parent, text="0. Download New Orders (Optional)", padding="10")
        download_frame.pack(fill=tk.X, pady=(0, 10))
        download_frame.columnconfigure(1, weight=1)
        ttk.Label(download_frame, text="Trader UID:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5), pady=2)
        self.uid_entry = ttk.Entry(download_frame)
        self.uid_entry.grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Label(download_frame, text="Pages to Download:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=2)
        self.pages_entry = ttk.Entry(download_frame)
        self.pages_entry.insert(0, "1")
        self.pages_entry.grid(row=1, column=1, sticky="ew", pady=2)
        self.download_button = ttk.Button(download_frame, text="Start Download", command=self.start_download)
        self.download_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    def _create_file_selection_section(self, parent):
        file_frame = ttk.LabelFrame(parent, text="1. Select Input File", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        self.select_button = ttk.Button(file_frame, text="Browse for Order File", command=self.select_file)
        self.select_button.pack(fill=tk.X)
        self.file_label = ttk.Label(file_frame, text="No file selected", wraplength=380)
        self.file_label.pack(pady=(5, 0))

    def _create_actions_section(self, parent):
        actions_frame = ttk.LabelFrame(parent, text="2. Available Actions", padding="10")
        actions_frame.pack(fill=tk.X, pady=10)
        self.transform_button = ttk.Button(actions_frame, text="Transform Data", command=self.run_transformation,
                                           state=tk.DISABLED)
        self.transform_button.pack(fill=tk.X, pady=5)
        self.load_tracker_button = ttk.Button(actions_frame, text="Load in Price Tracker",
                                              command=self.run_price_tracker, state=tk.DISABLED)
        self.load_tracker_button.pack(fill=tk.X, pady=5)
        self.optimizer_button = ttk.Button(actions_frame, text="Run Position Optimizer", command=self.run_optimizer,
                                           state=tk.DISABLED)
        self.optimizer_button.pack(fill=tk.X, pady=5)

        # --- Inputs ---
        def create_input_row(parent, label_text, default_value=""):
            frame = ttk.Frame(parent)
            frame.pack(fill=tk.X, pady=(5, 0))
            ttk.Label(frame, text=label_text).pack(side=tk.LEFT)
            entry = ttk.Entry(frame, width=15)
            entry.insert(0, default_value)
            entry.pack(side=tk.RIGHT)
            return entry

        self.capital_entry = create_input_row(actions_frame, "Initial Capital (USDT):", "1000.0")
        self.cost_entry = create_input_row(actions_frame, "Transaction Cost (USDT):", "0.0")
        self.stoploss_entry = create_input_row(actions_frame, "Stoploss ROI (%):")
        self.takeprofit_entry = create_input_row(actions_frame, "Take-profit ROI (%):")
        self.max_ratio_entry = create_input_row(actions_frame, "Max Order Ratio (%):", "10.0")

    def _create_log_section(self, parent):
        log_frame = ttk.LabelFrame(parent, text="Log Output", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scrollbar.set)

    def log(self, message):
        self.after(0, lambda: self._log_append(message))

    def _log_append(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.update_idletasks()

    def clear_right_panel(self):
        for widget in self.right_panel.winfo_children():
            widget.destroy()

    def select_file(self):
        transform_input_dir = os.path.join(project_root, 'TransformOrderData', 'orders')
        if not os.path.exists(transform_input_dir): os.makedirs(transform_input_dir)
        filepath = filedialog.askopenfilename(initialdir=transform_input_dir, title="Select a JSON order file",
                                              filetypes=(("JSON files", "*.json"),))
        if filepath: self._update_selected_file(filepath)

    def _update_selected_file(self, filepath):
        self.selected_file_name = os.path.splitext(os.path.basename(filepath))[0]
        self.file_label.config(text=f"Selected: {os.path.basename(filepath)}")
        self.log(f"Selected input file: {os.path.basename(filepath)}")
        self.transformed_file_path = None
        self.transform_button.config(state=tk.NORMAL)
        self.load_tracker_button.config(state=tk.DISABLED)
        self.optimizer_button.config(state=tk.DISABLED)

    def run_transformation(self):
        if not self.selected_file_name: return
        input_path = os.path.join(project_root, 'TransformOrderData', 'orders', f"{self.selected_file_name}.json")
        output_dir = os.path.join(project_root, 'MexcOrderPriceTracker', 'order_lists')
        output_path = os.path.join(output_dir, f"{self.selected_file_name}.json")
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        try:
            self.log("Starting data transformation...")
            transform_and_save_data(input_path, output_path)
            self.transformed_file_path = output_path
            self.log(f"Transformation complete. Output saved to:\n{output_path}")
            self.load_tracker_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Transformation failed: {e}")

    def run_price_tracker(self):
        if not self.transformed_file_path or not os.path.exists(self.transformed_file_path): return
        self.clear_right_panel()
        self.log("Loading Price Tracker GUI...")
        tracker_module = sys.modules['mexc_price_tracker']
        tracker_module.FILENAME = self.transformed_file_path
        try:
            self.price_tracker_gui = OrderTrackerGUI(FrameAsRoot(self.right_panel), tracker=self.price_tracker,
                                                     main_app=self)
            self.log("Price Tracker loaded.")
            self.after(1000, self.check_for_optimizer_data)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load Price Tracker: {e}")

    def run_optimizer(self):
        rate_dir = os.path.join(project_root, 'PositionOptimizer', 'order_rates')
        all_path = os.path.join(rate_dir, f"{self.selected_file_name}.json")
        final_path = None
        if os.path.exists(all_path):
            final_path = all_path
        else:  # Check for single order files
            if os.path.exists(rate_dir):
                for f in os.listdir(rate_dir):
                    if f.startswith(f"order_") and f.endswith('.json'):
                        final_path = os.path.join(rate_dir, f)
                        break
        if not final_path:
            messagebox.showerror("Error", "No optimizer data found. Please export data from the Price Tracker first.")
            return
        self.clear_right_panel()
        self.log(f"Running Position Optimizer on {os.path.basename(final_path)}...")
        output_text = tk.Text(self.right_panel, wrap=tk.WORD, font=("Courier", 10))
        output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        threading.Thread(target=self._run_optimizer_thread, args=(final_path, output_text), daemon=True).start()

    def _run_optimizer_thread(self, file_path, output_widget):
        try:
            initial_capital = float(self.capital_entry.get())
            transaction_cost = float(self.cost_entry.get())
            stop_loss_roi = float(self.stoploss_entry.get()) if self.stoploss_entry.get() else None
            take_profit_roi = float(self.takeprofit_entry.get()) if self.takeprofit_entry.get() else None
            max_order_ratio = float(self.max_ratio_entry.get()) if self.max_ratio_entry.get() else None
        except ValueError:
            messagebox.showerror("Input Error", "Please check that all numerical inputs are valid numbers.")
            return

        old_stdout, sys.stdout = sys.stdout, StringIO()
        try:
            optimizer_module = sys.modules['position_optimizer']
            optimizer_module.run_analysis(
                file_path=file_path,
                capital=initial_capital,
                cost=transaction_cost,
                sl_roi=stop_loss_roi,
                tp_roi=take_profit_roi,
                max_order_ratio=max_order_ratio
            )
            output = sys.stdout.getvalue()
            self.log("Position Optimizer finished.")
            self.after(0, lambda: output_widget.insert(tk.END, output))
        except Exception as e:
            self.log(f"An error occurred in Position Optimizer:\n{e}")
        finally:
            sys.stdout = old_stdout

    def check_for_optimizer_data(self):
        if not self.selected_file_name:
            self.after(1000, self.check_for_optimizer_data);
            return
        rate_dir = os.path.join(project_root, 'PositionOptimizer', 'order_rates')
        all_path = os.path.join(rate_dir, f"{self.selected_file_name}.json")
        file_exists = os.path.exists(all_path)
        if file_exists and os.path.exists(rate_dir):
            self.optimizer_button.config(state=tk.NORMAL)
            self.log("Optimizer data found. 'Run Position Optimizer' is now available.")
        if not file_exists:
            self.after(1000, self.check_for_optimizer_data)

    def start_download(self):
        """
        Initiates the order download process in a separate thread.
        """
        trader_uid = self.uid_entry.get().strip()
        if not trader_uid:
            messagebox.showerror("Input Error", "Trader UID cannot be empty.")
            return
        try:
            pages = int(self.pages_entry.get())
            if pages <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Input Error", "Please enter a valid positive number for pages.")
            return

        self.log("Starting download process...")
        self.download_button.config(state=tk.DISABLED)
        # Run the download in a background thread to prevent the GUI from freezing
        threading.Thread(
            target=self._run_download_thread,
            args=(trader_uid, pages),
            daemon=True
        ).start()

    def _run_download_thread(self, uid: str, num_pages: int):
        """
        Worker function that runs the download and handles the result.
        This function is executed in a background thread.
        """
        try:
            # The logger is passed to the downloader to log messages directly to the GUI
            downloader = OrderDownloader(uid=uid, num_pages=num_pages, logger=self.log)
            saved_file_path = downloader.run_download()

            if saved_file_path:
                # If download is successful, update the GUI from the main thread
                self.after(0, self._update_selected_file, saved_file_path)
            else:
                self.log("Download failed or was aborted. Please check the logs for details.")

        except Exception as e:
            # Log any unexpected exceptions that occur during the download process
            self.log(f"An unexpected error occurred during download: {e}")

        finally:
            # Always re-enable the download button, ensuring it's done on the main thread
            self.after(0, lambda: self.download_button.config(state=tk.NORMAL))


if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()