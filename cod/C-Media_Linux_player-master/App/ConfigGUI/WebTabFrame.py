from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *

# Otras librerías
import json
import os
import copy
import logging


# ---------------------------------------------------------------------------
# Paleta de colores
# ---------------------------------------------------------------------------
COLOR_NARANJA = "#f99f04"
COLOR_NARANJA_HOVER = "#ff8c00"
COLOR_NARANJA_PRESSED = "#f99f04"
COLOR_ROJO = "#d9534f"
COLOR_ROJO_HOVER = "#c9302c"
COLOR_FONDO = "#FFFFFF"
COLOR_INPUT_BG = "#F2F4F6"
COLOR_BORDE = "#E4E6E9"
COLOR_TEXTO = "#313336"
COLOR_TEXTO_SUAVE = "#5B6066"
COLOR_BACKGROUND = "#F2F4F6"
COLOR_SCROLLBAR_BG = "#D0D0D3"
COLOR_ADVERTENCIA = "#C0392B"

# Nombre del archivo del control web dentro del JSON de pantallas
CONTROL_WEB = "Control.NavegadorWebChrome.dll"

# Llaves que se agregan a cada pantalla para recordar su monitor
LLAVE_MONITOR = "MonitorAsignado"        # indice (0 = automatico)
LLAVE_MONITOR_NOMBRE = "MonitorNombre"   # nombre real: HDMI-1, VGA-1, DP-2...


class WebTabFrame(QWidget):
    """
    Clase de vista de configuracion del Contenedor Web.
    Permite administrar varias URLs: cada URL corresponde a una pantalla
    con un control de navegador web, y puede asignarse a un monitor.
    """

    def __init__(self):
        super().__init__()
        self.setEnabled(False)
        self.pantallas_web = []   # [{"url","monitor","monitor_nombre"}, ...]
        self.nav_bar = False
        self.filas_url = []       # [{"widget","check","entry","combo","indice"}, ...]
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
            QComboBox {{
                min-width: 175px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 22px;
            }}
            QComboBox QAbstractItemView {{
                background-color: white;
                border: 1px solid {COLOR_BORDE};
                selection-background-color: {COLOR_NARANJA};
                selection-color: white;
                outline: none;
            }}
            QLineEdit:read-only {{
                color: {COLOR_TEXTO_SUAVE};
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
            QLabel#ayuda {{
                color: {COLOR_TEXTO_SUAVE};
            }}
            QLabel#monitores {{
                color: {COLOR_TEXTO_SUAVE};
                font-weight: 600;
            }}
            QLabel#advertencia {{
                color: {COLOR_ADVERTENCIA};
                font-weight: 600;
            }}
            QLabel#indiceUrl {{
                color: {COLOR_TEXTO_SUAVE};
                font-weight: 600;
                min-width: 22px;
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

        # Layout principal
        self.rootLayout = QVBoxLayout(self)
        self.rootLayout.setContentsMargins(0, 0, 0, 0)
        self.rootLayout.setSpacing(0)

        # Scroll
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {COLOR_BORDE};
                width: 12px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLOR_SCROLLBAR_BG};
                min-height: 20px;
                border-radius: 6px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        self.rootLayout.addWidget(self.scroll)

        # Contenedor del scroll
        self.scrollWidget = QWidget()
        self.mainLayout = QVBoxLayout(self.scrollWidget)
        self.mainLayout.setContentsMargins(20, 18, 20, 18)
        self.mainLayout.setSpacing(14)
        self.scroll.setWidget(self.scrollWidget)

        # ------------------------------------------------------------------
        # Fila 1: URLs
        # ------------------------------------------------------------------
        titulo_url = QLabel("Url")
        titulo_url.setObjectName("tituloSeccion")
        self.mainLayout.addWidget(titulo_url)

        ayuda_url = QLabel(
            "La primera URL deberá ser del selector que maneja la impresora y el lector."

        )
        ayuda_url.setObjectName("ayuda")
        ayuda_url.setWordWrap(True)
        self.mainLayout.addWidget(ayuda_url)

        # Monitores detectados
        self.label_monitores = QLabel()
        self.label_monitores.setObjectName("monitores")
        self.label_monitores.setWordWrap(True)

        self.refrescar_button = self._crear_boton("Detectar pantallas")
        self.refrescar_button.clicked.connect(self.refrescar_monitores)
        self.refrescar_button.setMinimumWidth(160)

        fila_monitores = QHBoxLayout()
        fila_monitores.setSpacing(10)
        fila_monitores.addWidget(self.label_monitores, 1)
        fila_monitores.addWidget(self.refrescar_button, 0, Qt.AlignTop)
        self.mainLayout.addLayout(fila_monitores)

        # Advertencia de monitores en espejo
        self.label_advertencia = QLabel()
        self.label_advertencia.setObjectName("advertencia")
        self.label_advertencia.setWordWrap(True)
        self.label_advertencia.hide()
        self.mainLayout.addWidget(self.label_advertencia)

        # Contenedor donde se apilan las filas de URL
        self.urls_container = QWidget()
        self.urls_layout = QVBoxLayout(self.urls_container)
        self.urls_layout.setContentsMargins(0, 0, 0, 0)
        self.urls_layout.setSpacing(8)
        self.mainLayout.addWidget(self.urls_container)

        # Botones + Url / Eliminar
        self.addUrl_button = self._crear_boton("+ Url")
        self.addUrl_button.clicked.connect(self.add_url)
        self.addUrl_button.setMinimumWidth(110)

        self.deleteUrl_button = self._crear_boton("Eliminar", COLOR_ROJO, COLOR_ROJO_HOVER)
        self.deleteUrl_button.clicked.connect(self.delete_urls)
        self.deleteUrl_button.setMinimumWidth(110)

        fila_botones_url = QHBoxLayout()
        fila_botones_url.setSpacing(10)
        fila_botones_url.addStretch(1)
        fila_botones_url.addWidget(self.addUrl_button)
        fila_botones_url.addWidget(self.deleteUrl_button)
        self.mainLayout.addLayout(fila_botones_url)

        # Se crean las filas con las URLs existentes
        if self.pantallas_web:
            for datos in self.pantallas_web:
                self._agregar_fila_url(datos["url"],
                                       datos.get("monitor", 0),
                                       datos.get("monitor_nombre", ""))
        else:
            self._agregar_fila_url("", 0, "")

        self._actualizar_label_monitores()

        # Se reacomodan los combos si se conecta o desconecta un monitor
        app = QGuiApplication.instance()
        if app is not None:
            app.screenAdded.connect(lambda s: self.refrescar_monitores())
            app.screenRemoved.connect(lambda s: self.refrescar_monitores())

        # ------------------------------------------------------------------
        # Fila 2: Barra de navegacion
        # ------------------------------------------------------------------
        fila_navbar = QHBoxLayout()
        fila_navbar.setSpacing(28)

        self.nav_bar_button = QCheckBox()
        self.nav_bar_button.setChecked(self.nav_bar)
        fila_navbar.addLayout(self._crear_fila_opcion(
            os.path.expanduser("~") + "/.config/Ciel/C-Media_Player/images/language_24dp_F99F04_FILL0_wght400_GRAD0_opsz24.svg",
            "Barra de Navegación", self.nav_bar_button))
        fila_navbar.addStretch(1)

        self.mainLayout.addLayout(fila_navbar)
        self.mainLayout.addStretch(1)

        

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
    def _crear_boton(self, texto, color=COLOR_NARANJA, color_hover=COLOR_NARANJA_HOVER):
        """
        Crea un boton con el estilo de la aplicacion
        """
        boton = QPushButton(texto)
        boton.setCursor(Qt.PointingHandCursor)
        boton.setMinimumHeight(40)
        boton.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                padding: 8px 18px;
                border-radius: 6px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {color_hover};
            }}
            QPushButton:pressed {{
                background-color: {color};
            }}
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

    def _crear_caja_icono(self, icono):
        """
        Caja cuadrada con icono en naranja suave
        """
        caja = QLabel()
        caja.setObjectName("cajaIcono")
        caja.setFixedSize(36, 36)
        caja.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap(icono)
        if not pixmap.isNull():
            caja.setPixmap(pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        return caja

    def _crear_fila_opcion(self, icono, texto, checkbox):
        """
        Fila: caja de icono + etiqueta + checkbox
        """
        layout = QHBoxLayout()
        layout.setSpacing(10)
        layout.addWidget(self._crear_caja_icono(icono))
        layout.addWidget(QLabel(texto))
        layout.addSpacing(6)
        layout.addWidget(checkbox)
        return layout

    # -----------------------------------------------------------------
    # Monitores
    # -----------------------------------------------------------------
    def _monitores(self):
        """
        Lista de monitores detectados por el sistema
        :return: list[QScreen]
        """
        app = QGuiApplication.instance()
        return list(app.screens()) if app is not None else []

    def _nombre_monitor(self, indice, monitor):
        """
        Etiqueta legible de un monitor
        :param indice: int. Posicion en la lista (base 0)
        :param monitor: QScreen
        :return: str
        """
        geo = monitor.geometry()
        nombre = monitor.name() or "Monitor"
        return f"{indice + 1} · {nombre} ({geo.width()}x{geo.height()})"

    def _llenar_combo(self, combo, seleccion=0, nombre=""):
        """
        Llena un combo con los monitores detectados.
        El dato de cada opcion es {"indice": int, "nombre": str}
        :param combo: QComboBox
        :param seleccion: int. Indice guardado (0 = automatico)
        :param nombre: str. Nombre del monitor guardado
        """
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Automático", {"indice": 0, "nombre": ""})

        monitores = self._monitores()
        for indice, monitor in enumerate(monitores):
            combo.addItem(self._nombre_monitor(indice, monitor),
                          {"indice": indice + 1, "nombre": monitor.name()})

        posicion = -1

        # Seleccion por nombre: es lo estable entre reinicios
        if nombre:
            for i in range(combo.count()):
                if combo.itemData(i).get("nombre") == nombre:
                    posicion = i
                    break
            if posicion < 0:
                # El monitor guardado no esta conectado: se conserva la opcion
                combo.addItem(f"{nombre} (no conectado)",
                              {"indice": seleccion, "nombre": nombre})
                posicion = combo.count() - 1

        # Compatibilidad con configuraciones que solo guardaron el indice
        if posicion < 0 and seleccion:
            for i in range(combo.count()):
                if combo.itemData(i).get("indice") == seleccion:
                    posicion = i
                    break
            if posicion < 0:
                combo.addItem(f"{seleccion} · (no conectado)",
                              {"indice": seleccion, "nombre": ""})
                posicion = combo.count() - 1

        combo.setCurrentIndex(posicion if posicion >= 0 else 0)
        combo.blockSignals(False)

    def refrescar_monitores(self):
        """
        Vuelve a leer los monitores conectados y actualiza los combos,
        conservando la seleccion de cada fila
        """
        for fila in self.filas_url:
            datos = fila["combo"].currentData() or {"indice": 0, "nombre": ""}
            self._llenar_combo(fila["combo"], datos.get("indice", 0),
                               datos.get("nombre", ""))
        self._actualizar_label_monitores()

    def _detectar_espejo(self):
        """
        Detecta monitores que comparten la misma geometria (modo espejo)
        :return: list[list[str]]. Grupos de monitores clonados
        """
        geometrias = {}
        for monitor in self._monitores():
            geo = monitor.geometry()
            clave = (geo.x(), geo.y(), geo.width(), geo.height())
            geometrias.setdefault(clave, []).append(monitor.name())
        return [nombres for nombres in geometrias.values() if len(nombres) > 1]

    def _actualizar_label_monitores(self):
        """
        Muestra cuantos monitores se detectaron, cuales son,
        y advierte si estan en modo espejo
        """
        monitores = self._monitores()
        if not monitores:
            self.label_monitores.setText("No se detectaron monitores.")
            self.label_advertencia.hide()
            return

        detalle = "   |   ".join(self._nombre_monitor(i, m) for i, m in enumerate(monitores))
        cantidad = len(monitores)
        plural = "pantalla detectada" if cantidad == 1 else "pantallas detectadas"
        self.label_monitores.setText(f"{cantidad} {plural}:   {detalle}")

        espejo = self._detectar_espejo()
        if espejo:
            grupos = "; ".join(" = ".join(g) for g in espejo)
            self.label_advertencia.setText(
                f"Atención: {grupos} están en modo espejo (muestran la misma imagen). "
                "Las ventanas quedarán encimadas en una sola pantalla. "
                "Configure el modo extendido en el sistema para poder repartirlas.")
            self.label_advertencia.show()
        else:
            self.label_advertencia.hide()

    # -----------------------------------------------------------------
    # Manejo de las filas de URL
    # -----------------------------------------------------------------
    def _agregar_fila_url(self, url="", monitor=0, monitor_nombre=""):
        """
        Crea una fila: check de seleccion + indice + URL + monitor asignado
        :param url: str. Valor inicial del campo
        :param monitor: int. Indice guardado (0 = automatico)
        :param monitor_nombre: str. Nombre del monitor guardado
        """
        fila = QWidget()
        layout = QHBoxLayout(fila)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        check = QCheckBox()
        check.setToolTip("Seleccionar para eliminar")

        indice = QLabel()
        indice.setObjectName("indiceUrl")

        entry = QLineEdit(url)
        entry.setMinimumHeight(38)
        entry.setPlaceholderText("https://ejemplo.com")

        combo = QComboBox()
        combo.setMinimumHeight(38)
        combo.setCursor(Qt.PointingHandCursor)
        combo.setToolTip("Monitor donde se abrirá esta URL")
        self._llenar_combo(combo, monitor, monitor_nombre)

        layout.addWidget(check)
        layout.addWidget(indice)
        layout.addWidget(entry, 1)
        layout.addWidget(combo)

        self.urls_layout.addWidget(fila)
        self.filas_url.append({"widget": fila, "check": check, "entry": entry,
                               "combo": combo, "indice": indice})
        self._renumerar_filas()
        return fila

    def _renumerar_filas(self):
        """
        Actualiza el numero de ventana mostrado en cada fila
        """
        for numero, fila in enumerate(self.filas_url, start=1):
            fila["indice"].setText(str(numero))

    def add_url(self):
        """
        Agrega un nuevo campo de URL vacio al final de la lista
        """
        fila = self._agregar_fila_url("", 0, "")
        fila.findChild(QLineEdit).setFocus()

    def delete_urls(self):
        """
        Elimina todas las filas marcadas con el check
        """
        seleccionadas = [f for f in self.filas_url if f["check"].isChecked()]

        if not seleccionadas:
            QMessageBox.information(self, "Eliminar URL",
                                    "Marque al menos una URL para eliminarla.")
            return

        if len(seleccionadas) == len(self.filas_url):
            QMessageBox.warning(self, "Eliminar URL",
                                "Debe quedar al menos una URL configurada.")
            return

        respuesta = QMessageBox.question(
            self, "Eliminar URL",
            f"¿Eliminar {len(seleccionadas)} URL(s) seleccionada(s)?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if respuesta != QMessageBox.Yes:
            return

        for fila in seleccionadas:
            self.urls_layout.removeWidget(fila["widget"])
            fila["widget"].setParent(None)
            fila["widget"].deleteLater()
            self.filas_url.remove(fila)

        self._renumerar_filas()

    def _obtener_datos(self):
        """
        Devuelve las URLs con su monitor asignado.
        Si hay campos vacios devuelve None y avisa, para no perder filas en silencio.
        :return: list[dict] | None
        """
        datos = []
        vacias = 0
        for fila in self.filas_url:
            texto = fila["entry"].text().strip()
            if texto:
                seleccion = fila["combo"].currentData() or {"indice": 0, "nombre": ""}
                datos.append({"url": self._normalizar_url(texto),
                              "monitor": seleccion.get("indice", 0),
                              "monitor_nombre": seleccion.get("nombre", "")})
            else:
                vacias += 1

        if vacias:
            QMessageBox.warning(
                self, "Guardar",
                f"Hay {vacias} campo(s) de URL vacío(s).\n\n"
                "Escriba una dirección en cada campo o márquelo y use Eliminar. "
                "Los campos vacíos no se pueden guardar porque cada pantalla "
                "necesita una URL de inicio.")
            return None

        return datos

    def _normalizar_url(self, url):
        """
        Agrega el esquema http:// si la URL no lo trae
        """
        if "://" not in url and not url.startswith("file:"):
            return "http://" + url
        return url

    # -----------------------------------------------------------------
    # Lectura / escritura del archivo de pantallas
    # -----------------------------------------------------------------
    def _ruta_pantallas(self):
        """
        Resuelve la ruta del archivo json de pantallas a partir de config.json
        :return: str. Ruta absoluta
        """
        path = os.path.expanduser('~') + "/.config/Ciel/C-Media_Player/configs/config.json"
        with open(path, "r") as file:
            settings = json.loads(file.read())

        ruta = settings["Ruta"]
        if ruta.startswith("$"):
            var = os.environ[ruta[1:ruta.find("/")]]
            ruta = var + ruta[ruta.find("/"):]
        return ruta

    def _localizar_controles_web(self, settings):
        """
        Busca todos los controles de navegador web del archivo de pantallas
        :param settings: dic. Contenido del archivo de pantallas
        :return: list[tuple]. [(indice_pantalla, indice_control), ...]
        """
        ubicaciones = []
        for i, pantalla in enumerate(settings.get("Pantallas", [])):
            for j, control in enumerate(pantalla.get("Controles", [])):
                if CONTROL_WEB in control.get("NombreArchivo", ""):
                    ubicaciones.append((i, j))
        return ubicaciones

    def get_settings(self):
        """
        Obtiene la configuracion del archivo json y la guarda en atributos de la clase
        """
        try:
            ruta = self._ruta_pantallas()
            with open(ruta, "r", encoding="utf-8-sig") as file:
                settings = json.load(file)
        except Exception as e:
            logging.error("WebTab - lectura inicial: " + str(e))
            return

        for pantalla in settings.get("Pantallas", []):
            for controller in pantalla.get("Controles", []):
                if CONTROL_WEB in controller.get("NombreArchivo", ""):
                    self.setEnabled(True)
                    base = controller.get("ObjetoBase", {})
                    self.pantallas_web.append({
                        "url": base.get("UrlInicio", ""),
                        "monitor": pantalla.get(LLAVE_MONITOR, 0),
                        "monitor_nombre": pantalla.get(LLAVE_MONITOR_NOMBRE, "")
                    })
                    self.nav_bar = base.get("MostrarBarraNavegacion", False)

    def save_settings(self):
        """
        Guarda las URLs y su monitor en el archivo de pantallas.
        - Actualiza los controles web existentes.
        - Crea una pantalla nueva (clonando la primera pantalla web) por cada URL extra.
        - Elimina los controles/pantallas sobrantes.
        - Verifica el resultado releyendo el archivo.
        """
        datos = self._obtener_datos()
        if datos is None:
            return
        if not datos:
            QMessageBox.warning(self, "Guardar", "Debe ingresar al menos una URL válida.")
            return

        try:
            ruta = self._ruta_pantallas()
            with open(ruta, "r", encoding="utf-8-sig") as file:
                settings = json.load(file)
        except Exception as e:
            logging.error("WebTab - lectura: " + str(e))
            QMessageBox.critical(self, "Guardar",
                                 "No se pudo leer el archivo de pantallas.\n" + str(e))
            return

        ubicaciones = self._localizar_controles_web(settings)
        if not ubicaciones:
            QMessageBox.warning(self, "Guardar",
                                "El archivo de pantallas no contiene un control de navegador web.")
            return

        nav = self.nav_bar_button.isChecked()

        # Plantillas para clonar pantallas nuevas
        i0, j0 = ubicaciones[0]
        plantilla_pantalla = copy.deepcopy(settings["Pantallas"][i0])
        plantilla_control = copy.deepcopy(settings["Pantallas"][i0]["Controles"][j0])

        # 1. Actualizar los controles existentes que siguen teniendo URL
        for k, (i, j) in enumerate(ubicaciones[:len(datos)]):
            base = settings["Pantallas"][i]["Controles"][j].setdefault("ObjetoBase", {})
            base["UrlInicio"] = datos[k]["url"]
            base["MostrarBarraNavegacion"] = nav
            settings["Pantallas"][i][LLAVE_MONITOR] = datos[k]["monitor"]
            settings["Pantallas"][i][LLAVE_MONITOR_NOMBRE] = datos[k]["monitor_nombre"]

        # 2. Eliminar los sobrantes (de atras hacia adelante para no correr indices)
        for i, j in reversed(ubicaciones[len(datos):]):
            del settings["Pantallas"][i]["Controles"][j]
            if not settings["Pantallas"][i]["Controles"] and len(settings["Pantallas"]) > 1:
                del settings["Pantallas"][i]

        # 3. Crear pantallas nuevas para las URLs adicionales
        for extra in datos[len(ubicaciones):]:
            nueva_pantalla = copy.deepcopy(plantilla_pantalla)
            nuevo_control = copy.deepcopy(plantilla_control)
            nuevo_control.setdefault("ObjetoBase", {})
            nuevo_control["ObjetoBase"]["UrlInicio"] = extra["url"]
            nuevo_control["ObjetoBase"]["MostrarBarraNavegacion"] = nav
            nueva_pantalla["Controles"] = [nuevo_control]
            nueva_pantalla[LLAVE_MONITOR] = extra["monitor"]
            nueva_pantalla[LLAVE_MONITOR_NOMBRE] = extra["monitor_nombre"]
            settings["Pantallas"].append(nueva_pantalla)

        # 4. Renumerar pantallas: el Player espera ScreenNumber empezando en 1
        titulo_base = plantilla_pantalla.get("TitleName", "C-Media Player")
        for numero, pantalla in enumerate(settings["Pantallas"], start=1):
            pantalla["ScreenNumber"] = numero
            if numero > 1 and not pantalla.get("TitleName"):
                pantalla["TitleName"] = f"{titulo_base} ({numero})"

        # 5. Escritura atomica: se escribe un temporal y se reemplaza
        try:
            temporal = ruta + ".tmp"
            with open(temporal, "w", encoding="utf-8-sig") as file:
                json.dump(settings, file, ensure_ascii=False)
            os.replace(temporal, ruta)
        except Exception as e:
            logging.error("WebTab - escritura: " + str(e))
            QMessageBox.critical(self, "Guardar",
                                 "No se pudo guardar el archivo de pantallas.\n" + str(e))
            return

        # 6. Avisos sobre los monitores asignados
        conectados = [m.name() for m in self._monitores()]
        faltantes = sorted({d["monitor_nombre"] for d in datos
                            if d["monitor_nombre"] and d["monitor_nombre"] not in conectados})

        mensaje = f"Configuración guardada. {len(datos)} ventana(s) web."

        if faltantes:
            mensaje += ("\n\nAtención: " + ", ".join(faltantes)
                        + " no está conectado en este momento. Esas ventanas se "
                          "abrirán en el monitor principal hasta que se conecte.")

        if self._detectar_espejo():
            mensaje += ("\n\nAtención: hay monitores en modo espejo. Las ventanas "
                        "quedarán encimadas hasta que se configure el modo extendido.")

        logging.info(f"WebTab - guardado en {ruta} | ventanas: {len(datos)} | "
                     f"monitores conectados: {conectados}")

        QMessageBox.information(self, "Guardar", mensaje)



   
