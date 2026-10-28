import json
import os

from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *

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

BASE_DIR = os.path.expanduser("~") + "/.config/Ciel/C-Media_Player"
IMAGES_DIR = BASE_DIR + "/images"

CONTROL_IMPRESORA = "Control.Impresion.dll"
CONTROL_LECTOR = "Control.Captura.CodigoBarras.Omnidireccional"


class PerifericosTabFrame(QWidget):
    def __init__(self):
        super().__init__()

        # Valores por defecto (por si el control no existe en la configuracion)
        self.printers = ["UniversalPrinter"]
        self.readers = ["UniversalLector"]
        self.path = ""
        self.printer_index = 0
        self.reader_index = 0
        self.has_printer = False
        self.has_reader = False

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
        self.mainLayout.setContentsMargins(24, 16, 24, 16)
        self.mainLayout.setSpacing(12)
        self.setLayout(self.mainLayout)

        # ------------------------------------------------------------------
        # Seccion Impresora
        # ------------------------------------------------------------------
        self.seccion_impresora = self._crear_seccion_impresora()
        self.seccion_impresora.setEnabled(self.has_printer)
        self.mainLayout.addWidget(self.seccion_impresora)
        self.mainLayout.addWidget(self._crear_separador())

        # ------------------------------------------------------------------
        # Seccion Lector
        # ------------------------------------------------------------------
        self.seccion_lector = self._crear_seccion_lector()
        self.seccion_lector.setEnabled(self.has_reader)
        self.mainLayout.addWidget(self.seccion_lector)

        # Todo el espacio sobrante queda entre el contenido y el boton
        self.mainLayout.addStretch(1)

        # ------------------------------------------------------------------
        # Guardar centrado
        # ------------------------------------------------------------------
        self.save_button = self._crear_boton("Guardar")
        self.save_button.clicked.connect(self.save_settings)
        self.save_button.setMinimumWidth(260)
        self.save_button.setEnabled(self.has_printer or self.has_reader)

        fila_guardar = QHBoxLayout()
        fila_guardar.addStretch(1)
        fila_guardar.addWidget(self.save_button)
        fila_guardar.addStretch(1)
        self.mainLayout.addLayout(fila_guardar)

    # -----------------------------------------------------------------
    # Secciones
    # -----------------------------------------------------------------
    # Las dos secciones usan la misma cuadricula para que todo quede alineado:
    #   col 0: caja de icono (36px) | col 1: etiqueta | col 2: campo | col 3: boton
    ALTO_CAMPO = 38
    ANCHO_ETIQUETA = 70

    def _crear_seccion(self, titulo_texto):
        contenedor = QWidget()
        contenedor.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        grid = QGridLayout(contenedor)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.setColumnMinimumWidth(0, 36)
        grid.setColumnMinimumWidth(1, self.ANCHO_ETIQUETA)
        grid.setColumnStretch(2, 1)

        titulo = QLabel(titulo_texto)
        titulo.setObjectName("tituloSeccion")
        grid.addWidget(titulo, 0, 0, 1, 4)

        return contenedor, grid

    def _crear_etiqueta(self, texto):
        label = QLabel(texto)
        label.setFixedWidth(self.ANCHO_ETIQUETA)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return label

    def _crear_seccion_impresora(self):
        contenedor, grid = self._crear_seccion("Impresora")

        # Fila: modelo de impresora
        grid.addWidget(
            self._crear_caja_icono(IMAGES_DIR + "/print_24dp_F99F04_FILL0_wght400_GRAD-25_opsz24.svg"),
            1, 0, Qt.AlignVCenter
        )
        grid.addWidget(self._crear_etiqueta("Modelo"), 1, 1)

        self.combo_box_printer = QComboBox()
        self.combo_box_printer.addItems(self.printers)
        self.combo_box_printer.setCurrentIndex(self.printer_index)
        self.combo_box_printer.setFixedHeight(self.ALTO_CAMPO)
        grid.addWidget(self.combo_box_printer, 1, 2, 1, 2)  # ocupa campo + boton

        # Fila: ruta del logo
        grid.addWidget(self._crear_etiqueta("Logo"), 2, 1)

        self.path_entry = QLineEdit(self.path)
        self.path_entry.setFixedHeight(self.ALTO_CAMPO)
        self.path_entry.setReadOnly(True)
        self.path_entry.setPlaceholderText("Ningún archivo seleccionado (.bmp)")
        grid.addWidget(self.path_entry, 2, 2)

        self.file_name_button = self._crear_boton("Cargar")
        self.file_name_button.setFixedHeight(self.ALTO_CAMPO)
        self.file_name_button.setIcon(
            QIcon(IMAGES_DIR + "/folder_open_24dp_FFFFFF_FILL0_wght400_GRAD-25_opsz24.svg")
        )
        self.file_name_button.setIconSize(QSize(16, 16))
        self.file_name_button.clicked.connect(self.select_file)
        grid.addWidget(self.file_name_button, 2, 3)

        return contenedor

    def _crear_seccion_lector(self):
        contenedor, grid = self._crear_seccion("Lector de códigos")

        grid.addWidget(
            self._crear_caja_icono(IMAGES_DIR + "/scan_24dp_F99F04_FILL0_wght400_GRAD-25_opsz24.svg"),
            1, 0, Qt.AlignVCenter
        )
        grid.addWidget(self._crear_etiqueta("Modelo"), 1, 1)

        self.combo_box_reader = QComboBox()
        self.combo_box_reader.addItems(self.readers)
        self.combo_box_reader.setCurrentIndex(self.reader_index)
        self.combo_box_reader.setFixedHeight(self.ALTO_CAMPO)
        grid.addWidget(self.combo_box_reader, 1, 2, 1, 2)

        return contenedor

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
            QPushButton:disabled {{
                background-color: {COLOR_BORDE};
                color: {COLOR_TEXTO_SUAVE};
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
            caja.setPixmap(pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        return caja

    # -----------------------------------------------------------------
    # Logica de configuracion
    # -----------------------------------------------------------------
    def _ruta_configuracion(self):
        """Resuelve la ruta del archivo de pantallas a partir de config.json."""
        with open(BASE_DIR + "/configs/config.json", "r") as file:
            ruta = json.load(file)["Ruta"]
        if ruta.startswith("$"):
            sep = ruta.find("/")
            return os.environ[ruta[1:sep]] + ruta[sep:]
        return ruta

    def get_settings(self):
        with open(self._ruta_configuracion(), "r", encoding="utf-8-sig") as file:
            settings = json.load(file)

        for pantalla in settings["Pantallas"]:
            for controller in pantalla["Controles"]:
                nombre = controller["NombreArchivo"]

                if CONTROL_IMPRESORA in nombre:
                    self.has_printer = True
                    self.path = controller["ObjetoBase"]["RutaLogo"]["Path"]
                    self.printer_index = controller["ObjetoBase"]["TipoImpresora"]

                elif CONTROL_LECTOR in nombre:
                    self.has_reader = True
                    name = nombre[len(CONTROL_LECTOR) + 1:]
                    name = name[:name.find(".")]
                    if name == "Honeywell":
                        self.reader_index = self.readers.index("UniversalLector")

    def save_settings(self):
        path = self._ruta_configuracion()
        with open(path, "r", encoding="utf-8-sig") as file:
            settings = json.load(file)

        reader = self.combo_box_reader.currentText()
        if reader == "UniversalLector":
            reader = "Honeywell"

        for pantalla in settings["Pantallas"]:
            for controller in pantalla["Controles"]:
                nombre = controller["NombreArchivo"]

                if CONTROL_IMPRESORA in nombre:
                    controller["ObjetoBase"]["RutaLogo"]["Path"] = self.path_entry.text()
                    controller["ObjetoBase"]["TipoImpresora"] = self.combo_box_printer.currentIndex()

                elif CONTROL_LECTOR in nombre:
                    controller["NombreArchivo"] = CONTROL_LECTOR + "." + reader + ".dll"

        with open(path, "w", encoding="utf-8-sig") as file:
            file.write(json.dumps(settings))

    def select_file(self):
        file_name = QFileDialog.getOpenFileName(
            self, "Seleccionar Archivo", filter="Imagen BMP (*.bmp)"
        )[0]
        if file_name:
            self.file_name = file_name
            self.path_entry.setText(file_name)