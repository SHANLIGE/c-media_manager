#Librerias de GUI

from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *

from .Controllers.CodeReaders.CodeReaders import get_code_readers

import logging

class CodeReaderFrame(QWidget):
    def __init__(self, name,settings):
        """
        Constructor de clase
        :param settings: Configuracion del lector
        """
        code_readers = get_code_readers()
        self.code_reader = None
        for (r_name,reader) in code_readers.items():
            if r_name + ".dll" == name:
                self.code_reader = reader["import"](settings["PuertoSerial"])

        super().__init__()
        
    def get_code_reader(self):
        """
        Obtiene el lector
        """
        return self.code_reader