#Librerias de GUI 
import logging
import os

from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *

from .Controllers.Printers.Printers import get_impresoras



print("Tomando impresora")

class PrinterFrame(QWidget):
    """
    Clase de Frame de la impresora
    :param settings: Configuracion de la impresora
    """
    def __init__(self, settings):
    
        """
        Constructor de clase
        :param settings: Configuracion de la impresora
        """
        impresoras = get_impresoras()
        self.printer = None 
        try:
            for impresora in impresoras.values():
                if impresora["value"] == settings["TipoImpresora"]:
                    self.printer = impresora["import"](settings) 
                    break
        except Exception as e:
            print(e)
            logging.error ("No existe controlador para la impresora seleccionada")
        
        
        if self.printer.printer and os.path.exists (settings["RutaLogo"]["Path"]):
            self.printer.cargar (settings["RutaLogo"]["Path"])
        super().__init__()
        
    def get_printer(self):
        """
        Obtiene la impresora
        """
        return self.printer 

       