from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtCore import Qt

# Importeer de dialoog
from order_dialog import OrderDetailsDialog


class TraderTab(QWidget):
    def __init__(self, uid):
        super().__init__()
        self.uid = uid
        self.order_row_map = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        # We hebben nu 11 kolommen (Details is weg, Order ID is nu de knop)
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Order ID", "Amount", "Base Coin", "Quote Coin", "Side", "Leverage",
            "Open Time", "Entry Price", "Cur. Price", "PnL (USDT / %)", "Market PnL"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Compacte kolommen instellen
        # 0=Order ID(Knop), 2=Base, 3=Quote, 4=Side, 5=Lev, 6=Time, 9=PnL, 10=Mkt PnL
        compact_columns = [0, 2, 3, 4, 5, 6, 9, 10]
        for col in compact_columns:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def show_details(self, order_data):
        """Opent de popup dialoog."""
        dialog = OrderDetailsDialog(order_data, self)
        dialog.exec()

    def add_orders(self, orders, current_prices):
        for order in orders:
            order_id = str(order.get('id', 'N/A'))

            # --- DATA LOGICA ---
            try:
                amount = float(order.get('amount', 0))
                entry_price = float(order.get('openAvgPrice', 0))
                leverage_val = int(order.get('leverage', 1))
            except (ValueError, TypeError):
                amount, entry_price, leverage_val = 0.0, 0.0, 1

            base_coin = order.get('baseCoinName', 'N/A')
            quote_coin = order.get('quoteCoinName', 'N/A')
            raw_side = order.get('positionType', 0)

            ts_ms = order.get('openTime', 0)
            try:
                open_time = datetime.fromtimestamp(ts_ms / 1000).strftime('%H:%M:%S')
            except:
                open_time = "-"

            side_str = "N/A"
            side_color = QColor("#ffffff")
            if raw_side == 1:
                side_str = "Long"
                side_color = QColor("#00E676")
            elif raw_side == 2:
                side_str = "Short"
                side_color = QColor("#FF5252")

            # --- PNL BEREKENING ---
            kraken_price_raw = current_prices.get(base_coin, "N/A")
            pnl_text = "Waiting..."
            mkt_pnl_text = "Waiting..."
            pnl_color = QColor("#aaaaaa")
            kraken_price_display = str(kraken_price_raw)

            if isinstance(kraken_price_raw, (int, float)) and entry_price > 0:
                current_price = float(kraken_price_raw)
                diff = 0.0
                if raw_side == 1:
                    diff = current_price - entry_price
                elif raw_side == 2:
                    diff = entry_price - current_price

                pnl_usdt = diff * amount
                pnl_percent = (diff / entry_price) * leverage_val * 100
                mkt_percent = (diff / entry_price) * 100

                prefix = "+" if pnl_usdt >= 0 else ""
                pnl_text = f"{prefix}{pnl_usdt:.2f}$ ({prefix}{pnl_percent:.2f}%)"
                mkt_pnl_text = f"{prefix}{pnl_usdt:.2f}$ ({prefix}{mkt_percent:.2f}%)"

                if pnl_usdt > 0:
                    pnl_color = QColor("#00E676")
                elif pnl_usdt < 0:
                    pnl_color = QColor("#FF5252")
                else:
                    pnl_color = QColor("#ffffff")

            # --- TABEL UPDATE ---

            # 1. Rij bepalen
            if order_id in self.order_row_map:
                row_idx = self.order_row_map[order_id]
            else:
                row_idx = self.table.rowCount()
                self.table.insertRow(row_idx)
                self.order_row_map[order_id] = row_idx

                # --- KNOP MAKEN (In Kolom 0) ---
                # De tekst is nu het Order ID zelf
                btn = QPushButton(order_id)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setProperty("class", "table-btn")  # Houdt de blauwe styling uit styles.py

                # Callback
                btn.clicked.connect(lambda checked=False, o=order: self.show_details(o))

                self.table.setCellWidget(row_idx, 0, btn)

            # 2. Cellen vullen / updaten (Alles is 1 plek naar links verschoven tov vorige versie)
            def update_item(col, value, color=None):
                item = self.table.item(row_idx, col)
                if not item:
                    item = QTableWidgetItem()
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row_idx, col, item)
                item.setText(str(value))
                if color:
                    item.setForeground(QBrush(color))
                else:
                    item.setForeground(QBrush(QColor("#ffffff")))

            # Kolom 0 is de knop, dus we beginnen bij 1
            update_item(1, amount)
            update_item(2, base_coin)
            update_item(3, quote_coin)
            update_item(4, side_str, side_color)
            update_item(5, f"{leverage_val}x")
            update_item(6, open_time)
            update_item(7, entry_price)
            update_item(8, kraken_price_display)
            update_item(9, pnl_text, pnl_color)
            update_item(10, mkt_pnl_text, pnl_color)