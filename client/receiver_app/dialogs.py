"""
Dialógusablakok.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QTextBrowser, QVBoxLayout


class ImportantAlertDialog(QDialog):
    """
    Fontos üzenetekhez megjelenő kiemelt figyelmeztető ablak.
    """

    def __init__(self, sender: str, text: str, app_name: str):
        super().__init__()
        self.setWindowTitle(f"{app_name} - FONTOS")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.resize(580, 320)

        title = QLabel(f"Fontos üzenet érkezett: {sender}")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #ef4444;")

        body = QTextBrowser()
        body.setPlainText(text)

        ok_btn = QPushButton("Rendben")
        ok_btn.clicked.connect(self.accept)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(ok_btn, alignment=Qt.AlignRight)
        self.setLayout(layout)

    def show_centered(self):
        """
        A képernyő közepére helyezi és megnyitja az ablakot.
        """
        from PySide6.QtWidgets import QApplication

        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2,
            )
        self.exec()