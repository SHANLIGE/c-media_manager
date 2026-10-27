import logging
import threading
import time

from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *

from ..Event import Event

class Alert(QMessageBox):

    def __init__(self, *__args):
        QMessageBox.__init__(self)
        self.timeout = 0
        self.autoclose = False
        self.currentTime = 0

    def showEvent(self, QShowEvent):
        self.currentTime = 0
        if self.autoclose:
            self.startTimer(1000)

    def timerEvent(self, *args, **kwargs):
        self.currentTime += 1
        if self.currentTime >= self.timeout:
            self.done(0)

    @staticmethod
    def showWithTimeout(message):
        w = Alert()
        w.autoclose = True
        w.timeout = 10
        w.setText(message)
        w.setWindowTitle("Error")
        w.setIcon(QMessageBox.Critical)
        w.setStandardButtons(QMessageBox.NoButton)
        w.exec_()

class Worker(QObject):
    finished = Signal()    

    def run(self):
        for i in range(10):
            time.sleep(1)
        self.finished.emit()

class NetworkController():
    def __init__(self, ruta, webview, speech_synthesis):
        self.webview = webview
        self.ruta = ruta
        self.event = Event("")
        self.speech_synthesis = speech_synthesis

    def disconnected(self):
        logging.error("Desconexión de internet")
        self.speech_synthesis.cancel_speech()
        Alert.showWithTimeout("El Equipo se desconectó de internet")
        
        
    def connected(self):
        self.thread = QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        print("Start thread")
        self.thread.finished.connect(self.reload_view)   
    

    def reload_view(self):
        self.webview.load(QUrl(self.ruta))
        print("Load")
        
        

    def get_event(self):
        return self.event