# styles.py

STYLESHEET = """
QMainWindow {
    background-color: #121212;
}
QTabWidget::pane {
    background-color: #1e1e1e;
}

QTabBar::tab {
    background: #2c2c2c;
    color: #aaaaaa;
    padding: 8px 20px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #034f9d;
    color: white;
    font-weight: bold;
}
QTableWidget {
    background-color: #1e1e1e;
    color: #ffffff;
    gridline-color: #333333;
    border: none;
}
QHeaderView::section {
    background-color: #2c2c2c;
    color: #ffffff;
    padding: 5px;
    border: 1px solid #333333;
    font-weight: bold;
}
QTableCornerButton::section {
    background-color: #2c2c2c;
}
QTableWidget {
    background-color: #1e1e1e;           
    alternate-background-color: #2c2c2c; 
    color: #ffffff;
    gridline-color: #333333;
    border: none;
}

QPushButton.table-btn {
    background-color: #2d343b;
    color: white;
    border: 1px solid #394755;
    padding: 4px;
    border-radius: 5px;
    font-weight: bold;
    font-size: 11px;
}
QPushButton.table-btn:hover {
    background-color: #0460bd;
}
"""