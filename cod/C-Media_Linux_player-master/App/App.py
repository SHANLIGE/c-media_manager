# Librerias de GUI - PySide6
#Librerias de GUI - PySide6
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *

#Otras librerias 
import sys
import logging
import os

import traceback, sys





def excepthook(exc_type, exc_value, exc_tb):
    traceback.print_exception(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook
    
argv = sys.argv
debug = "--debug" in sys.argv

if debug:
    #Clases internas - Pruebas 
    #Descomentar para realizar pruebas con python
    from ConfigGUI.TitleBar import *
    from ConfigGUI.MainFrame import MainFrame as Configuration
    from Player import Player as Player
    argv.remove("--debug")
else:
    #Clases internas - Compilación
    #Descomentar para realizar compilacion de la aplicacion
    from App.ConfigGUI.TitleBar import *
    from App.ConfigGUI.MainFrame import MainFrame as Configuration
    from App.Player import Player as Player


log_dir = os.path.expanduser("~/.config/Ciel/C-Media_Player/logs")
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, "log.log")

open(log_file, "a").close()   # crea el archivo si no existe



logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format="%(asctime)s:%(levelname)s:%(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
    force=True
)

#Creacion del archivo de logs

# Descomentarear la siguiente linea, para activar el modo de depuracion, que es accesible desde el navegador: http://localhost:9222
# os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"

#Creacion aplicacion
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-pinch"

root = QApplication()
QCoreApplication.setApplicationName("C-Media Player")




#Creacion del SplashScreen
pixmap = QPixmap(os.path.expanduser('~')+"/.config/Ciel/C-Media_Player/Media/SplashScreen.png")
splash = QSplashScreen(pixmap)
splash.show()
root.processEvents()


#Iniciacion
if len(argv) == 1:
    try:
        player = Player(debug)

        splash.finish(player)
        player.show()

        #imprimir ticket Nulo
        try:
            from printer_test import UniversalESCPrinter
            _p = UniversalESCPrinter(port="/dev/ttyUSB0", baudrate=9600)
            _p.print(["NULL"])
            _p.close()
        except Exception as e:
            logging.warning("Impresión de prueba fallida: " + str(e))


    except Exception as e:
        logging.error(str(e))
        sys.exit()
elif "--config" in argv:
    try:
        config = Configuration()
        splash.finish(config)
        config.show()
    except Exception as e:
        logging.error(str(e))
        sys.exit()
else:
    logging.error("Opcion no permitida")
    sys.exit()
root.lastWindowClosed.connect(root.quit)
#Fin de  la aplicacion
sys.exit(root.exec())




