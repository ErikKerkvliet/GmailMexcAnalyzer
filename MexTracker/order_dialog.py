from datetime import datetime
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFormLayout, QFrame, QWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# Matplotlib imports voor de grafiek
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates

from api_manager import ApiManager


class ChartWorker(QThread):
    """Haalt chart data op in background zodat popup direct opent."""
    data_loaded = pyqtSignal(list, list)  # times, prices

    def __init__(self, base_coin, start_time):
        super().__init__()
        self.base_coin = base_coin
        self.start_time = start_time
        self.api = ApiManager()

    def run(self):
        times, prices = self.api.fetch_kraken_history(self.base_coin, self.start_time)
        self.data_loaded.emit(times, prices)


class MplCanvas(FigureCanvasQTAgg):
    """Een Canvas widget voor Matplotlib grafieken."""

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        # Donkere achtergrond instellen voor de plot
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor('#1e1e1e')

        self.axes = self.fig.add_subplot(111)
        self.axes.set_facecolor('#1e1e1e')

        # As kleuren wit maken
        self.axes.tick_params(axis='x', colors='#aaaaaa')
        self.axes.tick_params(axis='y', colors='#aaaaaa')
        self.axes.spines['bottom'].set_color('#333333')
        self.axes.spines['top'].set_color('#333333')
        self.axes.spines['left'].set_color('#333333')
        self.axes.spines['right'].set_color('#333333')

        super().__init__(self.fig)


class OrderDetailsDialog(QDialog):
    def __init__(self, order_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Order Details - {order_data.get('id', 'Unknown')}")
        self.resize(800, 400)

        self.order_data = order_data

        # Styling
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #333333;
            }
            QLabel {
                font-size: 13px;
                color: #ffffff;
            }
        """)

        # Hoofd Layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(25, 25, 25, 25)

        # --- HEADER ---
        title = QLabel(f"Details voor {order_data.get('baseCoinName', '?')}")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #034f9d; margin-bottom: 5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #333333;")
        main_layout.addWidget(line)

        # --- CONTENT ---
        content_layout = QHBoxLayout()

        # 1. Linker kolom: Tekst Info
        info_widget = QWidget()
        form_layout = QFormLayout(info_widget)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setHorizontalSpacing(15)
        form_layout.setVerticalSpacing(12)

        self.populate_form(form_layout, order_data)
        content_layout.addWidget(info_widget, stretch=1)

        # 2. Rechter kolom: Grafiek
        self.chart_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        content_layout.addWidget(self.chart_canvas, stretch=2)

        main_layout.addLayout(content_layout)

        # --- FOOTER ---
        close_btn = QPushButton("Sluiten")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #034f9d; color: white; padding: 10px; 
                border-radius: 4px; font-weight: bold; border: none; font-size: 13px;
            }
            QPushButton:hover { background-color: #0460bd; }
        """)
        main_layout.addWidget(close_btn)

        self.setLayout(main_layout)

        # Start laden data
        self.load_chart_data()

    def populate_form(self, layout, data):
        """Vult de linker tekst kolom."""

        def add_row(label, value, color=None):
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #aaaaaa; font-weight: bold;")
            val = QLabel(str(value))
            if color:
                val.setStyleSheet(f"color: {color}; font-weight: bold;")
            else:
                val.setStyleSheet("color: #ffffff;")
            layout.addRow(lbl, val)

        add_row("Order ID:", data.get('id'))
        add_row("Symbol:", f"{data.get('baseCoinName')} / {data.get('quoteCoinName')}")

        p_type = data.get('positionType')
        type_str = "Long" if p_type == 1 else "Short"
        type_col = "#00E676" if p_type == 1 else "#FF5252"
        add_row("Type:", type_str, type_col)

        add_row("Leverage:", f"{data.get('leverage')}x")
        add_row("Entry Price:", data.get('openAvgPrice'))
        add_row("Amount:", data.get('amount'))

        ts = data.get('openTime', 0)
        try:
            time_str = datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d\n%H:%M:%S')
        except:
            time_str = "N/A"
        add_row("Open Time:", time_str)

    def load_chart_data(self):
        """Start background thread om API te callen."""
        self.chart_canvas.axes.text(0.5, 0.5, 'Loading Chart...',
                                    horizontalalignment='center',
                                    verticalalignment='center',
                                    color='white', transform=self.chart_canvas.axes.transAxes)
        self.chart_canvas.draw()

        base = self.order_data.get('baseCoinName')
        start = self.order_data.get('openTime', 0)

        self.worker = ChartWorker(base, start)
        self.worker.data_loaded.connect(self.update_chart)
        self.worker.start()

    def update_chart(self, times, prices):
        """Wordt aangeroepen als data binnen is."""
        ax = self.chart_canvas.axes
        ax.clear()

        if not times or not prices:
            ax.text(0.5, 0.5, 'No Data Available',
                    horizontalalignment='center', color='#ff5555',
                    transform=ax.transAxes)
            self.chart_canvas.draw()
            return

        # Kleur bepalen (stijging/daling)
        line_color = '#00E676'  # Groen
        if prices[-1] < prices[0]:
            line_color = '#FF5252'  # Rood

        # 1. Plot de lijn
        ax.plot(times, prices, color=line_color, linewidth=2, label='Price')

        # Entry Price ophalen
        entry_price = float(self.order_data.get('openAvgPrice', 0))
        entry_ts_ms = self.order_data.get('openTime', 0)

        if entry_price > 0:
            # 2. Teken de Entry Price Lijn (gestippeld wit)
            ax.axhline(y=entry_price, color='#ffffff', linestyle='--', alpha=0.5, linewidth=1)

            # 3. Teken de Entry DOT (.)
            if entry_ts_ms > 0:
                entry_date = datetime.fromtimestamp(entry_ts_ms / 1000)
                ax.scatter([entry_date], [entry_price], color='#ffffff', s=50, zorder=5, label='Entry')

        # X-as opmaak
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        ax.tick_params(axis='y', labelsize=8)

        # Grid
        ax.grid(True, color='#333333', linestyle='--', alpha=0.5)

        # NIEUW: Deze functie berekent automatisch de marges zodat labels niet wegvallen
        self.chart_canvas.fig.tight_layout()

        self.chart_canvas.draw()