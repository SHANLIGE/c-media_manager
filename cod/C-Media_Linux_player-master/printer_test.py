import serial
import time


class UniversalESCPrinter:

    def __init__(self, port="/dev/ttyUSB0", baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.printer = None

        self.connect()

    def connect(self):
        try:
            self.printer = serial.Serial(
                self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity=serial.PARITY_NONE,
                stopbits=1,
                timeout=1
            )

            time.sleep(0.2)

            # Reset impresora
            self.printer.write(b'\x1B\x40')

            print(f"✔ Conectado en {self.port} @ {self.baudrate}")

        except Exception as e:
            raise Exception(f"No se pudo conectar: {e}")

    def send(self, data):
        # envío por bloques (clave para SAT)
        chunk_size = 256

        for i in range(0, len(data), chunk_size):
            self.printer.write(data[i:i+chunk_size])
            time.sleep(0.03)

        self.printer.flush()
        time.sleep(0.1)

    def build_ticket(self, lineas):

        t = bytearray()

        # INIT
        t += b'\x1B\x40'      # reset
        t += b'\x1B\x74\x02'  # charset
        t += b'\x1B\x32'      # line spacing
        t += b'\x1B\x61\x01'  # centrado

        def add(texto):
            t.extend(texto.encode('latin-1', errors='ignore') + b'\n')

        # =====================
        # HEADER
        # =====================
        t += b'\x1B\x21\x30'  # doble tamaño
        if len(lineas) > 0: add(lineas[0])

        t += b'\x1B\x21\x00'  # normal
        if len(lineas) > 1: add(lineas[1])
        if len(lineas) > 2: add(lineas[2])

        t += b'\n'

        # =====================
        # BODY
        # =====================
        t += b'\x1B\x61\x00'  # izquierda

        for i in range(3, 7):
            if len(lineas) > i:
                add(lineas[i])

        t += b'\n'

        # =====================
        # TURNO (DESTACADO)
        # =====================
        t += b'\x1B\x61\x01'   # centro
        t += b'\x1D\x21\x11'   # tamaño grande

        if len(lineas) > 10:
            add("NULL: " + lineas[10])

        t += b'\x1D\x21\x00'   # normal

        # =====================
        # SERVICIO
        # =====================
        if len(lineas) > 11:
            add("NULL: " + lineas[11])

        if len(lineas) > 12:
            add(lineas[12])

        t += b'\n'

        # =====================
        # FOOTER
        # =====================
        t += b'\x1B\x61\x01'

        for i in [7, 8, 9]:
            if len(lineas) > i:
                add(lineas[i])

        t += b'\n\n\n'

        # CUT
        t += b'\x1D\x56\x00'

        return t

    def print(self, lineas):
        tx = self.build_ticket(lineas)
        self.send(tx)

    def close(self):
        if self.printer:
            self.printer.close()


# =========================
# TEST
# =========================

if __name__ == "__main__":

    printer = UniversalESCPrinter(
        port="/dev/ttyUSB0",
        baudrate=9600 
    )

    lineas = [
        "NULL",
    ]

    printer.print(lineas)
    printer.close()