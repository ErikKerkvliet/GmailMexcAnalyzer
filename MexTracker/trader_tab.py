from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtCore import Qt
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
        # 12 kolommen
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            "Order ID", "Amount", "Base Coin", "Quote Coin", "Side", "Leverage",
            "Open Time", "Entry (MEXC)", "Entry (Kraken)", "Kraken Current", "PnL (USDT / %)", "Market PnL"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Compact maken van specifieke kolommen
        # 0=ID, 2=Base, 3=Quote, 4=Side, 5=Lev, 6=Time, 10=PnL, 11=Mkt
        compact_columns = [0, 2, 3, 4, 5, 6, 10, 11]
        for col in compact_columns:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def show_details(self, order_data):
        dialog = OrderDetailsDialog(order_data, self)
        dialog.exec()

    def add_orders(self, orders, current_prices, historical_prices):
        """
        Update tabel met:
        - orders: lijst met dicts
        - current_prices: dict {coin: price} (Kraken Live)
        - historical_prices: dict {order_id: price} (Kraken Entry)
        """
        for order in orders:
            order_id = str(order.get('id', 'N/A'))

            # --- DATA LOGICA ---
            try:
                amount = float(order.get('amount', 0))
                mexc_entry = float(order.get('openAvgPrice', 0))
                leverage_val = int(order.get('leverage', 1))
            except (ValueError, TypeError):
                amount, mexc_entry, leverage_val = 0.0, 0.0, 1

            base_coin = order.get('baseCoinName', 'N/A')
            quote_coin = order.get('quoteCoinName', 'N/A')
            raw_side = order.get('positionType', 0)

            ts_ms = order.get('openTime', 0)
            try:
                open_time = datetime.fromtimestamp(ts_ms / 1000).strftime('%Y-%m-%d %H:%M')
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

            # --- PRIJZEN ---
            # current_prices komt uit de worker thread en bevat Kraken Live Prijzen
            cur_price_raw = current_prices.get(base_coin, "N/A")
            kraken_entry_raw = historical_prices.get(order_id, "Loading...")

            cur_price_disp = str(cur_price_raw)
            kraken_entry_disp = str(kraken_entry_raw)

            # --- PNL BEREKENING ---
            pnl_text = "Waiting..."
            mkt_pnl_text = "Waiting..."
            pnl_color = QColor("#aaaaaa")

            # PnL berekening: We vergelijken de MEXC Entry met de Huidige Kraken Prijs
            if isinstance(cur_price_raw, (int, float)) and mexc_entry > 0:
                current_price = float(cur_price_raw)
                diff = 0.0
                if raw_side == 1:
                    diff = current_price - mexc_entry
                elif raw_side == 2:
                    diff = mexc_entry - current_price

                pnl_usdt = diff * amount
                pnl_percent = (diff / mexc_entry) * leverage_val * 100
                mkt_percent = (diff / mexc_entry) * 100

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

            if order_id in self.order_row_map:
                row_idx = self.order_row_map[order_id]
            else:
                row_idx = self.table.rowCount()
                self.table.insertRow(row_idx)
                self.order_row_map[order_id] = row_idx

                # KNOP
                btn = QPushButton(order_id)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setProperty("class", "table-btn")
                btn.clicked.connect(lambda checked=False, o=order: self.show_details(o))
                self.table.setCellWidget(row_idx, 0, btn)

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

            # Kolom Indexen:
            # 0: Knop (Order ID)
            # 1: Amount
            # 2: Base
            # 3: Quote
            # 4: Side
            # 5: Leverage
            # 6: Open Time
            # 7: Entry (MEXC)
            # 8: Entry (Kraken)
            # 9: Kraken Current (Voorheen Cur. Price)
            # 10: PnL
            # 11: Mkt PnL

            update_item(1, amount)
            update_item(2, base_coin)
            update_item(3, quote_coin)
            update_item(4, side_str, side_color)
            update_item(5, f"{leverage_val}x")
            update_item(6, open_time)
            update_item(7, mexc_entry)
            update_item(8, kraken_entry_disp)
            update_item(9, cur_price_disp)
            update_item(10, pnl_text, pnl_color)
            update_item(11, mkt_pnl_text, pnl_color)