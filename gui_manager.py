# gui_manager.py

import tkinter as tk
from tkinter import messagebox, ttk
from src.database_manager import DatabaseManager

DB_FILE = "trades.db"


class TradeManagerApp:
    def __init__(self, root):
        self.db_manager = DatabaseManager(DB_FILE)
        self.root = root
        self.root.title("Trade Manager - Openstaande Posities")
        self.root.geometry("950x450")

        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))
        # NIEUW: Stijl voor de statusmelding
        style.configure("Status.TLabel", foreground="red", font=("Helvetica", 12))

        # Stijl voor afwisselende rij kleuren en kolom separators
        style.configure("Treeview", rowheight=25)
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

        # Voeg borders toe aan de cellen voor kolom separators
        style.configure("Treeview",
                        background="white",
                        fieldbackground="white",
                        borderwidth=1,
                        relief="solid")

        self.tree_colors = {
            'even': '#FFFFFF',  # Wit voor even rijen
            'odd': '#5f5f5f'  # Licht grijs voor oneven rijen
        }

        # --- Top Frame voor Labels ---
        top_frame = ttk.Frame(root, padding=(10, 10, 10, 0))
        top_frame.pack(fill=tk.X)

        title_label = ttk.Label(top_frame, text="Openstaande trades:", font=("Helvetica", 12))
        title_label.pack(side=tk.LEFT)

        # NIEUW: Een apart label voor de statusmelding
        self.status_label = ttk.Label(top_frame, text="", style="Status.TLabel")
        self.status_label.pack(side=tk.LEFT, padx=150)

        # --- Frame voor de Tabel ---
        table_frame = ttk.Frame(root, padding=(10, 0, 10, 10))
        table_frame.pack(fill=tk.BOTH, expand=True)

        # GEWIJZIGD: 'id' is een datakolom, maar wordt niet getoond.
        # De 'columns' tuple bevat alle data die we willen opslaan in een rij.
        self.columns = ('id', 'pair', 'direction', 'trader', 'entry_price', 'open_time')
        # De 'displaycolumns' tuple bepaalt welke kolommen ZICHTBAAR zijn.
        display_columns = ('pair', 'direction', 'trader', 'entry_price', 'open_time')

        self.tree = ttk.Treeview(table_frame, columns=self.columns, displaycolumns=display_columns, show='headings',
                                 style="Treeview")

        # Definieer de headers voor de ZICHTBARE kolommen
        self.tree.heading('pair', text='Crypto Pair')
        self.tree.heading('direction', text='Richting')
        self.tree.heading('trader', text='Trader')
        self.tree.heading('entry_price', text='Entry Prijs')
        self.tree.heading('open_time', text='Geopend Op')

        # Definieer de kolombreedtes voor de ZICHTBARE kolommen
        self.tree.column('pair', width=120, anchor=tk.W)
        self.tree.column('direction', width=80, anchor=tk.W)
        self.tree.column('trader', width=120, anchor=tk.W)
        self.tree.column('entry_price', width=100, anchor=tk.E)
        self.tree.column('open_time', width=250, anchor=tk.W)

        # Configureer tags voor afwisselende rij kleuren
        self.tree.tag_configure('evenrow', background='#FFFFFF')
        self.tree.tag_configure('oddrow', background='#F0F0F0')

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=scrollbar.set)

        # --- Frame voor de Knoppen ---
        button_frame = ttk.Frame(root, padding="10")
        button_frame.pack(fill=tk.X)

        close_button = ttk.Button(button_frame, text="Sluit Geselecteerde Trade", command=self.close_selected_trade)
        close_button.pack(side=tk.LEFT, padx=5)

        refresh_button = ttk.Button(button_frame, text="Vernieuwen", command=self.populate_trades_list)
        refresh_button.pack(side=tk.LEFT, padx=5)

        self.populate_trades_list()

    def populate_trades_list(self):
        """Haalt open trades op uit de DB en vult de Treeview-tabel."""
        # Maak eerst de tabel leeg en wis de statusmelding
        self.status_label.config(text="")
        for item in self.tree.get_children():
            self.tree.delete(item)

        open_trades = self.db_manager.get_open_trades_details()

        if not open_trades:
            # NIEUW: Toon de melding in het statuslabel boven de tabel
            self.status_label.config(text="Geen openstaande trades gevonden.")
            return

        for index, trade in enumerate(open_trades):
            # Voeg een visuele separator toe aan elke cel met een pipe symbool
            values_tuple = (
                trade['id'],
                f" {trade['crypto_pair']}",
                f" {trade['direction']}",
                f" {trade['trader']}",
                f" ${trade['entry_price']:.4f}",
                f" {trade['open_time']}"
            )
            # Wissel tussen even en oneven rij tags
            tag = 'evenrow' if index % 2 == 0 else 'oddrow'
            self.tree.insert('', 'end', values=values_tuple, tags=(tag,))

    def close_selected_trade(self):
        """Sluit de trade die op dit moment in de tabel is geselecteerd."""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Geen selectie", "Selecteer eerst een trade uit de tabel.")
            return

        item_data = self.tree.item(selected_item)
        values = item_data['values']

        if not values:
            messagebox.showerror("Fout", "Kon de geselecteerde trade niet lezen.")
            return

        # De ID is nog steeds de eerste waarde in de 'values' tuple, ook al is hij verborgen.
        trade_id = values[0]
        trade_pair = values[1]
        trade_trader = values[3]

        confirm = messagebox.askyesno("Bevestiging", f"Weet je zeker dat je de trade {trade_pair} van {trade_trader} wilt sluiten?")

        if confirm:
            success = self.db_manager.close_trade_manually(trade_id)
            if success:
                self.populate_trades_list()
            else:
                messagebox.showerror("Databasefout", f"Kon trade {trade_id} niet sluiten.")


def main():
    root = tk.Tk()
    app = TradeManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()