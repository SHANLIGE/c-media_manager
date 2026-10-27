from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *

#Clases externass
from .WebViewFrame import WebViewFrame
from .PrinterFrame import PrinterFrame
from .CodeReaderFrame import CodeReaderFrame


class MainFrame(QWidget):
    """
    Clase de Frame Principal
    :param controllers: list. Controladores de la aplicacion
    """
    def __init__(self, controllers):
        """
        Clase de Frame Principal
        :param controllers: list. Controladores de la aplicacion
        """
        super().__init__()
        self.webview_frame = None
        self.printer_frame = None
        self.code_reader_frame = None
        self.controllers = controllers


        self.apis = {}

        #Set Layout
        self.mainLayout = QGridLayout()
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.mainLayout)

        #Controladores
        for controller in self.controllers:

            #BrowserFrame
            if "Control.NavegadorWebChrome.dll" in controller["NombreArchivo"]:
                self.webview_frame = WebViewFrame(settings = controller["ObjetoBase"])

            #PrinterFrame
            elif "Control.Impresion.dll" in controller["NombreArchivo"]:
                self.printer_frame = PrinterFrame(controller["ObjetoBase"])
                self.apis["printer"] = self.printer_frame.get_printer()

            #CodeReaderFrame
            elif "Control.Captura.CodigoBarras.Omnidireccional" in controller["NombreArchivo"]:
                
                self.code_reader_frame = CodeReaderFrame(controller["NombreArchivo"][45:],controller["ObjetoBase"])
                self.apis["code_reader"] = self.code_reader_frame.get_code_reader()

        self.webview_frame.set_apis(self.apis)

        self.mainLayout.addWidget(self.webview_frame)
        


    def closeEvent(self):
        """
        Evento de cierre de la aplicacion
        """
        if self.code_reader_frame:
            self.code_reader_frame.get_code_reader().disconnect()
            self.webview_frame.close_speech_synth()
