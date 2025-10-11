# gui_manager.py

import tkinter as tk
from tkinter import messagebox, ttk
from src.database_manager import DatabaseManager
from datetime import datetime
from tkcalendar import DateEntry

DB_FILE = "trades.db"


class TradeManagerApp:
    def __init__(self, root):
        self.db_manager = DatabaseManager(DB_FILE)
        self.root = root
        self.root.title("Trade Manager - All Trades")
        self.root.geometry("1000x400")

        # --- DATA STORAGE & SORTING STATE ---
        self.all_trades_cache = []
        self.current_sort_column = "open_time"
        self.sort_direction = True

        # --- FILTER VARIABLES ---
        self.filter_open_var = tk.BooleanVar(value=True)
        self.filter_closed_var = tk.BooleanVar(value=False)
        self.filter_trader_var = tk.StringVar(value="All")
        self.filter_start_date_var = tk.StringVar()
        self.filter_end_date_var = tk.StringVar()

        # --- GUI STYLING ---
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))
        style.configure("Status.TLabel", foreground="blue", font=("Helvetica", 10))

        # --- Main Layout Frames ---
        filter_frame = ttk.Frame(root, padding="10")
        filter_frame.pack(side=tk.TOP, fill=tk.X)
        button_frame = ttk.Frame(root, padding="10")
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        table_frame = ttk.Frame(root, padding=(10, 0, 10, 10))
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # --- FILTER WIDGETS ---
        status_filter_frame = ttk.LabelFrame(filter_frame, text="Status Filter")
        status_filter_frame.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Checkbutton(status_filter_frame, text="Open", variable=self.filter_open_var,
                        command=self.apply_filters).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(status_filter_frame, text="Closed", variable=self.filter_closed_var,
                        command=self.apply_filters).pack(side=tk.LEFT, padx=5)

        trader_filter_frame = ttk.LabelFrame(filter_frame, text="Trader Filter")
        trader_filter_frame.pack(side=tk.LEFT, padx=5, fill=tk.Y)
        unique_traders = ["All"] + self.db_manager.get_unique_traders()
        self.trader_combobox = ttk.Combobox(trader_filter_frame, textvariable=self.filter_trader_var,
                                            values=unique_traders, state="readonly")
        self.trader_combobox.pack(side=tk.LEFT, padx=5)
        self.trader_combobox.bind("<<ComboboxSelected>>", self.apply_filters)

        # --- UPDATED: Date filter now uses DD-MM-YYYY format ---
        date_filter_frame = ttk.LabelFrame(filter_frame, text="Date Filter (DD-MM-YYYY)")
        date_filter_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.start_date_entry = DateEntry(date_filter_frame, width=12, background='darkblue',
                                          foreground='white', borderwidth=2,
                                          date_pattern='dd-mm-y', textvariable=self.filter_start_date_var)
        self.start_date_entry.pack(side=tk.LEFT, padx=5)
        self.start_date_entry.delete(0, "end")

        self.end_date_entry = DateEntry(date_filter_frame, width=12, background='darkblue',
                                        foreground='white', borderwidth=2,
                                        date_pattern='dd-mm-y', textvariable=self.filter_end_date_var)
        self.end_date_entry.pack(side=tk.LEFT, padx=5)
        self.end_date_entry.delete(0, "end")

        ttk.Button(date_filter_frame, text="Apply", command=self.apply_filters).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(date_filter_frame, text="Clear", command=self._clear_date_filter).pack(side=tk.LEFT, padx=5, pady=5)

        self.status_label = ttk.Label(filter_frame, text="", style="Status.TLabel")
        self.status_label.pack(side=tk.BOTTOM, anchor=tk.E)

        # --- ACTION BUTTONS ---
        close_button = ttk.Button(button_frame, text="Close Selected Trade", command=self.close_selected_trade)
        close_button.pack(side=tk.LEFT, padx=5)
        refresh_button = ttk.Button(button_frame, text="Refresh Data", command=self.fetch_all_trades)
        refresh_button.pack(side=tk.LEFT, padx=5)

        # --- TREEVIEW TABLE SETUP ---
        self.columns = ('id', 'status', 'pair', 'direction', 'trader', 'entry_price', 'open_time', 'timestamp')
        display_columns = ('status', 'pair', 'direction', 'trader', 'entry_price', 'open_time')
        self.tree = ttk.Treeview(table_frame, columns=self.columns, displaycolumns=display_columns, show='headings')

        for col in display_columns:
            self.tree.heading(col, text=col.replace('_', ' ').title(),
                              command=lambda c=col: self.sort_column_by(c, True))

        self.tree.column('status', width=80, anchor=tk.CENTER)
        self.tree.column('pair', width=120, anchor=tk.W)
        self.tree.column('direction', width=80, anchor=tk.W)
        self.tree.column('trader', width=90, anchor=tk.W)
        self.tree.column('entry_price', width=50, anchor=tk.E)
        self.tree.column('open_time', width=50, anchor=tk.CENTER)

        self.tree.tag_configure('OPEN_even', background='#d9f2d9')
        self.tree.tag_configure('OPEN_odd', background='#c8e6c9')
        self.tree.tag_configure('CLOSED_even', background='#f2d9d9')
        self.tree.tag_configure('CLOSED_odd', background='#ffcdd2')

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=scrollbar.set)

        self.fetch_all_trades()

    def fetch_all_trades(self):
        self.all_trades_cache = self.db_manager.get_all_trades_details()
        self.apply_filters()

    def _clear_date_filter(self):
        self.filter_start_date_var.set("")
        self.filter_end_date_var.set("")
        self.apply_filters()

    def apply_filters(self, event=None):
        show_open = self.filter_open_var.get()
        show_closed = self.filter_closed_var.get()
        selected_trader = self.filter_trader_var.get()
        start_date_str = self.filter_start_date_var.get()
        end_date_str = self.filter_end_date_var.get()

        start_date, end_date = None, None
        try:
            # --- UPDATED: Parse DD-MM-YYYY format ---
            if start_date_str:
                start_date = datetime.strptime(start_date_str, "%d-%m-%Y").date()
        except ValueError:
            messagebox.showerror("Invalid Date", "Start Date format must be DD-MM-YYYY.")
            return
        try:
            # --- UPDATED: Parse DD-MM-YYYY format ---
            if end_date_str:
                end_date = datetime.strptime(end_date_str, "%d-%m-%Y").date()
        except ValueError:
            messagebox.showerror("Invalid Date", "End Date format must be DD-MM-YYYY.")
            return

        filtered_trades = []
        for trade in self.all_trades_cache:
            status_match = (show_open and trade['status'] == 'OPEN') or \
                           (show_closed and trade['status'] == 'CLOSED')
            if not status_match: continue

            trader_match = (selected_trader == "All" or trade['trader'] == selected_trader)
            if not trader_match: continue

            trade_date = datetime.fromtimestamp(trade['timestamp']).date()
            date_match = False
            if start_date and end_date:
                if start_date <= trade_date <= end_date:
                    date_match = True
            elif start_date:
                if trade_date == start_date:
                    date_match = True
            elif end_date:
                if trade_date == end_date:
                    date_match = True
            else:
                date_match = True

            if not date_match:
                continue

            filtered_trades.append(trade)

        self.populate_trades_list(filtered_trades)

    def populate_trades_list(self, trades):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for index, trade in enumerate(trades):
            parity = 'even' if index % 2 == 0 else 'odd'
            row_tag = f"{trade['status']}_{parity}"

            # --- UPDATED: Convert timestamp to DD-MM-YYYY for display ---
            display_date = datetime.fromtimestamp(trade['timestamp']).strftime('%d-%m-%Y')

            values_tuple = (
                trade['id'], trade['status'], f" {trade['crypto_pair']}", f" {trade['direction']}",
                f" {trade['trader']}", f" ${trade['entry_price']:.4f}", f" {display_date}",
                trade['timestamp']
            )
            self.tree.insert('', 'end', values=values_tuple, tags=(row_tag,))

        self.status_label.config(text=f"Showing {len(trades)} trades")
        self.sort_column_by(self.current_sort_column, False)

    def sort_column_by(self, col, reverse_on_click):
        if self.current_sort_column == col and reverse_on_click:
            self.sort_direction = not self.sort_direction
        else:
            self.current_sort_column = col
            self.sort_direction = True

        items = []
        for item_id in self.tree.get_children(''):
            if col == 'open_time':
                col_index = self.columns.index('timestamp')
                value = int(self.tree.item(item_id)['values'][col_index])
            else:
                col_index = self.columns.index(col)
                value = self.tree.item(item_id)['values'][col_index]
                if col == 'entry_price':
                    value = float(str(value).replace('$', '').strip())
            items.append((value, item_id))

        items.sort(key=lambda x: x[0], reverse=self.sort_direction)

        for index, (val, item_id) in enumerate(items):
            self.tree.move(item_id, '', index)

        for c in self.columns:
            if c != 'timestamp':
                self.tree.heading(c, text=c.replace('_', ' ').title())

        arrow = ' ▼' if self.sort_direction else ' ▲'
        current_header_text = self.tree.heading(col, "text")
        self.tree.heading(col, text=current_header_text + arrow)

    def close_selected_trade(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("No selection", "Please select a trade from the table first.")
            return
        values = self.tree.item(selected_item, 'values')
        if not values:
            messagebox.showerror("Error", "Could not read the selected trade.")
            return
        trade_id = values[self.columns.index('id')]
        trade_status = values[self.columns.index('status')]
        trade_pair = values[self.columns.index('pair')]
        trade_trader = values[self.columns.index('trader')]
        if trade_status == 'CLOSED':
            messagebox.showinfo("Already Closed", f"The trade for {trade_pair} is already closed.")
            return

        success = self.db_manager.close_trade_manually(trade_id)
        if success:
            self.fetch_all_trades()
        else:
            messagebox.showerror("Database Error", f"Could not close trade {trade_id}.")


def main():
    root = tk.Tk()
    app = TradeManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()