import sys

from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
# Otras librerias
import os
import logging
import json
import threading
import time
import subprocess
import re


# Llaves que guarda la configuracion para cada pantalla
LLAVE_MONITOR = "MonitorAsignado"          # indice del monitor (0 = automatico)
LLAVE_MONITOR_NOMBRE = "MonitorNombre"     # nombre real: HDMI-1, VGA-1, DP-2...

# Llaves opcionales en config.json
LLAVE_KIOSCO = "ModoKioscoEstricto"        # omite al gestor de ventanas
LLAVE_TACTIL = "MapeoTactil"               # "auto" o {"dispositivo": "monitor"}


class ScreenWindow(QMainWindow):
    """
    Ventana independiente para una pantalla del archivo de configuracion
    :param frame: MainFrame. Contenido de la pantalla
    :param titulo: str. Titulo de la ventana
    :param flags: Qt.WindowFlags. Banderas heredadas de la ventana principal
    :param icono: QIcon. Icono de la aplicacion
    """

    def __init__(self, frame, titulo, flags, icono):
        super().__init__()
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.setWindowIcon(icono)
        self.setWindowTitle(titulo)
        # Qt.Window es obligatorio: sin el, una ventana de nivel superior
        # con banderas propias queda como Qt.Widget y el gestor de ventanas
        # la trata de forma inconsistente (decoracion y pantalla completa)
        self.setWindowFlags(Qt.Window | flags)
        self.frame = frame
        self.setCentralWidget(frame)

    def closeEvent(self, event):
        """
        Cierra el contenido de la pantalla
        """
        try:
            self.frame.closeEvent()
        except Exception:
            logging.exception("ScreenWindow - error al cerrar el frame")
        event.accept()


class Player(QMainWindow):
    """
    Clase principal de la aplicacion.
    Es la ventana de la primera pantalla y administra una ventana adicional
    por cada pantalla restante, repartidas entre los monitores conectados.
    """

    # Señal para cambiar el estado de las ventanas desde el hilo de monitoreo
    estado_pantalla = Signal(bool)

    def __init__(self, debug=False):
        """
        Clase principal de la aplicacion
        """
        if debug:
            from AppFrames.MainFrame import MainFrame
        else:
            from .AppFrames.MainFrame import MainFrame
        super().__init__()
        self.flags = Qt.WindowFlags()
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)

        # Icono de la Aplicacion
        self.icono = QIcon()
        path = os.path.expanduser('~') + "/.config/Ciel/C-Media_Player/Media/Logo-CMedia_lx.png"
        self.icono.addFile(path, QSize(), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(self.icono)

        # Nombre de la Aplicacion
        QCoreApplication.setApplicationName("C-Media Player v2.2")

        self.screen_disconnected = False
        # Se usa "cerrando" y no "close" para no pisar el metodo close() de QWidget
        self.cerrando = False
        self.app = QApplication.instance()

        # Obtencion de configuracion
        self.sett = self.get_sett()
        if "$" == self.sett["Ruta"][0]:
            var = os.environ[self.sett["Ruta"][1:self.sett["Ruta"].find("/")]]
            file_name = var + self.sett["Ruta"][self.sett["Ruta"].find("/"):]
        else:
            file_name = self.sett["Ruta"]
        self.screen_config = self.get_screen_config(file_name)

        self.pantalla_completa = self.sett.get("PantallaCompleta", False)
        # Modo kiosco estricto: omite al gestor de ventanas por completo.
        # al saltarse el gestor, la ventana no recibe el foco de
        # entrada de la forma habitual y el tactil o el teclado pueden dejar
        # de responder. Actívelo solo si el gestor ignora la pantalla completa.
        self.kiosco = self.sett.get(LLAVE_KIOSCO, False)

        # Ventana siempre visible (Top Most)
        if self.sett["SiempreVisible"]:
            self.flags |= Qt.WindowStaysOnTopHint

        # Mostrar Borde de la Ventana
        if not (self.sett["MostrarBordeVentana"]):
            self.flags |= Qt.FramelessWindowHint

        if self.kiosco:
            self.flags |= Qt.FramelessWindowHint
            self.flags |= Qt.X11BypassWindowManagerHint

        self.setWindowFlags(Qt.Window | self.flags)

        self.estado_pantalla.connect(self._aplicar_estado_pantalla)

        # ------------------------------------------------------------------
        # Creacion de las pantallas: una ventana por cada una
        # ------------------------------------------------------------------
        self.frames = {}
        self.titulos = {}
        self.asignaciones = {}   # numero -> {"indice": int, "nombre": str}
        self.ventanas = {}       # ventanas secundarias (pantalla 2 en adelante)

        for pantalla in self.screen_config["Pantallas"]:
            numero = pantalla.get("ScreenNumber", len(self.frames) + 1)
            self.frames[numero] = MainFrame(pantalla["Controles"])

            # Los titulos deben ser unicos: si varias pantallas comparten el
            # mismo TitleName no hay forma de distinguirlas en el log
            titulo = pantalla.get("TitleName") or "C-Media Player"
            if titulo in self.titulos.values():
                titulo = f"{titulo} [{numero}]"
            self.titulos[numero] = titulo

            self.asignaciones[numero] = {
                "indice": pantalla.get(LLAVE_MONITOR, 0),
                "nombre": pantalla.get(LLAVE_MONITOR_NOMBRE, "")
            }

        numeros = sorted(self.frames)

        # La primera pantalla es esta misma ventana
        self.numero_principal = numeros[0]
        self.setWindowTitle(self.titulos[self.numero_principal])
        self.setCentralWidget(self.frames[self.numero_principal])

        # El resto se abre en ventanas propias
        for numero in numeros[1:]:
            self.ventanas[numero] = ScreenWindow(self.frames[numero],
                                                 self.titulos[numero],
                                                 self.flags, self.icono)

        self._registrar_monitores()

        # Geometria inicial. No se crea la ventana nativa aqui: hacerlo antes
        # de mostrar rompe la inicializacion de QtWebEngine en algunos drivers.
        self._preasignar_geometria()

        # Reacomodo automatico cuando se conecta o desconecta un monitor
        try:
            self.app.screenAdded.connect(self._monitores_cambiaron)
            self.app.screenRemoved.connect(self._monitores_cambiaron)
        except Exception:
            logging.exception("Player - no se pudo conectar la detección de monitores")

        # Hilo de monitoreo (compatibilidad con el comportamiento anterior)
        self.thread = threading.Thread(target=self.print_screens, daemon=True)
        self.thread.start()

    # ------------------------------------------------------------------
    # Deteccion de monitores
    # ------------------------------------------------------------------
    def _registrar_monitores(self):
        """
        Deja en el log el estado real de los monitores y avisa si estan
        en modo espejo, que es el caso en que el reparto no puede funcionar
        """
        try:
            monitores = self.app.screens()
        except Exception:
            logging.exception("Player - no se pudieron leer los monitores")
            return

        logging.info(f"Player - monitores detectados: {len(monitores)}")

        geometrias = {}
        for indice, monitor in enumerate(monitores):
            geo = monitor.geometry()
            clave = (geo.x(), geo.y(), geo.width(), geo.height())
            geometrias.setdefault(clave, []).append(monitor.name())
            logging.info(f"Player - monitor [{indice + 1}] {monitor.name()} "
                         f"{geo.width()}x{geo.height()} en ({geo.x()},{geo.y()})")

        for nombres in geometrias.values():
            if len(nombres) > 1:
                logging.warning(
                    "Player - monitores en ESPEJO con la misma geometria: "
                    + " = ".join(nombres)
                    + ". Las ventanas quedaran encimadas. Configure modo extendido "
                      "con xrandr para poder repartirlas.")

        if len(monitores) < len(self.frames):
            logging.warning(
                f"Player - hay {len(self.frames)} pantalla(s) configurada(s) "
                f"pero solo {len(monitores)} monitor(es) disponible(s).")

    def _pares_ventanas(self):
        """
        Ventanas de la aplicacion en orden de pantalla
        :return: list[tuple]. [(numero, ventana), ...]
        """
        pares = [(self.numero_principal, self)]
        pares += [(n, self.ventanas[n]) for n in sorted(self.ventanas)]
        return pares

    def _buscar_monitor(self, asignacion):
        """
        Busca el monitor pedido por una pantalla.
        Se prioriza el nombre (HDMI-1, VGA-1...) porque el indice cambia
        segun el orden en que el sistema detecte las salidas de video.
        :param asignacion: dic. {"indice": int, "nombre": str}
        :return: QScreen | None
        """
        monitores = self.app.screens()

        nombre = asignacion.get("nombre", "")
        if nombre:
            for monitor in monitores:
                if monitor.name() == nombre:
                    return monitor
            logging.warning(f"Player - el monitor '{nombre}' no está conectado")

        indice = asignacion.get("indice", 0)
        if indice and indice <= len(monitores):
            return monitores[indice - 1]
        if indice:
            logging.warning(f"Player - el monitor {indice} no está conectado")

        return None

    def _calcular_monitores(self):
        """
        Decide en que monitor va cada pantalla.
        Primero respeta las asignaciones explicitas; las que estan en
        automatico se reparten en los monitores que queden libres.
        :return: dict. numero de pantalla -> QScreen
        """
        monitores = self.app.screens()
        if not monitores:
            return {}

        principal = self.app.primaryScreen() or monitores[0]
        resultado = {}
        usados = set()

        # 1. Asignaciones explicitas y validas
        for numero, _ in self._pares_ventanas():
            asignacion = self.asignaciones.get(numero, {})
            if not asignacion.get("nombre") and not asignacion.get("indice"):
                continue
            monitor = self._buscar_monitor(asignacion)
            if monitor is not None:
                resultado[numero] = monitor
                usados.add(monitor.name())

        # 2. El resto toma los monitores libres, en orden
        libres = [m for m in monitores if m.name() not in usados]
        for numero, _ in self._pares_ventanas():
            if numero in resultado:
                continue
            resultado[numero] = libres.pop(0) if libres else principal

        return resultado

    # ------------------------------------------------------------------
    # Ubicacion de las ventanas
    # ------------------------------------------------------------------
    def _preasignar_geometria(self):
        """
        Fija la geometria de cada ventana antes de mostrarla.
        En un escritorio extendido todos los monitores comparten un mismo
        sistema de coordenadas, asi que la geometria basta para que el
        gestor de ventanas mapee cada ventana en el monitor correcto.
        """
        try:
            asignados = self._calcular_monitores()
            for numero, ventana in self._pares_ventanas():
                monitor = asignados.get(numero)
                if monitor is not None:
                    ventana.setGeometry(self._geometria(monitor, numero, asignados))
        except Exception:
            # Una falla ubicando ventanas nunca debe impedir que el player abra
            logging.exception("Player - error al preasignar la geometría")

    def _geometria(self, monitor, numero, asignados):
        """
        Calcula la geometria de una ventana en su monitor
        :param monitor: QScreen. Monitor destino
        :param numero: int. Numero de pantalla
        :param asignados: dict. Reparto completo, para detectar ventanas encimadas
        :return: QRect
        """
        area = monitor.geometry()

        if self.pantalla_completa or self.kiosco:
            return area

        # Ventana normal: tamaño de config.json dentro del monitor destino
        ancho = self.sett["AnchoRequerido"]
        alto = self.sett["AltoRequerido"]
        izquierda = self.sett["LeftRequerido"]
        arriba = self.sett["TopRequerido"]

        # Si varias ventanas caen en el mismo monitor se escalonan
        previas = [n for n, m in asignados.items()
                   if m.name() == monitor.name() and n < numero]
        desplazamiento = 40 * len(previas)

        return QRect(area.x() + izquierda + desplazamiento,
                     area.y() + arriba + desplazamiento,
                     ancho, alto)

    def _show_nativo(self, ventana):
        """
        Muestra una ventana usando el show() de QMainWindow.

        IMPORTANTE: esta clase sobrescribe show(). Si aqui se llamara
        ventana.show() y la ventana fuera la principal (self), se volveria
        a entrar en Player.show() de forma indefinida (RecursionError).
        :param ventana: QMainWindow
        """
        QMainWindow.show(ventana)

    def _mostrar_ventana(self, ventana, monitor, geometria):
        """
        Muestra una ventana en su monitor con el estado correcto.
        :param ventana: QMainWindow
        :param monitor: QScreen. Monitor destino
        :param geometria: QRect. Geometria calculada
        """
        if self.kiosco:
            # Sin gestor de ventanas: la geometria manda y no hay decoracion
            ventana.setGeometry(geometria)
            self._show_nativo(ventana)
            ventana.raise_()
            return

        # La geometria se fija ANTES de mostrar, para que el gestor sepa
        # en que monitor debe mapear (y luego expandir) la ventana
        ventana.setGeometry(geometria)
        self._show_nativo(ventana)

        if self.pantalla_completa:
            # Segunda pasada: algunos gestores ignoran el estado de pantalla
            # completa si se pide en el mismo ciclo del mapeo de la ventana
            QTimer.singleShot(150, lambda v=ventana, m=monitor, g=geometria:
                              self._forzar_pantalla_completa(v, m, g))

    def _forzar_pantalla_completa(self, ventana, monitor, geometria, intento=1):
        """
        Reaplica la pantalla completa una vez la ventana ya esta mapeada.

        NO se usa setScreen() aqui: en X11, cambiar la pantalla de una ventana
        que ya esta visible puede hacer que Qt la destruya y la vuelva a crear,
        y el gestor la reubica en el monitor principal. Como en un escritorio
        extendido todos los monitores comparten un mismo sistema de coordenadas,
        basta con mover la ventana a las coordenadas del monitor destino.

        :param ventana: QMainWindow
        :param monitor: QScreen. Monitor destino
        :param geometria: QRect. Area del monitor
        :param intento: int. Numero de intento actual
        """
        if self.cerrando or not ventana.isVisible():
            return

        try:
            # Para moverla de monitor primero hay que sacarla de pantalla
            # completa: un gestor no reubica una ventana ya expandida
            if ventana.isFullScreen():
                ventana.showNormal()

            # move() se respeta mejor que setGeometry() para la posicion
            ventana.move(geometria.topLeft())
            ventana.resize(geometria.width(), geometria.height())
            ventana.showFullScreen()
            ventana.raise_()

            QTimer.singleShot(500, lambda v=ventana, m=monitor, g=geometria, i=intento:
                              self._verificar(v, m, g, i))
        except Exception:
            logging.exception("Player - error al aplicar pantalla completa")

    def _monitor_real(self, ventana):
        """
        Determina en que monitor esta realmente una ventana, usando el centro
        de su geometria. Es mas fiable que windowHandle().screen(), que a veces
        queda desactualizado tras un movimiento hecho por el gestor de ventanas.
        :param ventana: QMainWindow
        :return: QScreen | None
        """
        centro = ventana.frameGeometry().center()
        for pantalla in self.app.screens():
            if pantalla.geometry().contains(centro):
                return pantalla

        handle = ventana.windowHandle()
        return handle.screen() if handle is not None else None

    def _verificar(self, ventana, monitor, geometria, intento=1):
        """
        Comprueba que la ventana quedo en pantalla completa y en su monitor.
        Si el gestor de ventanas la movio, se reintenta hasta MAX_INTENTOS.
        :param ventana: QMainWindow
        :param monitor: QScreen. Monitor esperado
        :param geometria: QRect. Area del monitor
        :param intento: int. Numero de intento actual
        """
        if self.cerrando or not ventana.isVisible():
            return

        MAX_INTENTOS = 4

        real = self._monitor_real(ventana)
        nombre_real = real.name() if real is not None else "?"
        titulo = ventana.windowTitle()

        bien_ubicada = (nombre_real == monitor.name())
        bien_expandida = ventana.isFullScreen()

        if bien_ubicada and bien_expandida:
            if intento > 1:
                logging.info(f"Player - '{titulo}' quedó correctamente en "
                             f"{monitor.name()} tras {intento} intentos")
            return

        if intento < MAX_INTENTOS:
            logging.info(f"Player - '{titulo}' quedó en {nombre_real} "
                         f"(esperado {monitor.name()}, pantalla completa: "
                         f"{bien_expandida}). Reintento {intento + 1}...")
            # Cada reintento espera un poco mas: el gestor puede seguir
            # reacomodando ventanas durante el arranque
            QTimer.singleShot(300 * intento,
                              lambda v=ventana, m=monitor, g=geometria, i=intento + 1:
                              self._forzar_pantalla_completa(v, m, g, i))
            return

        # Se agotaron los reintentos: el gestor de ventanas no coopera
        if not bien_ubicada:
            logging.warning(f"Player - '{titulo}' quedó en el monitor {nombre_real} "
                            f"y no en {monitor.name()} tras {MAX_INTENTOS} intentos. "
                            "Active ModoKioscoEstricto en config.json.")
        if not bien_expandida:
            logging.warning(f"Player - '{titulo}' NO quedó en pantalla completa "
                            f"tras {MAX_INTENTOS} intentos. "
                            "Active ModoKioscoEstricto en config.json.")

    def _aplicar_ubicaciones(self):
        """
        Reubica ventanas ya visibles, por ejemplo tras conectar un monitor.
        Se sale de pantalla completa primero: un gestor de ventanas no mueve
        de monitor una ventana que ya esta expandida.
        """
        try:
            asignados = self._calcular_monitores()
        except Exception:
            logging.exception("Player - error al calcular monitores")
            return

        for numero, ventana in self._pares_ventanas():
            monitor = asignados.get(numero)
            if monitor is None:
                continue

            try:
                geometria = self._geometria(monitor, numero, asignados)

                if self.kiosco:
                    ventana.setGeometry(geometria)
                    ventana.raise_()
                elif self.pantalla_completa:
                    ventana.showNormal()
                    ventana.setGeometry(geometria)
                    QTimer.singleShot(150, lambda v=ventana, m=monitor, g=geometria:
                                      self._forzar_pantalla_completa(v, m, g))
                else:
                    ventana.setGeometry(geometria)

                logging.info(f"Player - pantalla {numero} -> monitor {monitor.name()}")
            except Exception:
                logging.exception(f"Player - error al reubicar la pantalla {numero}")

    def show(self):
        """
        Muestra la ventana principal y todas las ventanas secundarias,
        cada una en el monitor que le corresponde.
        Si la ubicacion falla, las ventanas se muestran igual.
        """
        try:
            asignados = self._calcular_monitores()
        except Exception:
            logging.exception("Player - error al calcular monitores")
            asignados = {}

        for numero, ventana in self._pares_ventanas():
            monitor = asignados.get(numero)

            if monitor is None:
                self._show_nativo(ventana)
                if self.pantalla_completa and not self.kiosco:
                    ventana.showFullScreen()
                continue

            try:
                geometria = self._geometria(monitor, numero, asignados)
                self._mostrar_ventana(ventana, monitor, geometria)
                logging.info(f"Player - pantalla {numero} "
                             f"'{self.titulos.get(numero)}' -> monitor {monitor.name()} "
                             f"{geometria.width()}x{geometria.height()} "
                             f"en ({geometria.x()},{geometria.y()})")
            except Exception:
                logging.exception(f"Player - error al mostrar la pantalla {numero}")
                # Ultimo recurso: mostrar sin ubicar
                try:
                    self._show_nativo(ventana)
                except Exception:
                    logging.exception(f"Player - no se pudo mostrar la pantalla {numero}")

        # El tactil se mapea cuando las ventanas ya estan en su sitio
        QTimer.singleShot(2000, self._mapear_tactil)

    def ventanas_todas(self):
        """
        Devuelve la ventana principal junto con las secundarias
        :return: list[QMainWindow]
        """
        return [ventana for _, ventana in self._pares_ventanas()]

    @Slot()
    def _monitores_cambiaron(self, *args):
        """
        Se llama cuando el sistema agrega o quita un monitor.
        Espera a que el escritorio termine de reorganizarse y reparte de nuevo.
        """
        if self.cerrando:
            return
        logging.info(f"Player - cambio de monitores: {len(self.app.screens())} conectado(s)")
        self._registrar_monitores()
        QTimer.singleShot(1500, self._reubicar)

    @Slot()
    def _reubicar(self):
        """
        Reaplica las ubicaciones despues de un cambio de monitores
        """
        if self.cerrando:
            return
        self._aplicar_ubicaciones()
        # Al cambiar el tamaño del escritorio virtual el tactil se
        # descalibra, asi que hay que volver a mapearlo
        QTimer.singleShot(2000, self._mapear_tactil)

    @Slot(bool)
    def _aplicar_estado_pantalla(self, completa):
        """
        Aplica pantalla completa o ventana normal a todas las ventanas.
        Se ejecuta siempre en el hilo de la interfaz.
        :param completa: bool. True para pantalla completa
        """
        if completa:
            self._aplicar_ubicaciones()
        else:
            for ventana in self.ventanas_todas():
                ventana.showNormal()

    # ------------------------------------------------------------------
    # Mapeo de pantallas tactiles
    # ------------------------------------------------------------------
    def _dispositivos_tactiles(self):
        """
        Busca dispositivos de entrada que parezcan pantallas tactiles
        :return: list[dict]. [{"id": str, "nombre": str}, ...]
        """
        try:
            salida = subprocess.run(["xinput", "list"], capture_output=True,
                                    text=True, timeout=10).stdout
        except Exception:
            logging.exception("Player - no se pudo ejecutar xinput")
            return []

        dispositivos = []
        for linea in salida.splitlines():
            if "slave" not in linea or "pointer" not in linea:
                continue

            coincidencia = re.search(r"↳\s+(.+?)\s+id=(\d+)", linea)
            if not coincidencia:
                continue

            nombre = coincidencia.group(1).strip()
            clave = nombre.lower()
            if any(t in clave for t in ["touch", "tactil", "elan", "egalax",
                                        "ilitek", "goodix", "silead",
                                        "digitizer"]):
                dispositivos.append({"id": coincidencia.group(2),
                                     "nombre": nombre})

        return dispositivos

    def _mapear_tactil(self):
        """
        Mapea las pantallas tactiles a su monitor.

        En X11 un panel tactil reparte sus coordenadas sobre todo el
        escritorio virtual. Con un solo monitor la relacion es 1 a 1, pero
        al conectar un segundo monitor el escritorio se ensancha y el tactil
        queda descalibrado: el toque aterriza en el monitor equivocado o
        parece no responder. xinput map-to-output limita el dispositivo a
        un solo monitor y restaura la correspondencia.
        """
        if self.cerrando:
            return

        config = self.sett.get(LLAVE_TACTIL)
        if not config:
            return   # sin configuracion no se toca nada

        dispositivos = self._dispositivos_tactiles()
        if not dispositivos:
            logging.info("Player - no se detectaron dispositivos táctiles")
            return

        # Modo automatico: todo el tactil va al monitor de la pantalla 1
        if isinstance(config, str) and config.lower() == "auto":
            asignados = self._calcular_monitores()
            monitor = asignados.get(self.numero_principal)
            if monitor is None:
                return
            destino = {d["nombre"]: monitor.name() for d in dispositivos}
        elif isinstance(config, dict):
            destino = config
        else:
            logging.warning(f"Player - valor inválido en {LLAVE_TACTIL}: {config}")
            return

        conectados = [m.name() for m in self.app.screens()]

        for dispositivo in dispositivos:
            monitor = destino.get(dispositivo["nombre"])
            if not monitor:
                continue
            if monitor not in conectados:
                logging.warning(f"Player - táctil '{dispositivo['nombre']}': el "
                                f"monitor {monitor} no está conectado")
                continue

            try:
                resultado = subprocess.run(
                    ["xinput", "map-to-output", dispositivo["id"], monitor],
                    capture_output=True, text=True, timeout=10)
                if resultado.returncode == 0:
                    logging.info(f"Player - táctil '{dispositivo['nombre']}' "
                                 f"mapeado a {monitor}")
                else:
                    logging.warning(f"Player - no se pudo mapear el táctil "
                                    f"'{dispositivo['nombre']}': "
                                    f"{resultado.stderr.strip()}")
            except Exception:
                logging.exception("Player - error al mapear el táctil")

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    def closeEvent(self, event):
        """
        Evento de cierre de la aplicacion: cierra tambien las pantallas secundarias
        """
        self.cerrando = True
        for numero in sorted(self.ventanas, reverse=True):
            try:
                self.ventanas[numero].close()
            except Exception:
                logging.exception(f"Player - error al cerrar la pantalla {numero}")
        try:
            self.centralWidget().closeEvent()
        except Exception:
            logging.exception("Player - error al cerrar el frame principal")
        event.accept()

    def get_screen_config(self, ruta):
        """
        Obtiene la informacion de las pantallas y su configuracion
        :param ruta: str. Ruta donde se encuentra el archivo de configuracion
        :return: dic. Configuracion extraida del archivo json
        """
        try:
            with open(ruta, 'r', encoding="utf-8-sig") as file:
                screen_config = json.load(file)
            return screen_config
        except Exception:
            logging.exception(f"Player - no se pudo leer el archivo de pantallas: {ruta}")
            QMessageBox.warning(self, "Advertencia",
                                "Ha ocurrido un problema con el archivo de las pantallas, "
                                "seleccione uno válido desde la aplicación de configuración.")
            sys.exit()

    def get_sett(self):
        """
        Obtiene la informacion de configuracion de la aplicacion
        :return: dic. Configuracion extraida del archivo json
        """
        path = os.path.expanduser('~') + "/.config/Ciel/C-Media_Player/configs/config.json"
        try:
            with open(path, "r") as file:
                sett = json.load(file)
            return sett
        except Exception:
            logging.exception(f"Player - no se pudo leer la configuración: {path}")
            QMessageBox.warning(self, "Advertencia",
                                "Uno de los archivos de la aplicacción no fue instalado correctamente. "
                                "Por favor reinstale la aplicación")
            sys.exit()

    def focus_changed(self):
        if self.pantalla_completa and not self.kiosco:
            if self.isActiveWindow():
                self.showFullScreen()
        if self.sett["SiempreVisible"]:
            for numero in sorted(self.frames):
                try:
                    self.frames[numero].focus_changed()
                except Exception:
                    logging.exception(f"Player - focus_changed en la pantalla {numero}")
            qApp.setActiveWindow(self)

    def print_screens(self):
        """
        Monitorea la conexion de monitores y ajusta todas las ventanas.
        No toca la interfaz directamente: emite una señal hacia el hilo principal.
        """
        while not self.cerrando:
            try:
                nombre = self.app.screens()[0].name()
            except Exception:
                time.sleep(0.5)
                continue

            if nombre == ":0.0" and not self.screen_disconnected:
                self.screen_disconnected = True
                self.estado_pantalla.emit(False)

            elif self.screen_disconnected and nombre != ":0.0":
                time.sleep(0.5)
                if self.pantalla_completa:
                    self.estado_pantalla.emit(True)
                self.screen_disconnected = False

            time.sleep(0.3)
        