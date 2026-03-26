class BrandedPopup(QFrame):
    clicked = Signal()

    def __init__(self, app_name: str, sender: str, text: str, icon: QIcon | None, dark: bool, important: bool):
        super().__init__(None)
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self.dark = dark
        self.important = important

        bg = "#2b2d31" if dark else "#ffffff"
        fg = "#e8eaed" if dark else "#111827"
        muted = "#9ca3af" if dark else "#6b7280"
        close_bg = "#7f1d1d" if important and dark else "#fee2e2" if important else "#374151" if dark else "#e5e7eb"
        close_fg = "#fecaca" if important and dark else "#b91c1c" if important else "#e8eaed" if dark else "#111827"

        self.setStyleSheet(f"""
            QFrame {{
                background: {bg};
            }}
            QLabel {{
                color: {fg};
                background: transparent;
            }}
            QTextBrowser {{
                background: transparent;
                color: {fg};
                border: none;
                font-size: 13px;
            }}
            QPushButton#popupCloseBtn {{
                background: {close_bg};
                color: {close_fg};
                border: none;
                border-radius: 10px;
                padding: 4px 10px;
                font-weight: bold;
            }}
        """)

        self.setMinimumWidth(360)
        self.setMaximumWidth(420)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(10)

        icon_label = QLabel()
        icon_label.setFixedSize(40, 40)
        if icon and not icon.isNull():
            icon_label.setPixmap(icon.pixmap(40, 40))
        else:
            pm = QPixmap(40, 40)
            pm.fill(Qt.transparent)
            painter = QPainter(pm)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor("#2563eb"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(4, 4, 32, 32)
            painter.end()
            icon_label.setPixmap(pm)

        title_wrap = QVBoxLayout()
        title_wrap.setSpacing(2)

        title = QLabel(app_name)
        title.setStyleSheet("font-size: 14px; font-weight: bold;")

        subtitle = QLabel(("FONTOS - " if important else "Új üzenet - ") + sender)
        subtitle.setStyleSheet(f"font-size: 12px; color: {muted};")

        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("popupCloseBtn")
        self.close_btn.setFixedSize(34, 28)
        self.close_btn.clicked.connect(self.close)

        header.addWidget(icon_label)
        header.addLayout(title_wrap, 1)
        header.addWidget(self.close_btn)

        self.body = QTextBrowser()
        self.body.setOpenExternalLinks(False)
        self.body.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.body.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body.setPlainText(text)

        root.addLayout(header)
        root.addWidget(self.body)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close)

        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(220)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

    def compute_size_and_position(self):
        screen = QApplication.primaryScreen()
        if not screen:
            self.resize(400, 160)
            return

        geo = screen.availableGeometry()
        max_width = min(420, max(320, geo.width() - 40))
        max_height = min(260, max(140, geo.height() - 40))

        self.setMaximumWidth(max_width)
        self.resize(max_width, 180)

        # próbáljuk a tartalomhoz igazítani, de ne lógjon ki
        doc_height = int(self.body.document().size().height()) + 16
        desired_height = 90 + min(doc_height, max_height - 90)
        final_height = max(140, min(desired_height, max_height))
        self.resize(max_width, final_height)

        x = geo.x() + geo.width() - self.width() - 20
        y = geo.y() + geo.height() - self.height() - 20
        self.move(x, y)

    def show_popup(self, duration_ms: int | None = None):
        self.compute_size_and_position()

        if duration_ms is None:
            text_len = len(self.body.toPlainText())
            if self.important:
                duration_ms = 15000
            elif text_len > 250:
                duration_ms = 12000
            elif text_len > 120:
                duration_ms = 9000
            else:
                duration_ms = 7000

        self.setWindowOpacity(0.0)
        self.show()
        self.anim.start()
        self.timer.start(duration_ms)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            self.close()
            event.accept()
            return
        super().mousePressEvent(event)