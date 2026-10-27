
import serial
import time
import re
import sys

PORT = "/dev/ttyACM0"
BAUD = 9600
CMD_TRIGGER = b'\x16\x4D\x0D'  # SYN M CR — dispara un escaneo

def __init__(self, device=None):
    self.device = device
   
    self.connect()
    print("DEVICE:", device, type(device))
    print("USB OBJ:", self.device.get("USB ", "No hay USB"), type(self.device.get("USB ", "No hay USB")))
    print("PUERTO SERIAL:", self.device.get("PORT ", "No hay PORT"), type(self.device.get("PORT ", "No hay PORT")))

def extraer_cedula(raw_bytes):
    """
    Extrae el número de cédula de los bytes raw del lector.
    Regla: 10 dígitos justo antes del nombre (mayúsculas).
    Si empieza en 0 → cédula de 8 dígitos, se eliminan los ceros.
    """
   

    try:
        texto = raw_bytes.decode('latin-1')  # latin-1 preserva todos los bytes

        # Busca: 10+ dígitos seguidos de 2+ letras mayúsculas (el nombre)
        match = re.search(r'(\d{10,})([A-Z]{2,})', texto)
        if match:
            digits = match.group(1)
            cedula = digits[-10:]           # últimos 10 dígitos
            cedula = cedula.lstrip('0')     # quitar ceros (cédulas de 8 dígitos)
            return cedula if cedula else None

    except Exception as e:
        print(f"Error al extraer cédula: {e}")
    return None


def debug_cedulas():
    print(" LECTOR CÉDULAS — SERIAL")
    print(f" Conectando a {PORT}...\n")

    try:
        ser = serial.Serial(PORT, BAUD, timeout=3)
        print(f" Puerto abierto.\n")
        time.sleep(0.5)

        # Intento de modo presentación (permanente en el lector)
        # Si no funciona, el re-trigger por software igual garantiza lectura continua
        print("  Intentando configurar modo presentación...")
        ser.write(b'\x16\x45\x0D')  # entrar config
        time.sleep(0.3)
        ser.write(b'TRGSTP3\r')     # modo presentación
        time.sleep(0.3)
        ser.write(b'\x16\x46\x0D') # salir config
        time.sleep(0.5)
        ser.reset_input_buffer()

        # Primer disparo manual (por si el modo presentación no tomó)
        ser.write(CMD_TRIGGER)
        print("Listo. Acerca una cédula...\n")
        print("-" * 50)

        while True:
            # readline() lee hasta \n o hasta que venza el timeout
            raw = ser.read_until(b'\r')

            if not raw:
                # Timeout — re-disparar para garantizar lectura continua
                
                ser.write(CMD_TRIGGER)
                continue

            cedula = extraer_cedula(raw)

            if cedula:
                print(f"CÉDULA: {cedula}")
                print(f"   Dígitos: {len(cedula)}")
            else:
                # No es cédula — puede ser QR, código de barras, etc.
                try:
                    texto = raw.strip().decode('utf-8', errors='replace')
                    if texto:
                        print(f" CÓDIGO (no cédula): {texto[:40]}")
                except:
                    pass

            print("-" * 50)

            # Re-disparar para siguiente lectura (fallback si modo presentación no funcionó)
            time.sleep(0.5)  # pausa anti-doble lectura
            ser.write(CMD_TRIGGER)
       
    except serial.SerialException as e:
        print(f" Error de puerto: {e}")
    except KeyboardInterrupt:
        print("\n Saliendo...")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
    

if __name__ == "__main__":
    debug_cedulas()