import json
import pathlib #Libreria de control de directorios
from ..Connection.UsbConnection import UsbConnection #Libreria de conexion usb
from ..Connection.SerialConnection import SerialConnection #Libreria de conexion serial
import time #Libreria control de tiempo (hilo principal)
import math #Libreria de matematicas
import cv2 #Libreria de manipulacion de imagenes
from ...Event import Event


class Printer():

    """
    Clase de impresora Universal. Conexion mediante puerto serial y puerto USB.
    :param device: dic. Datos de la impresora
    """
    
    def __init__(self, device):
        
        """
        Constructor de clase
        :param device: dic. Datos de la impresora
        """

        self.__cambios = {}
        self.__version = None
        self._logo_tx = None  # ultima definicion del logo (GS *) enviada por cargar()
        self.event = Event("Impresion")
        self.device = device

        # ── Ancho de papel configurable ──────────────────────────────────────
        # Calcula el ancho imprimible en puntos (203 dpi, margen 4 mm por lado).
        # Se usa en todos los comandos ESC W para evitar que el texto se corte
        # en impresoras SAT con papel de 57 mm.
        papel_mm = int(device.get("AnchoPapel", 80))
        margen_mm = 4
        self._dx_puntos = max(200, int((papel_mm - 2 * margen_mm) * 203 / 25.4))
        self._dx_L = self._dx_puntos & 0xFF
        self._dx_H = (self._dx_puntos >> 8) & 0xFF

  
        self.printer = None

        #Extraer configuración real
        config = device.get("PuertoSerial", {})

       
        try:
            if config.get("NombrePuerto") == "/dev/ttyUSB0":
                    self.printer = UsbConnection(0x4030, 0x6001)
            else:
                    self.printer = SerialConnection(
                        "/dev/ttyUSB0",
                        baudrate=config.get("Baudios", 9600),
                        parity=config.get("Paridad", "N"),
                        stopbits=config.get("BitsParada", 1),
                        bytesize=config.get("BitsDatos", 8)
                    )
        except Exception as e:
                print("Error inicializando impresora:", e)
                self.printer = None

        if self.printer is None:
            self.event.awake("NotificarError", [json.dumps("Impresora No Encontrada")])

        #Constructor
        self.detalle = "Manejo de puerto USB o puerto serial segun selección"
        self.__cambios[self.__version] = self.detalle
        
        

    def getPrinter(self):
        return self.printer

    def get_event(self):
        return self.event

    def clear_event(self):
        self.event.clear()

    #ILibretaInfo Members

    @property
    def Descripcion(self):
        return "Controlador para la impesora termal ESC/POS el cual imprime el tiquete para Digiturno Mega"

    @property
    def Detalle_cambios(self):
        return self.__cambios

    @property
    def Nombre_archivo(self):
        return pathlib.Path(__file__).absolute().name 

    @property
    def Ubicacion(self):
        return str(pathlib.Path().absolute())
    
    @property
    def Version(self):
        return self.__version
    
    #Metodos Impresora
    def imprimir(self, lineas, logo=None):
        """
        Imprime un Ticket
        :param lineas: dict o str. Datos de impresión o texto plano
        :param logo: str. opc. ubicación del logo en formato .bmp
        """

        # Seguridad: validar impresora
        if not self.printer:
            print("No hay impresora física inicializada")
            return

        try:
            print("Generando ticket ESC/POS...")

            texto = ""

            if isinstance(lineas, dict):
                texto = lineas.get("Texto", {}).get("Texto", "")
            else:
                texto = str(lineas)

            lineas_lista = texto.split("\n")

            while len(lineas_lista) < 15:
                lineas_lista.append("")

            tx = self.Ticket([
                lineas_lista[0],
                lineas_lista[1],
                lineas_lista[2],
                lineas_lista[3],
                lineas_lista[4],
                lineas_lista[5],
                lineas_lista[6],
                lineas_lista[7],
                lineas_lista[8],
                lineas_lista[9],
                lineas_lista[10],
                lineas_lista[11],
                lineas_lista[12],
                lineas_lista[13],
                lineas_lista[14],
            ])

            # Reenviar la definicion del logo con CADA ticket.
           
            if logo is not None:
                try:
                    self._logo_tx = self.Logo(logo)
                except Exception as e:
                    print("No se pudo decodificar el logo:", e)
            if self._logo_tx is not None:
                tx = bytearray(self._logo_tx) + tx

           

            if hasattr(self.printer, "write"):
                self.printer.write(tx)
                

                # fuerza envío inmediato si existe flush
                if hasattr(self.printer, "flush"):
                    self.printer.flush()

                # pequeño delay para hardware real ESC/POS
                time.sleep(0.3)

                print("TICKET ENVIADO A IMPRESORA FÍSICA")

            else:
                raise Exception("Driver de impresora inválido")

        except Exception as e:
            print("Error imprimiendo ticket:", e)
            self.event.awake("NotificarError", [json.dumps(str(e))])    

    
    def get_paper(self):     

        """
        Retorna el estado del papel de la impresora
        :return: dic. estado del papel de la impresora
        """
    
        self.printer.write(b'\x1B\x76') #GS V       
        time.sleep(0.2)
        paper_state = self.printer.read()
        response = {}
        if len(paper_state) == 0:
            response["message"] = "La impresora no tiene papel"
        elif paper_state[0] == 3:
            response["message"] = "El papel está por acabarse"
        elif paper_state[0] == 0:
            response["message"] = "La impresora tiene papel"
        return response

    def Letras(self, caracter):
        """
        Soporte a caracteres especiales de utf-8
        :params caracter: bytearray. Informacion de un caracter
        :return: bytearray. Caracter especial en formato imprimible
        """
        array = caracter
        devolver = bytearray()
        k = 0
        while k < len(array):
            if array[k] == 195:
                if array[k+1] == 161:
                    devolver.append(160)    #á
                elif (array[k + 1] == 169):
                    devolver.append(130)    # é
                elif (array[k + 1] == 173):
                    devolver.append(161)    # í
                elif (array[k + 1] == 179): 
                    devolver.append(162)    # ó
                elif (array[k + 1] == 186): 
                    devolver.append(163)    # ú
                elif (array[k + 1] == 177):
                    devolver.append(164)    # ñ
                elif (array[k + 1] == 145):
                    devolver.append(165)    # Ñ
                elif (array[k + 1] == 129):
                    devolver.append(181)    # Á
                elif (array[k + 1] == 137): 
                    devolver.append(144)    # É
                elif (array[k + 1] == 141): 
                    devolver.append(214)    # Í
                elif (array[k + 1] == 147):
                    devolver.append(224)    # Ó
                elif (array[k + 1] == 154): 
                    devolver.append(233)    # Ú
                k+=1
            elif array[k] == 194:
                if (array[k + 1] == 191):
                    devolver.append(168)    # ¿
                if (array[k + 1] == 161):
                    devolver.append(173)    # ¡
                k+=1
            else:
                devolver.append(array[k])
            k+=1
        return devolver
            
    def cargar(self, logo):
        
        """
        Carga un logo en la impresora
        :param logo: str. ubicacion del logo a ser cargado
        :return: bytearray. informacion del logo
        """
        
   
        Tx = self.Logo(logo)
        self._logo_tx = Tx  # se guarda para reenviarla junto con cada ticket
        self.printer.write(Tx) 
        return Tx

    def _alto_area(self, lineas, nempty):
        """
        Calcula el alto del area de impresion segun lineas presentes.
        """
        _ALTO_BASE = 1040   # alto con TODAS las lineas presentes (el QR entra completo)
        _PASO = 40          # dots que se acortan por cada linea opcional ausente

        alto = _ALTO_BASE
        opcionales = (2, 3, 4, 5, 7, 8, 9, 11, 12, 13)  # indices de lineas opcionales
        for i in opcionales:
            if i < len(lineas) and lineas[i] in nempty:
                alto -= _PASO

        alto = max(400, alto)  # nunca por debajo de un minimo razonable
        return (alto & 0xFF, (alto >> 8) & 0xFF)

    def Ticket(self, lineas):

        """
        Crea el formato del Ticket
        :param lineas: str. Lineas a imprimir separadas por un salto de linea '\\n'
        :return: bytearray. Ticket imprimible
        """

        tamano4 = "small"
        tamano5 = "small"
        tamano6 = "small"

        pequeno = "[@TF:P@]"
        mediano = "[@TF:M@]"
        grande = "[@TF:G@]"

        interlineado = (0x30,0x30,0x30) # 0:  interlineado 4, 1:  interlineado 5, 2:  interlineado 6 

        tx = bytearray()
        tamano = len(lineas)
        if tamano > 5 :
            if lineas[3].startswith(pequeno):
                tamano4 = "small"
                lineas[3]= lineas[3][8:]
            elif lineas[3].startswith(mediano):
                tamano4 = "medium"
                lineas[3]= lineas[3][8:]
            elif lineas[3].startswith(grande):
                tamano4 = "big"
                lineas[3]= lineas[3][8:]
            else:
                tamano4 = "small"
            
            if lineas[4].startswith(pequeno):
                tamano5 = "small"
                lineas[4]= lineas[4][8:]
            elif lineas[4].startswith(mediano):
                tamano5 = "medium"
                lineas[4]= lineas[4][8:]
            elif lineas[4].startswith(grande):
                tamano5 = "big"
                lineas[4]= lineas[4][8:]
            else:
                tamano5 = "small"
            if lineas[5].startswith(pequeno):
                tamano6 = "small"
                lineas[5]= lineas[5][8:]
            elif lineas[5].startswith(mediano):
                tamano6 = "medium"
                lineas[5]= lineas[5][8:]
            elif lineas[5].startswith(grande):
                tamano6 = "big"
                lineas[5]= lineas[5][8:]
            else:
                tamano6 = "small"

        
        tx.append(0x1B)
        tx.append(0x4C)

        nempty = (None, '')

        # Alto dinamico del area (2 bytes finales de ESC W) segun lineas presentes
        _ay_L, _ay_H = self._alto_area(lineas, nempty)
        
        if tamano > 5:
            if lineas[4] not in nempty or lineas[5] not in nempty:
                if tamano > 13:
                    #Verifica que las líneas de texto y código qr existan
                    if lineas[13] not in nempty or lineas[14] not in nempty:
                        if (tamano4 == "big" and tamano5 == "big") or (tamano4 == "big" and tamano6 == "big") or (tamano5 == "big" and tamano6 == "big"):
                            tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H,0x40, 0x05]) #seleccion area de impresion
                            if not(tamano5 == "big"):
                                interlineado = (0x40, 0x60, 0x60)
                            elif not(tamano6 == "big"):
                                interlineado = (0x60, 0x40, 0x60)
                            else:
                                interlineado = (0x60, 0x60, 0x60)
                        elif tamano4 == "big" or tamano5 == "big" or tamano6 == "big":
                            tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H,0x10, 0x05]) #seleccion area de impresion
                            if tamano4 == "big":
                                interlineado = (0x40, 0x40, 0x30)
                            elif tamano5 != "big":
                                interlineado = (0x60, 0x40, 0x30)
                            else:
                                interlineado = (0x40, 0x60, 0x30)
                        else:
                            tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H,_ay_L, _ay_H]) #seleccion area de impresion (alto dinamico)
                            interlineado = (0x30, 0x30, 0x30)
                    #No existen lineas configuradas para qr
                    else:
                        if (tamano4 == "big" and tamano5 == "big") or (tamano4 == "big" and tamano6 == "big") or (tamano6 == "big" and tamano5 == "big"):
                            tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H,0x8E, 0x03]) #seleccion area de impresion
                            if not (tamano5 == "big"):
                                interlineado = (0x40, 0x60, 0x60)
                            elif not (tamano6 == "big"):
                                interlineado = (0x60, 0x40, 0x60)
                            else:
                                interlineado = (0x60, 0x60, 0x60)
                        elif tamano4 == "big" or tamano5 == "big" or tamano6 == "big":
                            tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H,0x5E, 0x03]) #seleccion area de impresion
                            if tamano4 == "big":
                                interlineado = (0x40, 0x40, 0x30)
                            elif tamano5 == "big":
                                interlineado = (0x60, 0x40, 0x30)
                            else:
                                interlineado = (0x40, 0x60, 0x30)
                        else:
                            tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H,0x3E, 0x03]) #seleccion area de impresion
                            interlineado = (0x30, 0x30, 0x30)
                #llegan menos de 13 lineas            
                else:
                    if (tamano4 == "big" and tamano5 == "big") or (tamano4 == "big" and tamano6 == "big") or (tamano6 == "big" and tamano5 == "big"):
                        tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H,0x8E, 0x03]) #seleccion area de impresion
                        if not (tamano5 == "big"):
                            interlineado = (0x40, 0x60, 0x60)
                        elif not (tamano6 == "big"):
                            interlineado = (0x60, 0x40, 0x60)
                        else:
                            interlineado = (0x60, 0x60, 0x60)
                    elif tamano4 == "big" or tamano5 == "big" or tamano6 == "big":
                        tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H,0x5E, 0x03]) #seleccion area de impresion
                        if tamano4 == "big":
                            interlineado = (0x40, 0x40, 0x30)
                        elif tamano5 == "big":
                            interlineado = (0x60, 0x40, 0x30)
                        else:
                            interlineado = (0x40, 0x60, 0x30)
                    else:
                        tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H,0x3E, 0x03]) #seleccion area de impresion
                        interlineado = (0x30, 0x30, 0x30)

            #las lineas 4 y 5 estan vacias
            else:
                if tamano > 13:
                    #Verifica que las lineas de text y codigo qr existan
                    if lineas[13] not in nempty or lineas[14] not in nempty:
                        tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H,_ay_L, _ay_H]) #seleccion area de impresion (alto dinamico)
                        interlineado = (0x30, 0x30, 0x30)
                    #No existeb las lineas configuradas para qr
                    else:
                        tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H,0xBE, 0x02]) #seleccion area de impresion
                        interlineado = (0x30, 0x30, 0x30)
                #llegan menos de 13 lineas
                else:
                    tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H,0xBE, 0x02]) #seleccion area de impresion
                    interlineado = (0x30, 0x30, 0x30)
        else:
            tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H,0x9E, 0x02]) #seleccion area de impresion
            interlineado = (0x30, 0x30, 0x30)
        tx += bytearray([0x1B, 0x54, 0x02]) #Direccion de impresion de derecha izquierda
        tx += bytearray([0x1D, 0x5C, 0x08, 0x02]) #Posicion vertical relativa (520 dots: 120px mas abajo que los 400 anteriores)
        tx += bytearray([0x1D, 0x2F, 0x33]) #Imprimir Logo cuádruple
        if tamano > 5:
            # Verifica que la linea 5 o 6 tenga texto que imprimir
            if lineas[5] not in nempty or lineas[4] not in nempty:
                if tamano > 13:
                    # Verifica que las líneas de texto y código qr existan
                    if lineas[13] not in nempty or lineas[14] not in nempty:
                        if (tamano4 == "big" and tamano5 == "big") or (tamano4 == "big" and tamano6 == "big") or (tamano6 == "big" and tamano5 == "big"):
                            tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H, 0x40, 0x05]) # seleccionar area de impresion
                        elif tamano4 == "big" or tamano5 == "big" or tamano6 == "big":
                            tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H, 0x10, 0x05]) # seleccionar area de impresion
                        else:
                            tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H, _ay_L, _ay_H]) # seleccionar area de impresion (alto dinamico)
                        # No existen líneas configuradas para qr
                    else:
                
                        if (tamano4 == "big" and tamano5 == "big") or (tamano4 == "big" and tamano6 == "big") or (tamano6 == "big" and tamano5 == "big"):
                            tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H, 0x8E, 0x03]) # seleccionar area de impresion
                        elif tamano4 == "big" or tamano5 == "big" or tamano6 == "big":
                            tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H, 0x5E, 0x03]) # seleccionar area de impresion
                        else:
                            tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H, 0x3E, 0x03]) # seleccionar area de impresion
                # Llegan menos de 13 líneas
                else:
                    if (tamano4 == "big" and tamano5 == "big") or (tamano4 == "big" and tamano6 == "big") or (tamano6 == "big" and tamano5 == "big"):
                        tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H, 0x8E, 0x03]) # seleccionar area de impresion
                    elif tamano4 == "big" or tamano5 == "big" or tamano6 == "big":
                        tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H, 0x5E, 0x03]) # seleccionar area de impresion
                    else:
                        tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H, 0x3E, 0x03]) # seleccionar area de impresion
            # Las líneas 4 y 5 están vacias
            else:
                if tamano > 13:
                    # Verifica que las líneas de texto y código qr existan
                    if lineas[13] not in nempty or lineas[14] not in nempty:
                        tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H, _ay_L, _ay_H]) # seleccionar area de impresion (alto dinamico)
                    # No existen líneas configuradas para qr
                    else:
                        tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H, 0xBE, 0x02]) # seleccionar area de impresion
                
                # Llegan menos de 13 líneas
                else:
                    tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H, 0xBE, 0x02]) # seleccionar area de impresion
        else:
            tx += bytearray([0x1B, 0x57, 0x00, 0x00, 0x00, 0x00, self._dx_L, self._dx_H, 0x9E, 0x02]) # seleccionar area de impresion

        tx += bytearray([0x1B, 0x74, 0x02]) # Configura tabla de caracteres multilenguaje para imprimir tildes en las mayusculas (Á É Í Ó Ú)
        tx += bytearray([0x1B, 0x54, 0x02]) # direccion de impresion de derecha a izquierda
        tx += bytearray([0x1B, 0x32]) # espacio entre lineas
        tx += bytearray([0x1B, 0x21, 0x00]) # seleccionar modo de impresion
        tx += bytearray([0x1B, 0x44, 0x13, 0x00]) # tabulaciones horizontales
        tx += bytearray([0x1D, 0x5C, 0x28, 0x00]) # posicion vertical relativa +40 dots: separa la linea 1 del borde inferior del area para que su mitad no se recorte
        tx += bytearray([0x1B, 0x33, 0x48]) # interlineado entre linea 1 y 2 0x48=72 dots: supera los 48 del glifo doble para que la linea 2 no se encime con la linea 1
        tx += bytearray([0x1B, 0x21, 0x30]) # seleccionar modo de impresion


        #region linea 1
        if tamano > 1:
            if lineas[0] not in nempty:
                line1 = bytearray(lineas[0].encode('utf-8'))
                mientras = self.Letras(line1)
                for k in range(len(mientras)):
                    tx.append(mientras[k])
            tx += bytearray([0x0A]) # salto de linea (con interlineado amplio da el espacio entre linea 1 y 2)
    
        #endregion linea 1
        #region linea 2
        if tamano > 1:
            if lineas[1] not in nempty:
                line2 = bytearray(lineas[1].encode('utf-8'))
                mientras = self.Letras(line2)
                for k in range(len(mientras)):
                    tx.append(mientras[k])
        #endregion linea 2
      
        tx += bytearray([0x1B, 0x33, 0x28]) #selecionar espaciado 
        tx += bytearray([0x1B,0x21,0x01,0x09])# selecionar modo de impresion

        tx += bytearray([0x0A, 0x09])

        #region linea 3
        if (tamano > 2):
            if lineas[2] not in nempty:
                line3 = bytearray(lineas[2].encode('utf-8'))

                mientras = self.Letras(line3)

                for k in range(len(mientras)):
                    tx.append(mientras[k])

        #endregion linea 3
        tx += bytearray([0x0A, 0x09]) # salto de linea
        tx += bytearray([0x1D, 0x5C, 0x37, 0x00]) # posicion vertical relativa: 55 dots (eje invertido con ESC T 2, subir el valor sube la linea 7: 10px arriba de los 45 anteriores)
    
        #region linea 7
        if tamano > 6:
        
            if lineas[6] not in nempty:
            

                line7 = bytearray(lineas[6].encode('utf-8'))
                
                mientras = self.Letras(line7)
                for k in range(len(mientras)):
                    tx.append(mientras[k])
        #endregion linea 7
        tx += bytearray([0x1D, 0x5C, 0xC9, 0xFF]) # compensa los 55px: solo se mueve la linea 7, el resto no se corre
        tx += bytearray([0x0A, 0x09])
        tx += bytearray([0x0A, 0x0A]) #salto de linea
        tx += bytearray([0x0A]) # salto de linea (SAT)
        tx += bytearray([0x0A]) # salto de linea (SAT)
        tx += bytearray([0x1B, 0x32]) # espacio entre lineas
        tx += bytearray([0x1D, 0x5C, 0x38, 0x00]) # posicion vertical relativa 56 dots: sube el bloque turno + lineas 13,4,6,15 los 72 dots que se acorto el turno al des-estirarlo
        tx += bytearray([0x1D, 0x21, 0x33]) # Tamaño de letra 4*4 (antes 4*7): mismo multiplicador ancho/alto para que no salga estirado verticalmente
        tx += bytearray ([0x09])
        
        
        #region turno
        
        if tamano > 10:
            if lineas[10] not in nempty:
                mostrar = bytearray(lineas[10].encode('utf-8'))

                mientras1 = self.Letras(mostrar)
                for k in range(len(mientras1)): # número del turno
                    tx.append(mientras1[k])
        #endregion turno
        
        tx += bytearray([0x1B, 0x21, 0x08, 0x09]) # seleccionar modo de impresion 

    

        #region servicio
        if tamano > 11:
        
            if lineas[11] not in nempty:
                tecla = bytearray(lineas[11].encode('utf-8'))
                mientras2 = self.Letras(tecla)
                for k in range(len(mientras2)):
                    tx.append(mientras2[k])
        #endregion servicio

        tx += bytearray([0x0A]) # salto de linea
        tx += bytearray([0x1B, 0x21, 0x01, 0x09]) # seleccionar modo de impresion 
    
        #region hora

        if tamano > 12:
            if lineas[12] not in nempty:
                    # hora = _ticket1.Date.ToString(_printerTicketBasicInfo.DateFormat).Length;
                    #fecha1 = encode.GetBytes(_ticket1.Date.ToString(_printerTicketBasicInfo.DateFormat));
                fecha1 = bytearray(lineas[12].encode('utf-8'))

                mientras3 = self.Letras(fecha1)
                for k in range(len(mientras3)):
                    tx.append(mientras3[k])
        #endregion hora

            #tx[i++] = 0x1B; tx[i++] = 0x33; tx[i++] = 0x5B;  # seleccionar espaciado 
        tx += bytearray([0x0A]) # salto de linea
        tx += bytearray([0x1B, 0x33, interlineado[0]]) # seleccionar espaciado
    

        if tamano4 == "big":
            tx += bytearray([0x1B, 0x21, 0x30]) # seleccionar modo de impresion letra pequeña
    
        elif tamano4 == "medium":
            tx += bytearray([0x1B, 0x21, 0x08]) # seleccionar modo de impresion letra pequeña
    
        else:
            tx += bytearray([0x1B, 0x21, 0x01]) # seleccionar modo de impresion letra pequeña
    
        #region linea 4
        if tamano > 3:
            if lineas[3] not in nempty:

                line4 = bytearray(lineas[3].encode('utf-8'))

                mientras = self.Letras(line4)
                for k in range(len(mientras)):
                    tx.append(mientras[k])
        #endregion linea 4
        
        #region linea 5
        if tamano > 4:
            if lineas[4] not in nempty:
                tx += bytearray([0x0A])
                tx += bytearray([0x1B, 0x33, interlineado[1]]) # seleccionar modo de impresion letra pequeña
                if tamano5 == "big":
                    tx += bytearray([0x1B, 0x21, 0x30]) # seleccionar modo de impresion letra pequeña
                    
                elif tamano5 == "medium":
                    tx += bytearray([0x1B, 0x21, 0x08]) # seleccionar modo de impresion letra pequeña
                    
                else:
                    tx += bytearray([0x1B, 0x21, 0x01]) # seleccionar modo de impresion letra pequeña
                    
                line5 = bytearray(lineas[4].encode('utf-8'))
                mientras = self.Letras(line5)
                for k in range(len(mientras)):
                    tx.append(mientras[k])
        #endregion linea 5
        
        #region linea 6
        if tamano > 5:
            if lineas[5] not in nempty:

                tx += bytearray([0x0A])# salto de linea
                tx += bytearray([0x1B, 0x33 ,interlineado[2]]) # seleccionar espaciado
                
                if tamano6 == "big":
                    tx += bytearray([0x1B, 0x21 ,0x30]) # seleccionar modo de impresion letra pequeña
                    
                elif tamano6 == "medium":
                    tx += bytearray([0x1B, 0x21 ,0x08]) # seleccionar modo de impresion letra pequeña
                    
                else:
                    tx += bytearray([0x1B, 0x21 ,0x01]) # seleccionar modo de impresion letra pequeña
                    

                line6 = bytearray(lineas[5].encode('utf-8'))
                
                mientras = self.Letras(line6)
                for k in range(len(mientras)):
                    tx.append(mientras[k])
              
                
        #endregion linea 6

        tx += bytearray([0x1B, 0x33, 0x5B]) # seleccionar espaciado
    
        #region linea 14 (texto qr)
        if tamano > 13:
            if lineas[13] not in nempty:
                tx += bytearray([0x1B, 0x33, 0x28]) # seleccionar espaciado
                tx += bytearray([0x1B, 0x21, 0x01]) # seleccionar modo de impresion
               
                

                line13 = bytearray(lineas[13].encode('utf-8'))

                mientras = self.Letras(line13)
                for k in range(len(mientras)):
                    tx.append(mientras[k])
        #endregion linea 14 (texto qr)

        #region linea 15 (código qr)

        if tamano > 14:
            if lineas[14] not in nempty:
                tx += bytearray([0x0A]) # salto de linea

                tx += bytearray([0x1B, 0x21, 0x01, 0x09]) # seleccionar modo de impresion

                # Convertir los datos del QR ANTES de calcular la longitud del payload.
                # Letras() puede cambiar el tamaño si hay caracteres especiales, por lo
                # que el header GS(k debe usar len(datos_qr), no len(lineas[14]).
                line14 = bytearray(lineas[14].encode('utf-8'))
                datos_qr = self.Letras(line14)
                payload_len = len(datos_qr) + 3  # +3 por cn, fn, m
                qr_pL = payload_len & 0xFF
                qr_pH = (payload_len >> 8) & 0xFF

                # GS ( k – Tamaño de modulo del QR (fn 67): 3 puntos por modulo
        
                tx += bytearray([0x1D, 0x28, 0x6B, 0x03, 0x00, 0x31, 0x43, 0x03])
                # GS ( k – Error correction level: M (15%)
                tx += bytearray([0x1D, 0x28, 0x6B, 0x03, 0x00, 0x31, 0x45, 0x31])
                # GS ( k – Store symbol data
                tx += bytearray([0x1D, 0x28, 0x6B, qr_pL, qr_pH, 0x31, 0x50, 0x30])
                for k in range(len(datos_qr)):
                    tx.append(datos_qr[k])

                # GS ( k – Print symbol
                tx += bytearray([0x1D, 0x28, 0x6B, 0x03, 0x00, 0x31, 0x51, 0x30])
              

        #endregion linea 15 (código qr)
        tx += bytearray([0x1B, 0x21, 0x01]) # seleccionar modo de impresion
        tx += bytearray([0x1B, 0x44, 0x0D, 0x00]) # tabulaciones horizontales
        tx += bytearray([0x1B, 0x54, 0x01]) # direccion de impresion de derecha a izquierda
        tx += bytearray([0x1B, 0x33, 0x18]) # seleccionar espaciado
        tx += bytearray([0x1B, 0x21, 0x00, 0x09]) # seleccionar modo de impresion 
        tx += bytearray([0x1D, 0x5C, 0x14, 0x00]) # corrimiento horizontal del bloque lineas 8/9/10 (20px: se baja el valor para ALEJARLAS del turno y darles mas espacio)
        tx += bytearray([0x1B, 0x5C, 0x30, 0x00]) # ESC \ +48 dots: con ESC T 1 este es el eje vertical fisico, baja las lineas 8/9/10 al nivel de la linea 7
        
        #region linea 8
        if tamano > 7:
        
            if lineas[7] not in nempty:
            
                # linea8 = _printerTicketBasicInfo.Product + " " + _printerTicketBasicInfo.Company;
                linea8 = lineas[7]
                
                line8 = bytearray(linea8.encode('utf-8'))

                mientras4 = self.Letras(line8)
                for k in range(len(mientras4)):
                    tx.append(mientras4[k])

        #endregion linea 8
      
        tx += bytearray([0x0A, 0x09]) # salto de linea
        tx += bytearray([0x1B, 0x5C, 0x30, 0x00]) # ESC \ +48: reaplica el offset vertical a la linea 9 (el salto de linea lo reinicio)

        #region linea 9
        if tamano > 8:
        
            if lineas[8] not in nempty:
                    # linea9 = _printerTicketBasicInfo.Telephone + " " + _printerTicketBasicInfo.City;
                linea9 = lineas[8]
                line9 = bytearray(linea9.encode('utf-8'))

                mientras5 = self.Letras(line9)
                for k in range(len(mientras5)):
                    tx.append(mientras5[k])


        #endregion linea 9
        tx += bytearray([0x0A, 0x09]) # salto de linea
        tx += bytearray([0x1B, 0x5C, 0x30, 0x00]) # ESC \ +48: reaplica el offset vertical a la linea 10 (el salto de linea lo reinicio)
    
        
        #region linea 10
        if tamano > 9:
        
            if lineas[9] not in nempty:
                    # linea10 = _printerTicketBasicInfo.Country;
                linea10 = lineas[9]
                line10 = bytearray(linea10.encode('utf-8'))

                mientras6 = self.Letras(line10)
                for k in range(len(mientras6)):
                    tx.append( mientras6[k])

        #endregion linea10
        
        tx += bytearray([0x0C])
        tx += bytearray([0x1B, 0x33, 16])
        tx += bytearray([0x0A]) # espacio al inicio del papel para evitar cortes de texto
        tx += bytearray([0x1D, 0x56, 0x01]) # cortar el papel
    
        return tx
    
    def Logo(self, bitmap):

        """
        Decodifica el Logo para la impresora
        :param bitmap: str. ubicacion del logo en formato .bmp
        :return: bytearray. i
        """
        
        array = bytearray()
        img =  cv2.imread(bitmap)
        height, width = img.shape[0:2]
        
        if width > 124:
            r = 124/width
            img = cv2.resize(img,(124, int(height*r)), interpolation = cv2.INTER_AREA)
            height, width = img.shape[0:2]
        if height > 88:
            r = 88/height
            img = cv2.resize(img, (int(width*r), 88), interpolation = cv2.INTER_AREA)
            height, width = img.shape[0:2]
        
        for row in range(height):
            for col in range(width):
                if all(img[row,col] != [255,255,255]):
                    img[row,col,0] = 0
                    img[row,col,1] = 0
                    img[row,col,2] = 0

        x = math.ceil(width / 8)   # bytes horizontales -> x*8 columnas de puntos
        y = math.ceil(height / 8)  # bytes verticales

        array.append(0x1D) #GS
        array.append(0x2A) #*
        array.append(x)
        array.append(y)

        # GS 
        for posX in range(x * 8):
            for byte_y in range(y):
                pixels = 0
                for cont in range(7, -1, -1):
                    posY = byte_y * 8 + (7 - cont)
                    if posX < width and posY < height:
                        f = img[posY, posX]
                        if f[2] == 0:
                            pixels += math.trunc(2**cont)
                array.append(pixels)

        return array