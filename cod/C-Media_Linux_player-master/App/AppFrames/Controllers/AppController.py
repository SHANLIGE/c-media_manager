import logging

from PySide6.QtCore import QTimer, QObject
from PySide6.QtWidgets import QApplication

try:
    from ..Event import Event
except ImportError:  # ejecucion suelta / pruebas
    from Event import Event


class AppController(QObject):
    """
    Controlador que se expone al player a traves del JSBridge para poder
    cerrar la aplicacion desde un boton de la interfaz web.

    Se registra en WebViewFrame.set_apis() junto a los demas:

        self.apis["app"] = AppController()

    Con eso JSBridge.parse_api_js() genera automaticamente:

        window.api.app.cerrar()
        window.api.app.minimizar()
        window.api.app.esta_activa()

    IMPORTANTE
    ----------
    WebViewFrame.on_load_finished() recorre TODAS las apis y llama
    api.get_event().set_page(...) y api.get_event().loaded(). Por eso este
    controlador tiene su propio Event aunque no emita eventos hacia el
    player: sin get_event() se lanza AttributeError y se rompe la carga de
    las demas APIs.
    """

    def __init__(self, player=None):
        """
        :param player: instancia de Player (ventana principal). Puede ir en
                       None: en ese caso se cierran todas las ventanas de
                       nivel superior, lo que igual dispara
                       Player.closeEvent().
        """
        super().__init__()
        self.player = player
        self.event = Event("App")

    # ------------------------------------------------------------------
    # Requeridos por WebViewFrame.on_load_finished()
    # ------------------------------------------------------------------

    def get_event(self):
        return self.event

    def clear_event(self):
        self.event.clear()

    # ------------------------------------------------------------------
    # Metodos publicos -> quedan expuestos como window.api.app.<nombre>
    # ------------------------------------------------------------------

    def cerrar(self):
        """
        Cierra la aplicacion completa.

        El cierre se agenda con QTimer.singleShot(0) para que ocurra
        despues de que JSBridge responda la promesa al JavaScript. Si se
        cerrara aqui mismo, la pagina se destruye antes de resolver la
        promesa y el JS queda esperando para siempre.
        """
        logging.info("AppController: solicitud de cierre desde el player")
        print(">>> AppController: cerrando aplicacion...")
        QTimer.singleShot(0, self._cerrar_ahora)
        return True

    def minimizar(self):
        """Saca la ventana de pantalla completa y la minimiza."""
        logging.info("AppController: minimizar")
        QTimer.singleShot(0, self._minimizar_ahora)
        return True

    def esta_activa(self):
        """Sirve para comprobar desde el JS que el puente esta vivo."""
        return True

    # ------------------------------------------------------------------
    # Ejecucion real (siempre en el hilo de la interfaz)
    # ------------------------------------------------------------------

    def _cerrar_ahora(self):
        try:
            app = QApplication.instance()

            # Se cierra la ventana principal para que Player.closeEvent()
            # cierre tambien las ventanas secundarias y libere los
            # dispositivos (lector, impresora).
            if self.player is not None:
                self.player.close()
            else:
                for ventana in list(app.topLevelWidgets()):
                    try:
                        ventana.close()
                    except Exception as e:
                        logging.error("AppController cerrando ventana: %s", e)

            app.quit()
        except Exception as e:
            logging.error("AppController._cerrar_ahora: %s", e)
            print(f">>> AppController error al cerrar: {e}")

    def _minimizar_ahora(self):
        try:
            ventanas = []
            if self.player is not None and hasattr(self.player, "ventanas_todas"):
                ventanas = self.player.ventanas_todas()
            else:
                ventanas = list(QApplication.instance().topLevelWidgets())

            for ventana in ventanas:
                try:
                    ventana.showNormal()
                    ventana.showMinimized()
                except Exception as e:
                    logging.error("AppController minimizando: %s", e)
        except Exception as e:
            logging.error("AppController._minimizar_ahora: %s", e)
