from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy
)
import os


COLOR_TEXTO = "#15181a"

class TitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.window = parent
        self._drag_pos = None

        self.setFixedHeight(36)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setObjectName("TitleBar")
        
        self.setStyleSheet(f"""
            QWidget#TitleBar {{
                background: white;
                border-bottom: 1.2px solid #e4e6e9;
            }}

            QWidget#TitleBar QLabel {{
                background: white;
                font-weight: 500;
                color: {COLOR_TEXTO};
                font-size: 14px;
                border-bottom: 1.2px solid #e4e6e9;
            }}

            QWidget#TitleBar QPushButton {{
                border: none;
                background: transparent;
                font-size: 16px;
                min-width: 42px;
            }}

            QWidget#TitleBar QPushButton:hover {{
                background: #efefef;
            }}

        
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)
 
        

        # Logo
        self.logo = QLabel()
        path = os.path.expanduser('~')+"/.config/Ciel/C-Media_Player/Media/LOGO-CMedia.png"
        self.logo.setPixmap(QIcon(path).pixmap(20, 20))
        layout.addWidget(self.logo)

        # Nombre de la aplicación
        self.title = QLabel("C-Media Player · Configuración")
        layout.addWidget(self.title)

        layout.addStretch()

        # Minimizar
        self.btn_min = QPushButton("—")
        self.btn_min.clicked.connect(self.window.showMinimized)
        layout.addWidget(self.btn_min)



        # Cerrar
        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("close")
        self.btn_close.clicked.connect(self.window.close)
        layout.addWidget(self.btn_close)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()
            event.accept()

    def toggle_maximize(self):
        if self.window.isMaximized():
            self.window.showNormal()
        else:
            self.window.showMaximized()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            self.window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()  