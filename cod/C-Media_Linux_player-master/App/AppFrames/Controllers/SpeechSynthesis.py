from ..Event import Event
from gtts import gTTS
import subprocess
import threading
import time

import logging

import os
import shutil
import tempfile

from PySide6 import QtCore


class SpeechSynthesis(QtCore.QObject):
    """
    Sintesis de voz del player.

    Usa gTTS (requiere internet) y, si no hay conexion, cae a un motor
    local (espeak-ng, espeak o pico2wave) para que el kiosco no se quede
    mudo cuando falla la red.
    """

    # Solo una locucion suena a la vez en todo el proceso. Con varias
    # pantallas hay varias instancias de esta clase y todas comparten
    # la salida de audio; sin este candado se pisan entre si.
    _candado_audio = threading.Lock()

    # Contador para dar un archivo temporal distinto a cada instancia
    _contador = 0
    _candado_contador = threading.Lock()

    # Cuantas veces se reintenta una locucion que fallo antes de descartarla
    MAX_REINTENTOS = 3

    def __init__(self):
        super().__init__()
        self.event = Event("")
        self.is_speaking = False
        self.cancel = False
        self.close = False
        self.queue = []
        self.sub = None

        # Candado para la cola: la modifican el hilo de audio y el hilo
        # de la interfaz (desde el WebChannel) al mismo tiempo
        self._candado_cola = threading.Lock()

        # Evento para dormir en vez de girar en vacio consumiendo CPU
        self._hay_trabajo = threading.Event()

        # Cada instancia escribe en su propio archivo. Antes todas usaban
        # el mismo audio.ogg: con varias pantallas una sobrescribia el
        # audio de otra mientras sonaba.
        with SpeechSynthesis._candado_contador:
            SpeechSynthesis._contador += 1
            numero = SpeechSynthesis._contador

        carpeta = os.path.expanduser('~') + "/.config/Ciel/C-Media_Player/configs"
        try:
            os.makedirs(carpeta, exist_ok=True)
        except Exception:
            carpeta = tempfile.gettempdir()

        # Extension .mp3: gTTS genera MP3, no OGG
        self.path = os.path.join(carpeta, f"audio_{os.getpid()}_{numero}.mp3")

        self.motor_local = self._detectar_motor_local()
        self.reproductor = self._detectar_reproductor()

        if self.reproductor is None:
            logging.error("SpeechSynthesis: no se encontró mpg123 ni ffplay. "
                          "Instale mpg123: sudo apt install mpg123")

        self.thread = threading.Thread(target=self.start_thread, daemon=True)
        self.thread.start()

    # -----------------------------------------------------------------
    # Deteccion de herramientas del sistema
    # -----------------------------------------------------------------
    def _detectar_reproductor(self):
        """
        Busca un reproductor de audio disponible
        :return: str | None. Nombre del ejecutable
        """
        for programa in ("mpg123", "ffplay", "mpv", "cvlc"):
            if shutil.which(programa):
                return programa
        return None

    def _detectar_motor_local(self):
        """
        Busca un motor de voz que funcione sin internet
        :return: str | None. Nombre del ejecutable
        """
        for programa in ("espeak-ng", "espeak", "pico2wave"):
            if shutil.which(programa):
                return programa
        logging.warning("SpeechSynthesis: no hay motor de voz local instalado. "
                        "Sin internet no habrá audio. "
                        "Instale uno: sudo apt install espeak-ng")
        return None

    # -----------------------------------------------------------------
    # Hilo de reproduccion
    # -----------------------------------------------------------------
    def start_thread(self):
        """
        Hilo que consume la cola de locuciones.

        Antes este bucle giraba sin pausa cuando la cola estaba vacia y
        consumia un nucleo completo de forma permanente. Ahora espera en
        un threading.Event hasta que llegue trabajo.
        """
        while not self.close:
            # Duerme hasta que start() avise que hay algo que decir
            if not self._hay_trabajo.wait(timeout=0.5):
                continue
            if self.close:
                break

            while not self.close:
                with self._candado_cola:
                    if self.cancel or not self.queue:
                        self._hay_trabajo.clear()
                        break
                    utterance = self.queue.pop(0)

                texto = str(utterance.get("text", "")).strip()
                if not texto:
                    continue

                intentos = utterance.get("_intentos", 0)
                exito = self._speak(texto.capitalize())

                if not exito and not self.cancel:
                    intentos += 1
                    if intentos < self.MAX_REINTENTOS:
                        # Se reintenta, pero con una pausa. El codigo
                        # anterior reencolaba al frente sin limite ni
                        # espera: si no habia internet, la misma locucion
                        # se reintentaba para siempre a toda velocidad y
                        # el audio no volvia nunca.
                        utterance["_intentos"] = intentos
                        with self._candado_cola:
                            self.queue.insert(0, utterance)
                        time.sleep(1.5 * intentos)
                    else:
                        logging.error(f"SpeechSynthesis: se descarta la locución "
                                      f"tras {intentos} intentos: {texto[:60]}")

    @QtCore.Slot(list)
    def start(self, queue):
        """
        Recibe la cola de locuciones desde JavaScript
        :param queue: list. Locuciones pendientes
        """
        self.cancel = True
        self._detener_reproduccion()

        with self._candado_cola:
            self.queue = list(queue) if queue else []

        # Se limpia la cola del lado de JavaScript. OJO: la variable del
        # JSBridge es una var de closure, no window.queue, asi que hay que
        # apuntar a la que realmente existe (ver el JS corregido).
        self.event.awake_js("if (window.__cielSpeechQueue) { window.__cielSpeechQueue.length = 0; }")

        self.cancel = False
        self._hay_trabajo.set()

    def _detener_reproduccion(self):
        """
        Corta la reproduccion en curso, si la hay
        """
        if self.sub is not None:
            try:
                self.sub.terminate()
            except Exception:
                pass
            self.sub = None

    # -----------------------------------------------------------------
    # Generacion y reproduccion
    # -----------------------------------------------------------------
    def _generar_gtts(self, texto):
        """
        Genera el audio con gTTS. Requiere conexion a internet.
        :param texto: str
        :return: str | None. Ruta del archivo generado
        """
        try:
            motor = gTTS(text=texto, lang="es", slow=False)
            motor.save(self.path)
            return self.path
        except Exception as e:
            logging.warning(f"SpeechSynthesis: gTTS falló ({e}). "
                            "Revise la conexión a internet.")
            return None

    def _hablar_local(self, texto):
        """
        Reproduce con el motor de voz local, sin internet
        :param texto: str
        :return: bool. True si se reprodujo
        """
        if self.motor_local is None:
            return False

        try:
            if self.motor_local in ("espeak-ng", "espeak"):
                comando = [self.motor_local, "-v", "es", "-s", "150", texto]
                self.sub = subprocess.Popen(comando, stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL)
                self.sub.wait()
                return True

            if self.motor_local == "pico2wave":
                wav = self.path.replace(".mp3", ".wav")
                subprocess.run(["pico2wave", "-l", "es-ES", "-w", wav, texto],
                               check=True, timeout=30)
                return self._reproducir(wav)
        except Exception as e:
            logging.error(f"SpeechSynthesis: motor local falló: {e}")

        return False

    def _reproducir(self, archivo):
        """
        Reproduce un archivo de audio
        :param archivo: str. Ruta del archivo
        :return: bool. True si se reprodujo
        """
        if self.reproductor is None:
            return False

        if self.reproductor == "mpg123":
            comando = ["mpg123", "-q", archivo]
        elif self.reproductor == "ffplay":
            comando = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", archivo]
        elif self.reproductor == "mpv":
            comando = ["mpv", "--no-video", "--really-quiet", archivo]
        else:
            comando = ["cvlc", "--play-and-exit", "--quiet", archivo]

        try:
            self.sub = subprocess.Popen(comando, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)
            self.sub.wait()
            return True
        except Exception as e:
            logging.error(f"SpeechSynthesis: no se pudo reproducir: {e}")
            return False

    def _speak(self, text):
        """
        Genera y reproduce una locucion
        :param text: str. Texto a decir
        :return: bool. True si se reprodujo correctamente
        """
        # Solo una locucion a la vez en todo el proceso
        with SpeechSynthesis._candado_audio:
            if self.cancel or self.close:
                return True   # cancelado a proposito, no es un fallo

            self.is_speaking = True
            try:
                archivo = self._generar_gtts(text)

                if archivo is not None:
                    if self._reproducir(archivo):
                        return True
                    return False

                # Sin internet: se intenta con el motor local
                logging.info("SpeechSynthesis: usando el motor de voz local")
                return self._hablar_local(text)
            except Exception as e:
                logging.error(f"SpeechSynthesis: error al hablar: {e}")
                return False
            finally:
                self.is_speaking = False
                self.sub = None

    def speak_func(self, speechSynthesisUtterance):
        """
        Compatibilidad con el codigo anterior
        :param speechSynthesisUtterance: str. Texto a decir
        """
        self._speak(str(speechSynthesisUtterance))

    # -----------------------------------------------------------------
    # API expuesta a JavaScript
    # -----------------------------------------------------------------
    @QtCore.Slot()
    def getVoices(self):
        return ""

    def get_event(self):
        return self.event

    @QtCore.Slot()
    def cancel_speech(self):
        """
        Cancela todo lo pendiente y corta lo que este sonando
        """
        self.cancel = True
        with self._candado_cola:
            self.queue = []
        self._detener_reproduccion()
        self._hay_trabajo.clear()
        self.cancel = False

    def close_thread(self):
        """
        Detiene el hilo de sintesis y limpia el archivo temporal
        """
        self.cancel = True
        self.close = True
        self._detener_reproduccion()
        self._hay_trabajo.set()   # despierta el hilo para que pueda salir

        try:
            self.thread.join(timeout=3)
        except Exception:
            pass

        for archivo in (self.path, self.path.replace(".mp3", ".wav")):
            try:
                if os.path.exists(archivo):
                    os.remove(archivo)
            except Exception:
                pass
