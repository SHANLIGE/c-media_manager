from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QCheckBox, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget, QWidget, QFrame
from .CodeReaderTabFrame import CodeReaderTabFrame
from .GeneralTabFrame import GeneralTabFrame
from .WebTabFrame import WebTabFrame
from .PrinterTabFrame import PrinterTabFrame
from .TitleBar import TitleBar
from .PerifericsTabFrame import PerifericosTabFrame
import os



COLOR_NARANJA = "#f99f04"
COLOR_NARANJA_HOVER = "#ff8c00"
COLOR_NARANJA_PRESSED = "#f99f04"



class MainFrame(QWidget):
    """
    Clase de pantalla principal (configuracion)
    """
    def __init__(self):
        """
        Constructor de clase
        """
        super().__init__()
        icon = QIcon()
        path = os.path.expanduser('~')+"/.config/Ciel/C-Media_Player/Media/Logo-CMedia_C.png"
        icon.addFile(path, QSize(), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)
        #Nombre de la Aplicacionclass MainWindow(QMainWindow):

        
        self.setWindowTitle("C-Media Player Lx · Configuración")
        self.setMinimumSize(800, 500)
        self.setMaximumSize(800, 500)
        QCoreApplication.setApplicationName("C-Media Player Lx · Configuration")


        self.setWindowFlags(Qt.FramelessWindowHint)
        
        self.TitleBar = TitleBar(self)
        self.TitleBar.setGeometry(0, 0, self.width(), 36)
        self.TitleBar.show()
        self.TitleBar.raise_()
      

        #Background color
        bg = QPalette()
        bg.setColor(QPalette.Window, "#dae7ef") #AR
        self.setAutoFillBackground(True)
        self.setPalette(bg)

        self.setStyleSheet(f""" 
            QWidget {{
                color: #58666c;
                font-family: "Segoe UI", "Noto Sans", sans-serif;
                font-size: 13px; 
                background-color: #ffffff;
            }}    
          
            QTabWidget::pane {{
                border: 1.2px solid #e4e6e9;
            }} 
            QTabBar::tab {{
                background-color: #ffffff;
                padding: 8px 20px;
                font-size: 14px;
            
            }}
            QTabBar::tab:selected {{
                font-weight: bold;
                color: {COLOR_NARANJA};
                border-bottom: 2.5px solid {COLOR_NARANJA};
            }}           
        """)
        

        #Set Layout
        self.mainLayout = QGridLayout()
        self.mainLayout.setContentsMargins(15, 36, 15, 15)
        self.setLayout(self.mainLayout)
        

        #TabFrame
        self.tabWidget = QTabWidget(self)
        self.generalTab = GeneralTabFrame()
        self.webTab = WebTabFrame()
        self.periferics = PerifericosTabFrame()
    

        self.tabWidget.addTab(self.generalTab, QIcon(os.path.expanduser("~") + "/.config/Ciel/C-Media_Player/images/settings_24dp_F99F04_FILL0_wght400_GRAD-25_opsz40.svg"),
            "General")
        

        self.tabWidget.addTab(self.webTab, QIcon(os.path.expanduser("~") + "/.config/Ciel/C-Media_Player/images/language_24dp_F99F04_FILL0_wght400_GRAD0_opsz24.svg"),
            "Web")
        
        self.tabWidget.addTab(self.periferics, QIcon(os.path.expanduser("~") + "/.config/Ciel/C-Media_Player/images/periferics_24dp_F99F04_FILL0_wght400_GRAD-25_opsz24.svg"),
            "Periféricos")
        
     
        
        self.mainLayout.addWidget(self.tabWidget)
        
        palette = QPalette() # PANTONE
        palette.setColor(QPalette.Window, "#ffffff") 
        palette.setColor(QPalette.WindowText, Qt.black)
        palette.setColor(QPalette.Base, Qt.white)
        palette.setColor(QPalette.AlternateBase, QColor(218, 231, 239))
        palette.setColor(QPalette.ToolTipBase, Qt.black)
        palette.setColor(QPalette.ToolTipText, Qt.black)
        palette.setColor(QPalette.Text, "#58666c")
        palette.setColor(QPalette.Button, "#ffffff")
        palette.setColor(QPalette.ButtonText, Qt.black)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, "#2a82da")
        palette.setColor(QPalette.Highlight, "#2a82da")
        palette.setColor(QPalette.HighlightedText, Qt.black)
        palette.setColor(QPalette.Disabled, QPalette.Base, QColor(44, 44, 45)) 
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(88, 102, 108))
        palette.setColor(QPalette.Disabled, QPalette.Button, QColor(193, 196, 199))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(88, 89, 91))
        #palette.setColor(QPalette.Disabled, QPalette.Window, QColor(49, 49, 49))
        #palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(57, 57, 57))
        self.setPalette(palette)