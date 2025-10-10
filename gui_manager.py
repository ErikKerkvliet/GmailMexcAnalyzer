# gui_manager.py

import tkinter as tk
from tkinter import messagebox, ttk
from src.database_manager import DatabaseManager

DB_FILE = "trades.db"


class TradeManagerApp:
    def __init__(self, root):
        self.db_manager = DatabaseManager(DB_FILE)
        self.root = root
        self.root.title("Trade Manager - Open Positions")
        self.root.geometry("750x450")

        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))
        # Style for the status message
        style.configure("Status.TLabel", foreground="red", font=("Helvetica", 12))

        # Style for alternating row colors and column separators
        style.configure("Treeview", rowheight=25)
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

        # Add borders to the cells for column separators
        style.configure("Treeview",
                        background="white",
                        fieldbackground="white",
                        borderwidth=1,
                        relief="solid")

        self.tree_colors = {
            'even': '#FFFFFF',  # White for even rows
            'odd': '#5f5f5f'  # Light gray for odd rows
        }

        # --- Top Frame for Labels ---
        top_frame = ttk.Frame(root, padding=(10, 10, 10, 0))
        top_frame.pack(fill=tk.X)

        title_label = ttk.Label(top_frame, text="Open trades:", font=("Helvetica", 12))
        title_label.pack(side=tk.LEFT)

        # A separate label for the status message
        self.status_label = ttk.Label(top_frame, text="", style="Status.TLabel")
        self.status_label.pack(side=tk.LEFT, padx=150)

        # --- Frame for the Table ---
        table_frame = ttk.Frame(root, padding=(10, 0, 10, 10))
        table_frame.pack(fill=tk.BOTH, expand=True)

        # The 'columns' tuple contains all the data we want to store in a row.
        self.columns = ('id', 'pair', 'direction', 'trader', 'entry_price', 'open_time')
        # The 'displaycolumns' tuple determines which columns are VISIBLE.
        display_columns = ('pair', 'direction', 'trader', 'entry_price', 'open_time')

        self.tree = ttk.Treeview(table_frame, columns=self.columns, displaycolumns=display_columns, show='headings',
                                 style="Treeview")

        # Define the headers for the VISIBLE columns
        self.tree.heading('pair', text='Crypto Pair')
        self.tree.heading('direction', text='Direction')
        self.tree.heading('trader', text='Trader')
        self.tree.heading('entry_price', text='Entry Price')
        self.tree.heading('open_time', text='Opened At')

        # Define the column widths for the VISIBLE columns
        self.tree.column('pair', width=120, anchor=tk.W)
        self.tree.column('direction', width=80, anchor=tk.W)
        self.tree.column('trader', width=120, anchor=tk.W)
        self.tree.column('entry_price', width=80, anchor=tk.E)
        self.tree.column('open_time', width=150, anchor=tk.E)

        # Configure tags for alternating row colors
        self.tree.tag_configure('evenrow', background='#FFFFFF')
        self.tree.tag_configure('oddrow', background='#F0F0F0')

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=scrollbar.set)

        # --- Frame for the Buttons ---
        button_frame = ttk.Frame(root, padding="10")
        button_frame.pack(fill=tk.X)

        close_button = ttk.Button(button_frame, text="Close Selected Trade", command=self.close_selected_trade)
        close_button.pack(side=tk.LEFT, padx=5)

        refresh_button = ttk.Button(button_frame, text="Refresh", command=self.populate_trades_list)
        refresh_button.pack(side=tk.LEFT, padx=5)

        self.populate_trades_list()

    def populate_trades_list(self):
        """Fetches open trades from the DB and populates the Treeview table."""
        # First, clear the table and the status message
        self.status_label.config(text="")
        for item in self.tree.get_children():
            self.tree.delete(item)

        open_trades = self.db_manager.get_open_trades_details()

        if not open_trades:
            # Show the message in the status label above the table
            self.status_label.config(text="No open trades found.")
            return

        for index, trade in enumerate(open_trades):
            values_tuple = (
                trade['id'],
                f" {trade['crypto_pair']}",
                f" {trade['direction']}",
                f" {trade['trader']}",
                f" ${trade['entry_price']:.4f}",
                f" {trade['open_time'][0:-11]} "
            )
            # Alternate between even and odd row tags
            tag = 'evenrow' if index % 2 == 0 else 'oddrow'
            self.tree.insert('', 'end', values=values_tuple, tags=(tag,))

    def close_selected_trade(self):
        """Closes the trade that is currently selected in the table."""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("No selection", "Please select a trade from the table first.")
            return

        item_data = self.tree.item(selected_item)
        values = item_data['values']

        if not values:
            messagebox.showerror("Error", "Could not read the selected trade.")
            return

        # The ID is still the first value in the 'values' tuple, even though it's hidden.
        trade_id = values[0]
        trade_pair = values[1]
        trade_trader = values[3]

        confirm = messagebox.askyesno("Confirmation",
                                      f"Are you sure you want to close the trade {trade_pair} from {trade_trader}?")

        if confirm:
            success = self.db_manager.close_trade_manually(trade_id)
            if success:
                self.populate_trades_list()
            else:
                messagebox.showerror("Database Error", f"Could not close trade {trade_id}.")


def main():
    root = tk.Tk()
    app = TradeManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()