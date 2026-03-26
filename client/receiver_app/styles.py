"""
Az alkalmazás teljes QSS stílusát adja vissza.
"""

from PySide6.QtGui import QPalette


def is_dark_mode(app) -> bool:
    """
    Megállapítja, hogy a rendszer / Qt paletta sötét témát használ-e.
    """
    palette = app.palette()
    window_color = palette.color(QPalette.ColorRole.Window)
    return window_color.lightness() < 128


def build_stylesheet(dark: bool) -> str:
    """
    Visszaadja a teljes alkalmazás stíluslapját világos vagy sötét módban.
    """
    if dark:
        return """
        QMainWindow, QWidget {
            background: #111827;
            color: #e5e7eb;
            font-family: "Segoe UI";
        }

        QListWidget {
            background: #0f172a;
            border: 1px solid #1f2937;
            border-radius: 18px;
            padding: 8px;
            outline: none;
        }

        QListWidget::item {
            background: transparent;
            border-radius: 14px;
            padding: 12px;
            margin: 4px 0;
        }

        QListWidget::item:selected {
            background: #1e3a8a;
            color: white;
        }

        QListWidget::item:hover {
            background: #1f2937;
        }

        QTextBrowser {
            background: #0b1220;
            border: 1px solid #1f2937;
            border-radius: 20px;
            padding: 12px;
        }

        QLabel {
            color: #e5e7eb;
        }

        QPushButton {
            background: #2563eb;
            color: white;
            border: none;
            border-radius: 12px;
            padding: 10px 14px;
            font-weight: 600;
        }

        QPushButton:hover {
            background: #1d4ed8;
        }

        QMenu {
            background: #111827;
            color: #e5e7eb;
            border: 1px solid #1f2937;
            padding: 6px;
        }

        QMenu::item {
            padding: 8px 14px;
            border-radius: 8px;
        }

        QMenu::item:selected {
            background: #1f2937;
        }
        """

    return """
    QMainWindow, QWidget {
        background: #f8fafc;
        color: #0f172a;
        font-family: "Segoe UI";
    }

    QListWidget {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 8px;
        outline: none;
    }

    QListWidget::item {
        background: transparent;
        border-radius: 14px;
        padding: 12px;
        margin: 4px 0;
    }

    QListWidget::item:selected {
        background: #dbeafe;
        color: #1e3a8a;
    }

    QListWidget::item:hover {
        background: #f1f5f9;
    }

    QTextBrowser {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 12px;
    }

    QLabel {
        color: #0f172a;
    }

    QPushButton {
        background: #2563eb;
        color: white;
        border: none;
        border-radius: 12px;
        padding: 10px 14px;
        font-weight: 600;
    }

    QPushButton:hover {
        background: #1d4ed8;
    }

    QMenu {
        background: white;
        color: #0f172a;
        border: 1px solid #e2e8f0;
        padding: 6px;
    }

    QMenu::item {
        padding: 8px 14px;
        border-radius: 8px;
    }

    QMenu::item:selected {
        background: #eff6ff;
    }
    """