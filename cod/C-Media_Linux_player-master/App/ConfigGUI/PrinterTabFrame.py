import json
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *

import os

# ---------------------------------------------------------------------------
# Paleta de colores
# ---------------------------------------------------------------------------
COLOR_NARANJA = "#f99f04"
COLOR_NARANJA_HOVER = "#ff8c00"
COLOR_NARANJA_PRESSED = "#f99f04"
COLOR_FONDO = "#FFFFFF"
COLOR_INPUT_BG = "#F2F4F6"
COLOR_BORDE = "#E4E6E9"
COLOR_TEXTO = "#313336"
COLOR_TEXTO_SUAVE = "#5B6066"
COLOR_BACKGROUND = "#F2F4F6"


class PrinterTabFrame(QWidget):
    def __init__(self):
        super().__init__()
        self.setEnabled(False)
        self.path = ""
        self.get_settings()

        # Fondo blanco
        bg = QPalette()
        bg.setColor(QPalette.Window, COLOR_FONDO)
        self.setAutoFillBackground(True)
        self.setPalette(bg)

        self.setStyleSheet(f"""
            QWidget {{
                color: {COLOR_TEXTO};
                font-family: "Segoe UI", "Noto Sans", sans-serif;
                font-size: 13px;
            }}
            QLineEdit, QSpinBox, QComboBox {{
                background-color: {COLOR_INPUT_BG};
                border: 1px solid {COLOR_BORDE};
                border-radius: 8px;
                padding: 8px 10px;
            }}
         
            QComboBox::drop-down {{
                border: none;
                width: 28px;
            }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: white;
                border: 1px solid {COLOR_BORDE};
                border-radius: 6px;
                selection-background-color: {COLOR_NARANJA};
                selection-color: white;
            }}
            QLineEdit:read-only {{
                color: {COLOR_TEXTO_SUAVE};
            }}
            QFrame#separador {{
                color: {COLOR_BORDE};
                max-height: 1px;
                min-height: 1px;
            }}
            QLabel#tituloSeccion {{
                font-weight: 600;
                font-size: 14px;
            }}
            QLabel#cajaIcono {{
                background-color: {COLOR_BACKGROUND};
                border: 1px solid {COLOR_BORDE};
                border-radius: 5px;
                color: {COLOR_NARANJA};
                font-size: 16px;
                font-weight: bold;
            }}
        """)

        # Layout principal vertical
        self.mainLayout = QVBoxLayout()
        self.mainLayout.setContentsMargins(20, 18, 20, 18)
        self.mainLayout.setSpacing(14)
        self.setLayout(self.mainLayout)

        # ------------------------------------------------------------------
        # Fila 1: Logo (ruta del archivo)
        # ------------------------------------------------------------------
        titulo_logo = QLabel("Logo")
        titulo_logo.setObjectName("tituloSeccion")
        self.mainLayout.addWidget(titulo_logo)

        fila_logo_path = QHBoxLayout()
        fila_logo_path.setSpacing(12)

        self.path_entry = QLineEdit(self.path)
        self.path_entry.setMinimumHeight(38)
        self.path_entry.setReadOnly(True)
        fila_logo_path.addWidget(self.path_entry, stretch=1)

        self.file_name_button = self._crear_boton("Cargar")

        self.file_name_button.setIcon(
            QIcon(os.path.expanduser("~") +
                "/.config/Ciel/C-Media_Player/images/folder_open_24dp_FFFFFF_FILL0_wght400_GRAD-25_opsz24.svg")
        )
        self.file_name_button.setIconSize(QSize(16, 16))

        self.file_name_button.clicked.connect(self.select_file)
        fila_logo_path.addWidget(self.file_name_button)

        self.mainLayout.addLayout(fila_logo_path)
        self.mainLayout.addWidget(self._crear_separador())

        # ------------------------------------------------------------------
        # Fila 2: Impresora (combobox)
        # ------------------------------------------------------------------
        fila_impresora = QHBoxLayout()
        fila_impresora.setSpacing(10)

        fila_impresora.addWidget(
            self._crear_caja_icono(
                os.path.expanduser("~") + "/.config/Ciel/C-Media_Player/images/print_24dp_F99F04_FILL0_wght400_GRAD-25_opsz24.svg"
            )
        )

        impresora_label = QLabel("Impresora")
        impresora_label.setMinimumWidth(80)
        fila_impresora.addWidget(impresora_label)

        self.printers = ["UniversalPrinter"]
        self.combo_box_printer = QComboBox()
        self.combo_box_printer.addItems(self.printers)
        self.combo_box_printer.setCurrentIndex(self.index)
        self.combo_box_printer.setMinimumHeight(38)
        fila_impresora.addWidget(self.combo_box_printer, stretch=1)

        self.mainLayout.addLayout(fila_impresora)
        self.mainLayout.addWidget(self._crear_separador())
        self.mainLayout.addStretch(1)
        # ------------------------------------------------------------------
        # Logo marca de agua a la derecha
        # ------------------------------------------------------------------
        
        img = QLabel()
        logo_path = os.path.expanduser('~') + "/.config/Ciel/C-Media_Player/Media/LOGO-CMedia.png"
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaledToWidth(110, Qt.SmoothTransformation)
        img.setPixmap(pixmap)
        opacidad = QGraphicsOpacityEffect(img)
        opacidad.setOpacity(0.18)
        img.setGraphicsEffect(opacidad)

        fila_marca = QHBoxLayout()
       
        fila_marca.addWidget(img, alignment=Qt.AlignRight | Qt.AlignBottom)
        self.mainLayout.addLayout(fila_marca)

        # ------------------------------------------------------------------
        # Guardar centrado
        # ------------------------------------------------------------------
        self.save_button = self._crear_boton("Guardar")
        self.save_button.clicked.connect(self.save_settings)
        self.save_button.setMinimumWidth(260)

        fila_guardar = QHBoxLayout()
        fila_guardar.addStretch(1)
        fila_guardar.addWidget(self.save_button)
        fila_guardar.addStretch(1)

       
        self.mainLayout.addStretch(1)
        self.mainLayout.addLayout(fila_guardar)
        self.mainLayout.addStretch(1)

    # -----------------------------------------------------------------
    # Helpers visuales
    # -----------------------------------------------------------------
    def _crear_boton(self, texto):
        boton = QPushButton(texto)
        boton.setCursor(Qt.PointingHandCursor)
        boton.setMinimumHeight(40)
        boton.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_NARANJA};
                color: white;
                padding: 8px 18px;
                border-radius: 6px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLOR_NARANJA_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_NARANJA_PRESSED};
            }}
        """)
        return boton

    def _crear_separador(self):
        linea = QFrame()
        linea.setObjectName("separador")
        linea.setFrameShape(QFrame.HLine)
        return linea

    def _crear_caja_icono(self, icono):
        caja = QLabel()
        caja.setObjectName("cajaIcono")
        caja.setFixedSize(36, 36)
        caja.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap(icono)
        if not pixmap.isNull():
            caja.setPixmap(
                pixmap.scaled(
                    20, 20,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )

        return caja

    # -----------------------------------------------------------------
    # Logica original (sin cambios)
    # -----------------------------------------------------------------
    def get_settings(self):
        path = os.path.expanduser('~') + "/.config/Ciel/C-Media_Player/configs/config.json"
        with open(path, "r") as file:
            settings = json.loads(file.read())
        if "$" == settings["Ruta"][0]:
            var = os.environ[settings["Ruta"][1:settings["Ruta"].find("/")]]
            path = var + settings["Ruta"][settings["Ruta"].find("/"):]
        else:
            path = settings["Ruta"]
        with open(path, "r", encoding="utf-8-sig") as file:
            settings = json.load(file)
            for pantalla in settings["Pantallas"]:
                for controller in pantalla["Controles"]:
                    if "Control.Impresion.dll" in controller["NombreArchivo"]:
                        self.setEnabled(True)
                        self.path = controller["ObjetoBase"]["RutaLogo"]["Path"]
                        self.index = controller["ObjetoBase"]["TipoImpresora"]

    def save_settings(self):
        path = os.path.expanduser('~') + "/.config/Ciel/C-Media_Player/configs/config.json"
        with open(path, "r") as file:
            settings = json.loads(file.read())

        if "$" == settings["Ruta"][0]:
            var = os.environ[settings["Ruta"][1:settings["Ruta"].find("/")]]
            path = var + settings["Ruta"][settings["Ruta"].find("/"):]
        else:
            path = settings["Ruta"]
        with open(path, "r", encoding="utf-8-sig") as file:
            settings = json.load(file)
            for pantalla in range(len(settings["Pantallas"])):
                for controller in range(len(settings["Pantallas"][pantalla]["Controles"])):
                    if "Control.Impresion.dll" in settings["Pantallas"][pantalla]["Controles"][controller]["NombreArchivo"]:
                        settings["Pantallas"][pantalla]["Controles"][controller]["ObjetoBase"]["RutaLogo"]["Path"] = self.path_entry.text()
                        settings["Pantallas"][pantalla]["Controles"][controller]["ObjetoBase"]["TipoImpresora"] = self.combo_box_printer.currentIndex()

        with open(path, "w", encoding="utf-8-sig") as file:
            file.write(json.dumps(settings))

    def select_file(self):
        file_name = QFileDialog().getOpenFileName(self, "Seleccionar Archivo", filter="Config files (*bmp)")[0]
        if file_name != "":
            self.file_name = file_name
            self.path_entry.clear()
            self.path_entry.insert(file_name) 
