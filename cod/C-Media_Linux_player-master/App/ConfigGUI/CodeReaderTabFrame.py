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


class CodeReaderTabFrame(QWidget):
    def __init__(self):
        super().__init__()
        self.setEnabled(False)
        self.readers = ["UniversalLector"]
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
        # Fila 1: Lector (combobox)
        # ------------------------------------------------------------------
        fila_lector = QHBoxLayout()
        fila_lector.setSpacing(10)

        fila_lector.addWidget(self._crear_caja_icono(os.path.expanduser("~") + "/.config/Ciel/C-Media_Player/images/scan_24dp_F99F04_FILL0_wght400_GRAD-25_opsz24.svg"))

        lector_label = QLabel("Lector")
        lector_label.setMinimumWidth(80)
        fila_lector.addWidget(lector_label)

        self.combo_box_reader = QComboBox()
        self.combo_box_reader.addItems(self.readers)
        self.combo_box_reader.setCurrentIndex(self.index)
        self.combo_box_reader.setMinimumHeight(38)
        fila_lector.addWidget(self.combo_box_reader, stretch=1)

        self.mainLayout.addLayout(fila_lector)
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
                    if "Control.Captura.CodigoBarras.Omnidireccional" in controller["NombreArchivo"]:
                        self.setEnabled(True)
                        name = controller["NombreArchivo"][45:]
                        name = name[:name.find(".")]
                        if name == "Honeywell":
                            self.index = self.readers.index("UniversalLector")

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
                    if "Control.Captura.CodigoBarras.Omnidireccional" in settings["Pantallas"][pantalla]["Controles"][controller]["NombreArchivo"]:
                        reader = self.combo_box_reader.currentText()

                        if reader == "UniversalLector":
                            reader = "Honeywell"

                        settings["Pantallas"][pantalla]["Controles"][controller]["NombreArchivo"] = (
                            "Control.Captura.CodigoBarras.Omnidireccional." + reader + ".dll"
                        )

        with open(path, "w", encoding="utf-8-sig") as file:
            file.write(json.dumps(settings))
