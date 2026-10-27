from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *


#Clases Externasfila_
#from .ToggleButton import ToggleButton

#Otras librerias
import os
import json

# ---------------------------------------------------------------------------
# Paleta de colores (basada en el logo/estilo de la imagen de referencia)
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


class GeneralTabFrame(QWidget):
    """
    Clase de vista de configuracion General
    """
    def __init__(self):
        """
        Clase de vista de configuracion General
        """ 
        super().__init__()
        self.settings = {}
        self.get_settings()

        #Iniciacion de variables

        if "$" == self.settings["Ruta"][0]:
            var =  os.environ[self.settings["Ruta"][1:self.settings["Ruta"].find("/")]]
            file_name = var + self.settings["Ruta"][self.settings["Ruta"].find("/"):]
            self.file_name = file_name
        else:
            self.file_name = self.settings["Ruta"]
        self.fullscreen = self.settings["PantallaCompleta"]
        self.window_border = self.settings["MostrarBordeVentana"]
        self.on_top = self.settings["SiempreVisible"]
        self.w = self.settings["AnchoRequerido"]
        self.h = self.settings["AltoRequerido"]
        self.t = self.settings["TopRequerido"]
        self.l = self.settings["LeftRequerido"]

        #Seleccionar el fondo (blanco, como en la referencia)
        bg = QPalette()
        bg.setColor(QPalette.Window, COLOR_FONDO)
        self.setAutoFillBackground(True)
        self.setPalette(bg)

        #Estilos generales reutilizables para los widgets de este frame
        self.setStyleSheet(f"""
            QWidget {{
                color: {COLOR_TEXTO};
                font-family: "Segoe UI", "Noto Sans", sans-serif;
                font-size: 13px;
            }}
            QLineEdit, QSpinBox {{
                background-color: {COLOR_INPUT_BG};
                border: 1px solid {COLOR_BORDE};
                border-radius: 8px;
                padding: 8px 10px;
            }}
            QLineEdit:read-only {{
                color: {COLOR_TEXTO_SUAVE};
            }}
            QSpinBox {{
                max-width: 90px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 16px;
                border: none;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border: 2px solid {COLOR_BORDE};
                border-radius: 5px;
                background-color: white;
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLOR_NARANJA};
                border: 2px solid {COLOR_NARANJA};
                image: url({os.path.expanduser('~')}/.config/Ciel/C-Media_Player/images/check-solid-full.svg);
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

        #Configuracion del Layout principal
        self.mainLayout = QVBoxLayout()
        self.mainLayout.setContentsMargins(20, 18, 20, 18)
        self.mainLayout.setSpacing(14)
        self.setLayout(self.mainLayout)

        # ------------------------------------------------------------------
        # Fila 1: Archivo de recursos
        # ------------------------------------------------------------------
        titulo_archivo = QLabel("Archivo de recursos")
        titulo_archivo.setObjectName("tituloSeccion")
        self.mainLayout.addWidget(titulo_archivo)

        fila_archivo = QHBoxLayout()
        fila_archivo.setSpacing(12)

        self.file_name_entry = QLineEdit(self.file_name)
        self.file_name_entry.setReadOnly(True)
        self.file_name_entry.setMinimumHeight(38)
        fila_archivo.addWidget(self.file_name_entry, stretch=1)

        self.file_name_button = self._crear_boton("Cargar")

        self.file_name_button.setIcon(
            QIcon(os.path.expanduser("~") +
                "/.config/Ciel/C-Media_Player/images/folder_open_24dp_FFFFFF_FILL0_wght400_GRAD-25_opsz24.svg")
        )
        self.file_name_button.setIconSize(QSize(16, 16))


        self.file_name_button.clicked.connect(self.select_file)
        fila_archivo.addWidget(self.file_name_button)

        self.mainLayout.addLayout(fila_archivo)
        self.mainLayout.addWidget(self._crear_separador())

        # ------------------------------------------------------------------
        # Fila 2: Pantalla completa / Borde ventana / Siempre visible
        # ------------------------------------------------------------------
        fila_opciones = QHBoxLayout()
        fila_opciones.setSpacing(28)

        self.fullscreen_button = QCheckBox()
        self.fullscreen_button.setChecked(self.fullscreen)
        #self.fullscreen_button.toggled.connect(self.funcionfs) # CAMBIAR FUNCION
        fila_opciones.addLayout(self._crear_fila_opcion("⛶", "Pantalla completa", self.fullscreen_button))

        self.window_border_button = QCheckBox()
        self.window_border_button.setChecked(self.window_border)
        #self.window_border_button.toggled.connect(self.funcionwb) # CAMBIAR FUNCION
        fila_opciones.addLayout(self._crear_fila_opcion("▭", "Borde Ventana", self.window_border_button))

        self.on_top_button = QCheckBox()
        self.on_top_button.setChecked(self.on_top)
        #self.on_top_button.toggled.connect(self.funcionot) # CAMBIAR FUNCION
        fila_opciones.addLayout(self._crear_fila_opcion("👁", "Siempre Visible", self.on_top_button))

        fila_opciones.addStretch(1)
        self.mainLayout.addLayout(fila_opciones)
        self.mainLayout.addWidget(self._crear_separador())

        # ------------------------------------------------------------------
        # Fila 3: Ancho / Alto / Superior / Izquierda + logo
        # ------------------------------------------------------------------
        fila_dimensiones = QHBoxLayout()
        fila_dimensiones.setSpacing(28)

        columna_izq = QVBoxLayout()
        columna_izq.setSpacing(14)
        self.width_entry = self._crear_spinbox(self.w)
        columna_izq.addLayout(self._crear_fila_valor("↔", "Ancho pxls", self.width_entry))
        self.height_entry = self._crear_spinbox(self.h)
        columna_izq.addLayout(self._crear_fila_valor("↕", "Alto pxls", self.height_entry))

        columna_der = QVBoxLayout()
        columna_der.setSpacing(14)
        self.top_entry = self._crear_spinbox(self.t)
        columna_der.addLayout(self._crear_fila_valor("↑", "Superior", self.top_entry))
        self.left_entry = self._crear_spinbox(self.l)
        columna_der.addLayout(self._crear_fila_valor("←", "Izquierda", self.left_entry))

        self.mainLayout.addStretch(1)

        fila_dimensiones.addLayout(columna_izq)
        fila_dimensiones.addLayout(columna_der)
       

        #Imagen / logo (esquina inferior derecha, como en la referencia)
        img = QLabel()
        path = os.path.expanduser('~')+"/.config/Ciel/C-Media_Player/Media/LOGO-CMedia.png"
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            pixmap = pixmap.scaledToWidth(110, Qt.SmoothTransformation)
        img.setPixmap(pixmap)
        opacidad = QGraphicsOpacityEffect(img)
        opacidad.setOpacity(0.18)
        img.setGraphicsEffect(opacidad)
        fila_dimensiones.addWidget(img, alignment=Qt.AlignRight | Qt.AlignBottom)

        self.mainLayout.addLayout(fila_dimensiones)
     
        
        # ------------------------------------------------------------------
        # Fila 4: Guardar
        # ------------------------------------------------------------------
     
        self.save_button = self._crear_boton("Guardar")
        self.save_button.clicked.connect(self.save)
        self.mainLayout.addWidget(self.save_button)
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
        """
        Crea el boton
        """
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
          fila_  }}
        """)

        return boton

    def _crear_separador(self):
        """
        Linea horizontal divisoria entre secciones
        """
        linea = QFrame()
        linea.setObjectName("separador")
        linea.setFrameShape(QFrame.HLine)
        return linea
    
    def _crear_caja_icon(self, icono):
        """
        Caja cuadrada con icono (texto unicode) en naranja suave, como en la referencia
        """
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

    def _crear_caja_icono(self, caracter):
        """
        Caja cuadrada con icono (texto unicode) en naranja suave, como en la referencia
        """
        caja = QLabel(caracter)
        caja.setObjectName("cajaIcono")
        caja.setFixedSize(36, 36)
        caja.setAlignment(Qt.AlignCenter)
        return caja

    def _crear_fila_opcion(self, caracter, texto, checkbox):
        """
        Fila: caja de icono + etiqueta + checkbox, usada para las opciones booleanas
        """
        layout = QHBoxLayout()
        layout.setSpacing(10)
        layout.addWidget(self._crear_caja_icono(caracter))
        layout.addWidget(QLabel(texto))
        layout.addSpacing(6)
        layout.addWidget(checkbox)
        return layout

    def _crear_fila_valor(self, caracter, texto, spinbox):
        """
        Fila: caja de icono + etiqueta + spinbox, usada para los valores numericos
        """
        layout = QHBoxLayout()
        layout.setSpacing(10)
        layout.addWidget(self._crear_caja_icono(caracter))
        etiqueta = QLabel(texto)
        etiqueta.setMinimumWidth(70)
        layout.addWidget(etiqueta)
        layout.addWidget(spinbox)
        return layout

    def _crear_spinbox(self, valor_inicial):
        """
        QSpinBox con rango amplio para reemplazar los QLineEdit numericos
        (mantiene flechas arriba/abajo como en la referencia)
        """
        spin = QSpinBox()
        spin.setRange(-9999, 9999)
        spin.setValue(int(valor_inicial))
        spin.setMinimumHeight(34)
        return spin

    # -----------------------------------------------------------------
    # Logica original (sin cambios funcionales)
    # -----------------------------------------------------------------
    def select_file(self):
        """
        Abre un cuadro de dialogo para la seleccion del archivo de configuracion ccmj y lo guarda en la variable
        """
        file_name = QFileDialog().getOpenFileName(self, "Seleccionar Archivo", filter="Config files (*.ccmj)")[0]
        if file_name != "":
            self.file_name = file_name
            self.file_name_entry.clear()
            self.file_name_entry.insert(file_name)



    def save(self):
        """
        Guarda la informacion en el archivo json de configuracion
        """

        path = os.path.expanduser('~')+"/.config/Ciel/C-Media_Player/configs/config.json"

        with open(path, "w") as file:

            settings = {
                "Ruta" : self.file_name,
                "PantallaCompleta" : self.fullscreen_button.isChecked(),
                "SiempreVisible" : self.on_top_button.isChecked(),
                "MostrarBordeVentana" : self.window_border_button.isChecked(),
                "AnchoRequerido" : self.width_entry.value(),
                "AltoRequerido" : self.height_entry.value(),
                "TopRequerido" : self.top_entry.value(),
                "LeftRequerido" : self.left_entry.value()
            }

            file.write(json.dumps(settings))

    def get_settings(self):
        """
        Obtiene la configuracion del archivo json y las guarda en un atributo de la clase
        """

        path = os.path.expanduser('~')+"/.config/Ciel/C-Media_Player/configs/config.json"
        with open(path, "r") as file:
            self.settings = json.loads(file.read())