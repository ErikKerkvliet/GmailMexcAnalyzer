import sys
import os
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget
from styles import STYLESHEET
from worker_thread import WorkerThread
from trader_tab import TraderTab

# Fix voor Linux/Gnome
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.theme.gnome=false'

load_dotenv()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        print("[Main] Initializing Application...")

        self.setWindowTitle("MEXC Copy Trading Monitor")
        self.resize(1175, 650)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        user_ids_str = os.getenv("MEXC_USER_IDS", "")
        self.user_ids = [uid.strip() for uid in user_ids_str.split(',') if uid.strip()]

        if not self.user_ids:
            print("[Main ERROR] No user IDs found in .env file!")
        else:
            print(f"[Main] Loaded User IDs: {self.user_ids}")

        self.tab_widgets = {}

        for uid in self.user_ids:
            tab = TraderTab(uid)
            self.tab_widgets[uid] = tab
            self.tabs.addTab(tab, f"Loading {uid}...")

        # Start de background worker
        self.worker = WorkerThread(self.user_ids)
        self.worker.data_fetched.connect(self.update_gui)
        self.worker.start()

    def update_gui(self, uid, orders, prices):
        """Callback die wordt aangeroepen vanuit WorkerThread."""
        if uid not in self.tab_widgets:
            return

        tab = self.tab_widgets[uid]
        tab.add_orders(orders, prices)

        if orders:
            nickname = orders[0].get('traderNickName', str(uid))
            index = self.tabs.indexOf(tab)
            if index != -1:
                count = tab.table.rowCount()
                # Update de tab tekst alleen als het veranderd is (voorkomt flickering)
                new_title = f"({count}) {nickname}"
                if self.tabs.tabText(index) != new_title:
                    self.tabs.setTabText(index, new_title)

    def closeEvent(self, event):
        print("[Main] Closing application, stopping worker...")
        self.worker.stop()
        event.accept()
        print("[Main] Application closed.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()

    print("[Main] Event loop started.")
    sys.exit(app.exec())