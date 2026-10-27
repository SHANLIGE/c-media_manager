from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *


# Librerías Navegador Web
from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineSettings
from PySide6.QtWebEngineCore import QWebEngineCertificateError
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from PySide6.QtCore import QFile, QUrl

from .Event import Event
import logging

# Clases externas
from .JSBridge import JSBridge
from .NavBar import NavigationBar
from .Controllers.NetworkController import NetworkController
from .Controllers.SpeechSynthesis import SpeechSynthesis
from .Controllers.LocalMedia import LocalMedia
from .Controllers.CredentialManager import CredentialManager
from .Controllers.SystemInfo import SystemInfo

# NUEVO: controlador de cierre de la aplicacion y su inyeccion de JS.
# Ajustar la ruta del import segun donde se dejen los archivos.
from .Controllers.AppController import AppController
from .cierre_player import js_cierre

import sys
import logging
import os
from PySide6.QtNetwork import QSslCertificate, QSslSocket, QSslConfiguration


# Pantalla y nombre del boton oculto de cierre dentro del recurso.
# El boton se llama "Cerrar" en todos los players; si alguna sede usa otra pantalla, agregarla a esta lista y se enganchan todas.
BOTONES_CIERRE = [
    ("Utilidad", "Cerrar"),
]


class WebPage(QWebEnginePage):
    """
    Clase que sobre escribe la clase QWebEnginePage, base para instanciar una pagina web
    """

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        """
        Sobreescribe el mensaje de la consola de JavaScript, para imprimirlo en la consola
        :param level: int. nivel del mensaje
        :param message: str. mensaje
        :param lineNumber: int. numero de linea
        :param sourceID: str. id de la fuente
        """
        log = f"JS Console [{level}] line {lineNumber}: {message}"
        print(log)

    @Slot(str)
    def ejecutarJavaScript(self, script):
        """
        Ejecuta un script de JavaScript en la página web
        :param script: str. script a ejecutar
        """
        self.runJavaScript(script)


class WebViewFrame(QWidget):
    """
    Clase del Frame del contenedor Web
    :param settings: dic. Configuración del navegador
    """
    def __init__(self, settings):
        """
        Clase del Frame del contenedor Web
        :param settings: dic. Configuración del navegador
        """
        super().__init__()

        #Set Layout
        self.mainLayout = QGridLayout()
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.mainLayout)

        #Creación del contenedor
        self.view = QWebEngineView(self)
        self.view.setContextMenuPolicy(Qt.NoContextMenu)
        self.view.setPage(WebPage(self.view))
        self.nav_bar = None

        #Eliminar para producción

        self.view.page().certificateError.connect(self.on_cert_error)

        #Eliminar para producción


        self.loaded = False
        self.view.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)

        self.view.settings().setAttribute(
            QWebEngineSettings.PlaybackRequiresUserGesture, False)

        self.grabGesture(Qt.PinchGesture, Qt.DontStartGestureOnChildren)
        #Configuración
        self.settings = settings

        # Barra de Navegación
        if self.settings.get("MostrarBarraNavegacion", False):
            self.nav_bar = NavigationBar(self.view.page())
            self.mainLayout.addWidget(self.nav_bar, 0, 0)

        self.mainLayout.addWidget(self.view, 1, 0)
        self.view.setUrl(QUrl(self.settings["UrlInicio"]))

        self.channel = QWebChannel(self.view.page())
        self.view.loadFinished.connect(self.on_load_finished)

        # Al empezar una nueva carga, los eventos encolados no deben irse a
        # una pagina que ya no tiene el objeto Ciel.
        self.view.loadStarted.connect(self.on_load_started)

    #Eliminar para producción

    def on_cert_error(self, e):
       print("Error en el certificado")
       e.acceptCertificate()

    #Eliminar para producción


    #Añadir para producción
    '''
    def on_cert_error(self, e):
       print(f"Error SSL: {e.errorDescription()} en {e.url().toString()}")
       return False
    '''
    #Añadir para producción


    def showEvent(self, e):
        super().showEvent(e)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            self.view.setUrl(QUrl(self.settings["UrlInicio"]))
        event.accept()

    def on_load_started(self):
        """
        La pagina se esta recargando: se marcan los eventos como no listos
        para que no se envie JS a un documento sin el objeto Ciel.
        """
        self.loaded = False
        try:
            for api in list(self.apis.values()):
                evento = api.get_event()
                if hasattr(evento, "unloaded"):
                    evento.unloaded()
        except AttributeError:
            # Todavia no se llamo a set_apis()
            pass
        except Exception as e:
            logging.error(str(e))

    def on_load_finished(self, ok):
        """
        Evento de finalización del estado de carga
        Carga las apis al contenedor y cambia la url de la barra de navegación
        """
        print("Web cargada")

        for api in list(self.apis.values()):
            api.get_event().set_page(self.view.page())

        self.load_apis()

        if self.nav_bar:
            self.nav_bar.set_url(self.view.page().url().toString())

        #llamar loaded()
        self.loaded = True
        for api in list(self.apis.values()):
            api.get_event().loaded()

    def load_apis(self):
        """
        Carga las APIs al contenedor web
        """
        api = self.apis

        self.js_bridge = JSBridge(self.view.page(), api)

        self.view.page().setWebChannel(self.channel)
        qwebchannel_js = QFile("://qtwebchannel/qwebchannel.js")
        if qwebchannel_js.open(QFile.ReadOnly):
            source = qwebchannel_js.readAll().data().decode('utf-8')
            self.view.page().runJavaScript(source)
            self.channel.registerObject('external', self.js_bridge)
            self.channel.registerObject('speech', self.apis["speech"])
            self.channel.registerObject('local_media', self.apis['local_media'])
            self.channel.registerObject('credential_manager', self.apis['credential_manager'])
            self.channel.registerObject('system_info', self.apis['system_info'])
            qwebchannel_js.close()
        else:
            logging.error("No se pudo abrir qwebchannel.js")

        self.view.page().runJavaScript(self.js_bridge.parse_api_js())

        # NUEVO: engancha el boton oculto de cierre.
        # Va DESPUES de parse_api_js() para que window.api.app ya exista.
        # runJavaScript respeta el orden de encolado, asi que basta con
        # ponerlo aqui.
        self.enganchar_botones_cierre()

    def enganchar_botones_cierre(self):
        """
        Inyecta el JS que registra funcionesNavegacion.CerrarAplicacion y
        agrega un listener de click al boton oculto de cierre.
        """
        for pantalla, control in BOTONES_CIERRE:
            try:
                self.view.page().runJavaScript(js_cierre(pantalla, control))
                print(f"Cierre: enganche solicitado para {pantalla}/{control}")
            except Exception as e:
                logging.error("No se pudo inyectar el JS de cierre: " + str(e))

    def set_apis(self, apis):
        """
        Establece las APIs en la clase
        :param apis: dict. APIs
        """
        print("Estableciendo APIs en WebViewFrame")

        self.apis = apis
        self.apis["speech"] = SpeechSynthesis()
        self.apis['local_media'] = LocalMedia()
        self.apis['system_info'] = SystemInfo()
        self.apis['credential_manager'] = CredentialManager()
        self.apis["network"] = NetworkController(self.settings["UrlInicio"], self.view, self.apis["speech"])

        # NUEVO: controlador de cierre.
        
        self.apis["app"] = AppController()

    def close_speech_synth(self):
        self.apis["speech"].close_thread()

