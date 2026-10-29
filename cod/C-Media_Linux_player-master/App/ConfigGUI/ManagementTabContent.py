"""
ManagementTabContent.py  (ConfigGUI)
====================================
Pestaña "Contenidos" de la configuracion. Solo es la parte grafica:
toda la logica (descarga, manifiesto, servidor local) vive en
AppFrames/ManagementContent.py.

Desde aqui se puede:
- Descargar del servidor el reproductor web y sus contenidos (en segundo plano).
- Ver la lista de contenidos, reordenarlos (arrastrando o con las flechas),
  activarlos/desactivarlos con la casilla y eliminarlos.
- Ver cada contenido y una "Vista en orden" que los recorre como el player.
- Elegir cuando usa el player la copia local (modo sin conexion).
"""

from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *

import logging
import os
import sys

try:
    from AppFrames.ManagementContent import (
        Manifiesto, Sincronizador, ruta_archivo, urls_inicio_configuradas,
        normalizar_url, origen_de, mismo_origen, formato_tamano, formato_fecha,
        MODO_AUTOMATICO, MODO_EN_LINEA, MODO_SIN_CONEXION, ARCHIVOS_DIR)
except ImportError:
    # Si ConfigGUI se ejecuta sin la raiz del proyecto en el path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from AppFrames.ManagementContent import (
        Manifiesto, Sincronizador, ruta_archivo, urls_inicio_configuradas,
        normalizar_url, origen_de, mismo_origen, formato_tamano, formato_fecha,
        MODO_AUTOMATICO, MODO_EN_LINEA, MODO_SIN_CONEXION, ARCHIVOS_DIR)

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
    HAY_VIDEO = True
except ImportError:
    HAY_VIDEO = False


# ---------------------------------------------------------------------------
# Paleta de colores
# ---------------------------------------------------------------------------
COLOR_NARANJA = "#f99f04"
COLOR_NARANJA_HOVER = "#ff8c00"
COLOR_ROJO = "#d9534f"
COLOR_ROJO_HOVER = "#c9302c"
COLOR_FONDO = "#FFFFFF"
COLOR_INPUT_BG = "#F2F4F6"
COLOR_BORDE = "#E4E6E9"
COLOR_TEXTO = "#313336"
COLOR_TEXTO_SUAVE = "#5B6066"
COLOR_BACKGROUND = "#F2F4F6"

IMAGES_DIR = os.path.expanduser("~") + "/.config/Ciel/C-Media_Player/images"

DURACION_IMAGEN = 5   # segundos que dura cada imagen en la "Vista en orden"

TIPOS = {"imagen": "Imagen", "video": "Video", "audio": "Audio", "documento": "Documento"}

ROL_CLAVE = Qt.UserRole
ROL_TEXTO = Qt.UserRole + 1


class ManagementTabContent(QWidget):
    """
    Vista de configuracion del manejo de contenidos offline.
    """

    def __init__(self):
        super().__init__()
        self.manifiesto = Manifiesto()
        self.hilo = None
        self.sincronizador = None
        self.reproduciendo = False
        self.cola_vista = []

        self.timer_vista = QTimer(self)
        self.timer_vista.setSingleShot(True)
        self.timer_vista.timeout.connect(self._avanzar_vista)

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
            QLineEdit, QComboBox {{
                background-color: {COLOR_INPUT_BG};
                border: 1px solid {COLOR_BORDE};
                border-radius: 8px;
                padding: 8px 10px;
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
            QListWidget {{
                background-color: white;
                border: 1px solid {COLOR_BORDE};
                border-radius: 8px;
                padding: 4px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 6px 4px;
                border-radius: 5px;
            }}
            QListWidget::item:selected {{
                background-color: #FEF1DA;
                color: {COLOR_TEXTO};
            }}
            QListWidget::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {COLOR_BORDE};
                border-radius: 4px;
                background-color: white;
            }}
            QListWidget::indicator:checked {{
                background-color: {COLOR_NARANJA};
                border: 2px solid {COLOR_NARANJA};
                image: url({os.path.expanduser('~')}/.config/Ciel/C-Media_Player/images/check-solid-full.svg);
            }}
            QProgressBar {{
                background-color: {COLOR_INPUT_BG};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_NARANJA};
                border-radius: 3px;
            }}
            QLabel#tituloSeccion {{
                font-weight: 600;
                font-size: 14px;
            }}
            QLabel#ayuda {{
                color: {COLOR_TEXTO_SUAVE};
                font-size: 12px;
            }}
            QLabel#cajaIcono {{
                background-color: {COLOR_BACKGROUND};
                border: 1px solid {COLOR_BORDE};
                border-radius: 5px;
                color: {COLOR_NARANJA};
                font-size: 16px;
                font-weight: bold;
            }}
            QStackedWidget#vistaPrevia, QLabel#vistaPreviaTexto {{
                background-color: {COLOR_INPUT_BG};
                border-radius: 8px;
                color: {COLOR_TEXTO_SUAVE};
            }}
        """)

        self._construir_ui()
        self._cargar_lista()

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._al_salir)

    # -----------------------------------------------------------------
    # Interfaz
    # -----------------------------------------------------------------
    def _construir_ui(self):
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(20, 14, 20, 14)
        self.mainLayout.setSpacing(8)

        # --- Fila servidor ---------------------------------------------
        fila_servidor = QHBoxLayout()
        fila_servidor.setSpacing(10)
        fila_servidor.addWidget(self._crear_caja_icono(
            IMAGES_DIR + "/cloud_download_24dp_F99F04_FILL0_wght400_GRAD0_opsz24.svg", "⇩"))
        fila_servidor.addWidget(QLabel("Servidor"))

        self.url_entry = QLineEdit()
        self.url_entry.setMinimumHeight(38)
        self.url_entry.setPlaceholderText("https://servidor:puerto/api/v1.0/webplayer/index")
        urls_previas = self.manifiesto.datos.get("urls_inicio") or urls_inicio_configuradas()
        self.url_entry.setText(urls_previas[0] if urls_previas else "")
        fila_servidor.addWidget(self.url_entry, 1)

        self.sync_button = self._crear_boton("Descargar contenidos")
        self.sync_button.setMinimumWidth(180)
        self.sync_button.clicked.connect(self._sincronizar_o_cancelar)
        fila_servidor.addWidget(self.sync_button)
        self.mainLayout.addLayout(fila_servidor)

        # --- Fila estado -----------------------------------------------
        fila_estado = QHBoxLayout()
        fila_estado.setSpacing(10)
        self.label_estado = QLabel()
        self.label_estado.setObjectName("ayuda")
        self.label_estado.setMinimumWidth(10)
        self.barra = QProgressBar()
        self.barra.setFixedSize(200, 6)
        self.barra.setTextVisible(False)
        self.barra.hide()
        fila_estado.addWidget(self.label_estado, 1)
        fila_estado.addWidget(self.barra, 0, Qt.AlignVCenter)
        self.mainLayout.addLayout(fila_estado)

        # --- Lista + vista previa --------------------------------------
        medio = QHBoxLayout()
        medio.setSpacing(14)

        izquierda = QVBoxLayout()
        izquierda.setSpacing(6)
        self.label_lista = QLabel("Contenidos")
        self.label_lista.setObjectName("tituloSeccion")
        izquierda.addWidget(self.label_lista)

        self.lista = QListWidget()
        self.lista.setDragDropMode(QAbstractItemView.InternalMove)
        self.lista.setDefaultDropAction(Qt.MoveAction)
        self.lista.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lista.setToolTip("Arrastre para cambiar el orden. "
                              "Desmarque la casilla para que el contenido no se muestre.")
        self.lista.model().rowsMoved.connect(lambda *args: self._renumerar())
        self.lista.currentItemChanged.connect(self._al_seleccionar)
        izquierda.addWidget(self.lista, 1)
        medio.addLayout(izquierda, 3)

        derecha = QVBoxLayout()
        derecha.setSpacing(6)
        titulo_vista = QLabel("Vista previa")
        titulo_vista.setObjectName("tituloSeccion")
        derecha.addWidget(titulo_vista)

        self.vista = QStackedWidget()
        self.vista.setObjectName("vistaPrevia")
        self.vista.setMinimumSize(250, 140)
        self.vista_label = QLabel()
        self.vista_label.setObjectName("vistaPreviaTexto")
        self.vista_label.setAlignment(Qt.AlignCenter)
        self.vista_label.setWordWrap(True)
        self.vista_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.vista.addWidget(self.vista_label)

        # El reproductor de video/audio se crea la primera vez que se necesita
        # (ver _asegurar_reproductor): asi la configuracion abre aunque el
        # sistema de audio no este disponible.
        self.reproductor = None
        if HAY_VIDEO:
            self.video = QVideoWidget()
            self.vista.addWidget(self.video)
        derecha.addWidget(self.vista, 1)

        self.label_info = QLabel()
        self.label_info.setObjectName("ayuda")
        self.label_info.setWordWrap(True)
        derecha.addWidget(self.label_info)

        self.vista_button = self._crear_boton("▶  Vista en orden")
        self.vista_button.setMinimumHeight(34)
        self.vista_button.clicked.connect(self._alternar_vista)
        derecha.addWidget(self.vista_button)
        medio.addLayout(derecha, 2)

        self.mainLayout.addLayout(medio, 1)

        # --- Fila inferior ---------------------------------------------
        abajo = QHBoxLayout()
        abajo.setSpacing(8)

        self.subir_button = self._crear_boton("↑")
        self.subir_button.setToolTip("Subir")
        self.subir_button.setFixedWidth(44)
        self.subir_button.clicked.connect(lambda: self._mover(-1))
        self.bajar_button = self._crear_boton("↓")
        self.bajar_button.setToolTip("Bajar")
        self.bajar_button.setFixedWidth(44)
        self.bajar_button.clicked.connect(lambda: self._mover(1))
        self.eliminar_button = self._crear_boton("Eliminar", COLOR_ROJO, COLOR_ROJO_HOVER)
        self.eliminar_button.clicked.connect(self._eliminar)

        abajo.addWidget(self.subir_button)
        abajo.addWidget(self.bajar_button)
        abajo.addWidget(self.eliminar_button)
        abajo.addStretch(1)

        abajo.addWidget(QLabel("Usar copia local"))
        self.modo_combo = QComboBox()
        self.modo_combo.setMinimumHeight(38)
        self.modo_combo.addItem("Si no hay conexión", MODO_AUTOMATICO)
        self.modo_combo.addItem("Siempre", MODO_SIN_CONEXION)
        self.modo_combo.addItem("Nunca", MODO_EN_LINEA)
        self.modo_combo.setToolTip(
            "Si no hay conexión: el player abre el servidor y, si no responde, la copia local.\n"
            "Siempre: el player abre siempre la copia local.\n"
            "Nunca: el player abre siempre el servidor.")
        abajo.addWidget(self.modo_combo)

        self.save_button = self._crear_boton("Guardar")
        self.save_button.setMinimumWidth(130)
        self.save_button.clicked.connect(self.save_settings)
        abajo.addWidget(self.save_button)

        self.mainLayout.addLayout(abajo)

    # -----------------------------------------------------------------
    # Helpers visuales
    # -----------------------------------------------------------------
    def _crear_boton(self, texto, color=COLOR_NARANJA, color_hover=COLOR_NARANJA_HOVER):
        boton = QPushButton(texto)
        boton.setCursor(Qt.PointingHandCursor)
        boton.setMinimumHeight(38)
        boton.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                padding: 6px 14px;
                border-radius: 6px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {color_hover};
            }}
            QPushButton:pressed {{
                background-color: {color};
            }}
            QPushButton:disabled {{
                background-color: {COLOR_BORDE};
                color: {COLOR_TEXTO_SUAVE};
            }}
        """)
        return boton

    def _crear_caja_icono(self, icono, texto_alterno=""):
        caja = QLabel()
        caja.setObjectName("cajaIcono")
        caja.setFixedSize(36, 36)
        caja.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(icono)
        if not pixmap.isNull():
            caja.setPixmap(pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            caja.setText(texto_alterno)
        return caja

    # -----------------------------------------------------------------
    # Lista
    # -----------------------------------------------------------------
    def _cargar_lista(self):
        self._detener_vista()
        self.lista.blockSignals(True)
        self.lista.clear()

        for recurso in self.manifiesto.contenidos():
            texto = (f"{recurso.get('nombre', '')}   ·   "
                     f"{TIPOS.get(recurso.get('categoria'), 'Archivo')} · "
                     f"{formato_tamano(recurso.get('tamano', 0))}")
            if not recurso.get("en_servidor", True):
                texto += "   (ya no está en el servidor)"

            item = QListWidgetItem()
            item.setData(ROL_CLAVE, recurso["clave"])
            item.setData(ROL_TEXTO, texto)
            item.setFlags((item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
                          & ~Qt.ItemIsDropEnabled)
            item.setCheckState(Qt.Checked if recurso.get("activo", True) else Qt.Unchecked)
            item.setToolTip(recurso.get("url", ""))
            if not recurso.get("en_servidor", True):
                item.setForeground(QColor(COLOR_TEXTO_SUAVE))
            self.lista.addItem(item)

        self.lista.blockSignals(False)
        self._renumerar()
        self._actualizar_resumen()

        indice = self.modo_combo.findData(self.manifiesto.modo)
        self.modo_combo.setCurrentIndex(indice if indice >= 0 else 0)

        self.label_info.clear()
        if self.lista.count():
            self._mensaje_vista("Seleccione un contenido para verlo.")
        else:
            self._mensaje_vista("Aún no hay contenidos descargados.\n\n"
                                "Escriba la URL del servidor y pulse\n«Descargar contenidos».")

    def _renumerar(self):
        for fila in range(self.lista.count()):
            item = self.lista.item(fila)
            item.setText(f"{fila + 1}.  {item.data(ROL_TEXTO)}")

    def _actualizar_resumen(self):
        total = self.lista.count()
        self.label_lista.setText(f"Contenidos ({total})")
        soporte = len(self.manifiesto.recursos) - total
        fecha = self.manifiesto.datos.get("ultima_sincronizacion")
        if fecha:
            self.label_estado.setText(
                f"Última descarga: {formato_fecha(fecha)}   ·   {soporte} archivos de soporte "
                f"(páginas, estilos, scripts y datos)   ·   {self.manifiesto.origen}")
        else:
            self.label_estado.setText("Todavía no se ha descargado ninguna copia local.")

    def _recurso_de(self, item):
        if item is None:
            return None
        return self.manifiesto.recursos.get(item.data(ROL_CLAVE))

    def _mover(self, delta):
        fila = self.lista.currentRow()
        destino = fila + delta
        if fila < 0 or not 0 <= destino < self.lista.count():
            return
        self.lista.blockSignals(True)
        item = self.lista.takeItem(fila)
        self.lista.insertItem(destino, item)
        self.lista.setCurrentRow(destino)
        self.lista.blockSignals(False)
        self._renumerar()

    def _eliminar(self):
        item = self.lista.currentItem()
        recurso = self._recurso_de(item)
        if recurso is None:
            QMessageBox.information(self, "Eliminar", "Seleccione un contenido de la lista.")
            return

        respuesta = QMessageBox.question(
            self, "Eliminar",
            f"¿Eliminar «{recurso.get('nombre', '')}» de la copia local?\n\n"
            "Se borra el archivo de este equipo. Si sigue en el servidor se volverá "
            "a descargar la próxima vez. Para solo ocultarlo, desmarque su casilla.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if respuesta != QMessageBox.Yes:
            return

        self._detener_vista()
        self._parar_medio()
        self._aplicar_cambios()
        self.manifiesto.eliminar(recurso["clave"])
        try:
            self.manifiesto.guardar()
        except Exception as e:
            logging.error("ManagementTab - eliminar: " + str(e))
            QMessageBox.critical(self, "Eliminar", "No se pudo actualizar la copia local.\n" + str(e))
            return

        self.lista.blockSignals(True)
        self.lista.takeItem(self.lista.row(item))
        self.lista.blockSignals(False)
        self._renumerar()
        self._actualizar_resumen()
        self.label_info.clear()
        self._mensaje_vista("Contenido eliminado.")

    # -----------------------------------------------------------------
    # Vista previa
    # -----------------------------------------------------------------
    def _mensaje_vista(self, texto):
        self.vista_label.setPixmap(QPixmap())
        self.vista_label.setText(texto)
        self.vista.setCurrentWidget(self.vista_label)

    def _asegurar_reproductor(self):
        if self.reproductor is None and HAY_VIDEO:
            self.reproductor = QMediaPlayer(self)
            self.salida_audio = QAudioOutput(self)
            self.salida_audio.setVolume(0.6)
            self.reproductor.setAudioOutput(self.salida_audio)
            self.reproductor.setVideoOutput(self.video)
            self.reproductor.mediaStatusChanged.connect(self._estado_medio)
            self.reproductor.errorOccurred.connect(self._error_medio)
        return self.reproductor

    def _parar_medio(self):
        if self.reproductor is not None:
            self.reproductor.stop()
            self.reproductor.setSource(QUrl())

    @Slot(QListWidgetItem, QListWidgetItem)
    def _al_seleccionar(self, actual, anterior):
        # Un clic del usuario detiene la vista en orden
        if self.reproduciendo:
            self._detener_vista()
        recurso = self._recurso_de(actual)
        if recurso is not None:
            self._mostrar(recurso)

    def _mostrar(self, recurso):
        """
        Muestra un contenido en la vista previa.
        :return: bool. True si quedo reproduciendo un video/audio
        """
        self._parar_medio()
        categoria = recurso.get("categoria")
        ruta = ruta_archivo(recurso)

        self.label_info.setText(
            f"{TIPOS.get(categoria, 'Archivo')} · {formato_tamano(recurso.get('tamano', 0))}"
            f" · descargado {formato_fecha(recurso.get('descargado'))}")
        self.label_info.setToolTip(recurso.get("url", ""))

        if not os.path.exists(ruta):
            self._mensaje_vista("El archivo no está en este equipo.\n"
                                "Vuelva a descargar los contenidos.")
            return False

        if categoria == "imagen":
            pixmap = QPixmap(ruta)
            if pixmap.isNull():
                self._mensaje_vista("No se pudo abrir la imagen.")
                return False
            self.vista_label.setText("")
            self.vista_label.setPixmap(pixmap.scaled(
                self.vista.size() - QSize(8, 8), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.vista.setCurrentWidget(self.vista_label)
            return False

        if categoria in ("video", "audio") and HAY_VIDEO:
            if categoria == "audio":
                self._mensaje_vista("♪\n\n" + recurso.get("nombre", ""))
            else:
                self.vista.setCurrentWidget(self.video)
            reproductor = self._asegurar_reproductor()
            reproductor.setSource(QUrl.fromLocalFile(ruta))
            reproductor.play()
            return True

        self._mensaje_vista(f"{recurso.get('nombre', '')}\n\n"
                            "No hay vista previa para este tipo de archivo.")
        return False

    @Slot()
    def _alternar_vista(self):
        if self.reproduciendo:
            self._detener_vista()
            return
        if not any(self.lista.item(i).checkState() == Qt.Checked
                   for i in range(self.lista.count())):
            QMessageBox.information(self, "Vista en orden", "No hay contenidos activos para mostrar.")
            return
        self.reproduciendo = True
        self.cola_vista = []
        self.vista_button.setText("■  Detener")
        self._avanzar_vista()

    @Slot()
    def _avanzar_vista(self):
        if not self.reproduciendo:
            return
        if not self.cola_vista:
            # Vuelve a empezar: recorre los activos en el orden actual de la lista
            self.cola_vista = [i for i in range(self.lista.count())
                               if self.lista.item(i).checkState() == Qt.Checked]
            if not self.cola_vista:
                self._detener_vista()
                return

        fila = self.cola_vista.pop(0)
        self.lista.blockSignals(True)
        self.lista.setCurrentRow(fila)
        self.lista.blockSignals(False)

        recurso = self._recurso_de(self.lista.item(fila))
        reproduciendo_medio = self._mostrar(recurso) if recurso else False
        if not reproduciendo_medio:
            self.timer_vista.start(DURACION_IMAGEN * 1000)
        # Si es video/audio, avanza cuando termina (ver _estado_medio)

    def _detener_vista(self):
        self.reproduciendo = False
        self.cola_vista = []
        self.timer_vista.stop()
        self.vista_button.setText("▶  Vista en orden")
        self._parar_medio()

    def _estado_medio(self, estado):
        if HAY_VIDEO and estado == QMediaPlayer.EndOfMedia and self.reproduciendo:
            self._avanzar_vista()

    def _error_medio(self, error, mensaje=""):
        if error == QMediaPlayer.NoError:
            return
        self._mensaje_vista("No se pudo reproducir el archivo.\n" + (mensaje or ""))
        if self.reproduciendo:
            self.timer_vista.start(1500)

    def hideEvent(self, event):
        # Al cambiar de pestaña no debe quedar sonando un video
        self._detener_vista()
        super().hideEvent(event)

    # -----------------------------------------------------------------
    # Descarga
    # -----------------------------------------------------------------
    @Slot()
    def _sincronizar_o_cancelar(self):
        if self.hilo is not None:
            if self.sincronizador is not None:
                self.sincronizador.cancelar()
            self.sync_button.setEnabled(False)
            self.label_estado.setText("Cancelando ...")
            return

        url = normalizar_url(self.url_entry.text())
        if not url or not origen_de(url):
            QMessageBox.warning(self, "Descargar contenidos", "Escriba una URL de servidor válida.")
            return
        self.url_entry.setText(url)

        if self.manifiesto.origen and not mismo_origen(self.manifiesto.origen, url):
            respuesta = QMessageBox.question(
                self, "Descargar contenidos",
                f"La copia local actual es de {self.manifiesto.origen}.\n\n"
                f"Si descarga de {origen_de(url)} esa copia se reemplaza. ¿Continuar?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if respuesta != QMessageBox.Yes:
                return

        # Tambien se descargan las demas pantallas web del mismo servidor
        urls = [url] + [normalizar_url(u) for u in urls_inicio_configuradas()
                        if mismo_origen(u, url) and normalizar_url(u) != url]

        # Se guardan el orden y las casillas antes de que la descarga reescriba el manifiesto
        self._detener_vista()
        self._aplicar_cambios()
        try:
            self.manifiesto.guardar()
        except Exception as e:
            logging.error("ManagementTab - guardar antes de descargar: " + str(e))

        self._bloquear(True)
        self.hilo = QThread(self)
        self.sincronizador = Sincronizador(urls)
        self.sincronizador.moveToThread(self.hilo)
        self.hilo.started.connect(self.sincronizador.ejecutar)
        self.sincronizador.progreso.connect(self._al_progreso)
        self.sincronizador.terminado.connect(self._al_terminar)
        self.sincronizador.terminado.connect(self.hilo.quit)
        self.hilo.finished.connect(self.sincronizador.deleteLater)
        self.hilo.finished.connect(self.hilo.deleteLater)
        self.hilo.finished.connect(self._hilo_terminado)
        self.hilo.start()

    def _bloquear(self, descargando):
        self.sync_button.setText("Cancelar" if descargando else "Descargar contenidos")
        self.sync_button.setEnabled(True)
        for widget in (self.url_entry, self.lista, self.subir_button, self.bajar_button,
                       self.eliminar_button, self.vista_button, self.modo_combo, self.save_button):
            widget.setEnabled(not descargando)
        if descargando:
            self.barra.setRange(0, 0)
            self.barra.show()
        else:
            self.barra.hide()

    @Slot(int, int, str)
    def _al_progreso(self, actual, total, mensaje):
        if total > 0:
            self.barra.setRange(0, total)
            self.barra.setValue(actual)
            mensaje = f"[{actual}/{total}]  {mensaje}"
        else:
            self.barra.setRange(0, 0)
        ancho = max(100, self.label_estado.width())
        self.label_estado.setText(
            self.label_estado.fontMetrics().elidedText(mensaje, Qt.ElideMiddle, ancho))

    @Slot(bool, str)
    def _al_terminar(self, ok, mensaje):
        self.manifiesto = Manifiesto()
        self._cargar_lista()
        self._bloquear(False)
        if ok:
            QMessageBox.information(self, "Descargar contenidos", "Descarga terminada.\n\n" + mensaje)
        else:
            QMessageBox.warning(self, "Descargar contenidos", mensaje)

    @Slot()
    def _hilo_terminado(self):
        self.hilo = None
        self.sincronizador = None

    @Slot()
    def _al_salir(self):
        if self.sincronizador is not None:
            self.sincronizador.cancelar()
        if self.hilo is not None:
            self.hilo.quit()
            self.hilo.wait(5000)

    # -----------------------------------------------------------------
    # Guardar
    # -----------------------------------------------------------------
    def _aplicar_cambios(self):
        """Pasa al manifiesto el orden, las casillas y el modo de la interfaz."""
        orden = []
        for fila in range(self.lista.count()):
            item = self.lista.item(fila)
            clave = item.data(ROL_CLAVE)
            recurso = self.manifiesto.recursos.get(clave)
            if recurso is None:
                continue
            recurso["activo"] = item.checkState() == Qt.Checked
            orden.append(clave)
        self.manifiesto.datos["orden"] = orden
        self.manifiesto.datos["modo"] = self.modo_combo.currentData() or MODO_AUTOMATICO

    def save_settings(self):
        self._aplicar_cambios()
        try:
            self.manifiesto.guardar()
        except Exception as e:
            logging.error("ManagementTab - guardar: " + str(e))
            QMessageBox.critical(self, "Guardar", "No se pudo guardar la configuración.\n" + str(e))
            return
        QMessageBox.information(self, "Guardar",
                                "Cambios guardados.\nEl reproductor los usará la próxima vez que se abra.")
