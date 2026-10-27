import usb.core #Libreria que permite hacer la conexion con puertos Usb
import logging #Libreria de logging

class UsbConnection():
    """
    clase de coneccion a los dispositivos conectados por puerto USB
    :param id_vendor: int (hex). Id del vendedor del dispositivo conectado.
    :param id_product: int (hex). Id del producto del dispositivo conectado.
    :param timeout: int. Opcional. Limite de tiempo.
    :param ep_in: int. Opcional. Endpoint address lectura.
    :param ep_out: int. Opcional. Endpoint address escritura.
    :param interface: interface del equipo.
    """
    def __init__(self, id_vendor, id_product, timeout = 10000, ep_in = None , ep_out = None, interface = None):
        """
        La funcion es el constructor de la clase UsbConnection.
        :param id_vendor: int (hex). Id del vendedor del dispositivo conectado.
        :param id_product: int (hex). Id del producto del dispositivo conectado.
        :param timeout: int. Opcional. Limite de tiempo.
        :param ep_in: int. Opcional. Endpoint address lectura.
        :param ep_out: int. Opcional. Endpoint address escritura.
        :param interface: interface del equipo.
        """
        self.device = None
        self.id_vendor = id_vendor
        self.id_product =  id_product
        self.interface = interface
        self.ep_in = ep_in
        self.ep_out = ep_out
        self.timeout = timeout
        self.connect()


    def connect(self):
        """
        La funcion realiza la coneccion del objeto con el dispositivo mediante el puerto USB
        :return: str. Error
        """
        self.device = usb.core.find(idVendor = self.id_vendor, idProduct = self.id_product)

        if self.device is None:
            return 1

        ep = self.device[0].interfaces()[0].endpoints() 

        if self.interface == None:
            self.interface =  self.device[0].interfaces()[0].bInterfaceNumber
        
        if self.device.is_kernel_driver_active(self.interface):
            try:
                self.device.detach_kernel_driver(self.interface)
            except Exception as e:
                logging.error(str(e))
                return str(e)

        try:
            self.device.set_configuration()
            self.device.reset()
            if self.ep_out == None:
                self.ep_out = ep[0].bEndpointAddress
            if self.ep_in == None:
                self.ep_in = ep[1].bEndpointAddress
        except Exception as e:
            logging.error(str(e))
            return str(e)

    def write(self, data):
        """
        La funcion escribe un conjunto de bytes en el puerto USB.
        :param data: bytearray. Conjunto de bytes a escribir en el puertp USB.
        """
        if self.device:
            try:
                return self.device.write(self.ep_out, data, timeout = self.timeout)
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
                return self.device.read_line(self.ep_in, self.timeout)
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
                return self.device.read(self.ep_in, self.timeout)
            except Exception as e:
                logging.error(str(e))
                return str(e)