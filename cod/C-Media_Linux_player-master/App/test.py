from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtWebEngineWidgets import *
import sys

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow,self).__init__(*args, **kwargs)
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)
        self.browser.setUrl(QUrl("https://www.google.com"))
        #self.browser.setHtml("<html><body><h1>Hello World... Hello World</h1></body></html>")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()  # moved show outside main widget
    sys.exit(app.exec())   #  use app.exec instead of app.exec_