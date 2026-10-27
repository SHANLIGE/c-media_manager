import serial #libreria que permite la conexion con puerto serial
import logging #libreria de logging
from serial.serialutil import PARITY_NAMES #Libreria con los nombres de paridad
import serial.tools.list_ports

class SerialConnection():
    """
    clase de coneccion a los dispositivos conectados por puerto serial.
    :param port: string. Ubicacion del archivo del puerto
    :param timeout: int. Opcional. Limite de tiempo.
    :param baudrate: tasa de baudios.
    """
    def __init__(self, port, timeout = 2, baudrate = 9600, bytesize=8, parity=0,stopbits = 1 ):
        """
        La funcion es el constructor de la clase UsbConnection.
        :param port: string. Ubicacion del archivo del puerto
        :param timeout: int. Opcional. Limite de tiempo.
        :param baudrate: tasa de baudios.
        """
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = list(PARITY_NAMES.keys())[parity] 
        self.stopbits = stopbits
        self.timeout = timeout

        self.device = None

        self.connect()



    def connect(self):
        """
        La funcion realiza la coneccion del objeto con el dispositivo mediante el puerto USB
        :return: str. Error
        """
        try:
            if "/dev/" not in self.port:
                ports = serial.tools.list_ports.comports()
                for port, desc, hwid in sorted(ports):
                    if self.port in hwid:
                        self.port = port
            self.device = serial.Serial(port=self.port, baudrate=self.baudrate, bytesize=self.bytesize, parity=self.parity, stopbits=self.stopbits, timeout=self.timeout)
        except Exception as e:
            self.device = None
            logging.error(str(e))
            #raise str(e)

    def write(self, data):
        """
        La funcion escribe un conjunto de bytes en el puerto USB.
        :param data: bytearray. Conjunto de bytes a escribir en el puertp USB.
        """
        if self.device:
            try:
                self.device.write(data)
            except Exception as e:
                logging.error(str(e))
                return str(e)

    def read(self):
        """
        La funcion lee una cantidad de bytes del puerto USB.
        :return: array. Conjunto de bytes con informacion leidos en el puerto USB. 
        """
        if self.device:
            try:
                return self.device.read()
            except Exception as e:
                logging.error(str(e))
                return str(e)

    def read_line(self):
        """
        La funcion lee una cantidad de bytes del puerto USB.
        :return: array. Conjunto de bytes con informacion leidos en el puerto USB. 
        """
        if self.device:
            try:
                return self.device.readline()
            except Exception as e:
                logging.error(str(e))
                return str(e)

    def disconnect(self):
        """
        La funcion cierra la conexion con el puerto serial
        """
        if self.device:
            try:
                self.device.close()
            except Exception as e:
                logging.error(str(e))
                return str(e)
