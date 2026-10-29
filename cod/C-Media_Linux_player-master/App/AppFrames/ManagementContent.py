import hashlib
import json
import logging
import mimetypes
import os
import re
import socket
import ssl
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import ProxyHandler, Request, build_opener, urlopen

from PySide6.QtCore import QObject, Signal, Slot



# Rutas y parametros
BASE_DIR = os.path.join(os.path.expanduser("~"), ".config", "Ciel", "C-Media_Player")
CONFIG_JSON = os.path.join(BASE_DIR, "configs", "config.json")
CONTENIDOS_DIR = os.path.join(BASE_DIR, "contenidos")
ARCHIVOS_DIR = os.path.join(CONTENIDOS_DIR, "archivos")
MANIFIESTO = os.path.join(CONTENIDOS_DIR, "manifiesto.json")

CONTROL_WEB = "Control.NavegadorWebChrome.dll"

PUERTO_LOCAL = 8807          # puerto del servidor local (127.0.0.1)
TIEMPO_CAPTURA = 25          # segundos que se deja correr cada pagina para detectar peticiones
TIMEOUT_DESCARGA = 30        # segundos por peticion
TIMEOUT_CONEXION = 3         # segundos para decidir si el servidor responde
MAX_RECURSOS = 3000          # tope de archivos por sincronizacion
BLOQUE = 256 * 1024
AGENTE = "C-Media Player (sincronizacion de contenidos)"

# Igual que WebViewFrame, que acepta el certificado del servidor interno.
# Con un certificado valido en produccion, cambiar a True.
VERIFICAR_SSL = False

MODO_AUTOMATICO = "automatico"      # en linea si el servidor responde; si no, copia local
MODO_EN_LINEA = "en_linea"          # siempre el servidor (no usa la copia)
MODO_SIN_CONEXION = "sin_conexion"  # siempre la copia local

CATEGORIAS_CONTENIDO = ("imagen", "video", "audio", "documento")

MARCA_CAPTURA = "CMEDIA_CAPTURA:"

for _ext, _tipo in ((".mp4", "video/mp4"), (".webm", "video/webm"), (".m4v", "video/mp4"),
                    (".mov", "video/quicktime"), (".mkv", "video/x-matroska"),
                    (".ogv", "video/ogg"), (".mp3", "audio/mpeg"), (".m4a", "audio/mp4"),
                    (".js", "application/javascript"), (".mjs", "application/javascript"),
                    (".json", "application/json"), (".svg", "image/svg+xml"),
                    (".webp", "image/webp"), (".woff", "font/woff"), (".woff2", "font/woff2")):
    mimetypes.add_type(_tipo, _ext)



# Utilidades
def ahora_iso():
    return datetime.now().isoformat(timespec="seconds")


def normalizar_url(url):
    """Quita espacios y agrega http:// si la URL no trae esquema."""
    url = (url or "").strip()
    if url and "://" not in url:
        url = "http://" + url
    return url


def origen_de(url):
    """'https://host:8806/api/x?y' -> 'https://host:8806'"""
    p = urlsplit(url)
    if not p.scheme or not p.netloc:
        return ""
    return f"{p.scheme.lower()}://{p.netloc}"


def mismo_origen(url_a, url_b):
    return bool(url_a) and origen_de(url_a).lower() == origen_de(url_b).lower()


def clave_de(url):
    """Identificador de un recurso dentro del servidor: ruta + consulta."""
    p = urlsplit(url)
    return (p.path or "/") + ("?" + p.query if p.query else "")


def nombre_de(url_o_clave):
    """Nombre legible: ultimo segmento de la ruta."""
    ruta = urlsplit(url_o_clave).path.rstrip("/")
    nombre = unquote(ruta.rsplit("/", 1)[-1]) if ruta else ""
    return nombre or urlsplit(url_o_clave).netloc or "inicio"


def categoria_de(mime, url=""):
    mime = (mime or "").split(";")[0].strip().lower()
    if not mime or mime in ("application/octet-stream", "binary/octet-stream"):
        mime = mimetypes.guess_type(urlsplit(url).path)[0] or ""
    if mime.startswith("image/"):
        return "imagen"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("audio/"):
        return "audio"
    if mime == "application/pdf":
        return "documento"
    if mime in ("text/html", "application/xhtml+xml"):
        return "pagina"
    if mime == "text/css":
        return "estilo"
    if "javascript" in mime or "ecmascript" in mime:
        return "script"
    if "json" in mime or "xml" in mime:
        return "datos"
    if mime.startswith("font/") or "font" in mime:
        return "fuente"
    return "otro"


def es_texto(mime):
    mime = (mime or "").lower()
    return mime.startswith("text/") or any(
        t in mime for t in ("json", "javascript", "ecmascript", "xml"))


def formato_tamano(bytes_):
    valor = float(bytes_ or 0)
    for unidad in ("B", "KB", "MB", "GB"):
        if valor < 1024 or unidad == "GB":
            return f"{valor:.0f} {unidad}" if unidad == "B" else f"{valor:.1f} {unidad}"
        valor /= 1024


def formato_fecha(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return "—"


def nombre_archivo(clave, mime, url):
    """Nombre del archivo en disco: hash de la clave + extension."""
    ext = os.path.splitext(urlsplit(url).path)[1].lower()
    if not (1 < len(ext) <= 6) or not re.fullmatch(r"\.[a-z0-9]+", ext):
        ext = mimetypes.guess_extension((mime or "").split(";")[0].strip()) or ".bin"
    return hashlib.sha1(clave.encode("utf-8")).hexdigest()[:20] + ext


def ruta_archivo(recurso):
    return os.path.join(ARCHIVOS_DIR, recurso.get("archivo", ""))


def _borrar(ruta):
    try:
        os.remove(ruta)
    except OSError:
        pass



# Configuracion del player (URLs de los controles web)
def ruta_pantallas():
    """Resuelve el archivo de pantallas (.ccmj) a partir de config.json."""
    with open(CONFIG_JSON, "r") as file:
        ruta = json.load(file)["Ruta"]
    if ruta.startswith("$"):
        sep = ruta.find("/")
        ruta = os.environ[ruta[1:sep]] + ruta[sep:]
    return ruta


def urls_inicio_configuradas():
    """URLs de inicio de todos los controles web del archivo de pantallas."""
    try:
        with open(ruta_pantallas(), "r", encoding="utf-8-sig") as file:
            settings = json.load(file)
    except Exception as e:
        logging.error("ManagementContent - lectura de pantallas: " + str(e))
        return []

    urls = []
    for pantalla in settings.get("Pantallas", []):
        for control in pantalla.get("Controles", []):
            if CONTROL_WEB in control.get("NombreArchivo", ""):
                url = control.get("ObjetoBase", {}).get("UrlInicio", "")
                if url and url not in urls:
                    urls.append(url)
    return urls


def servidor_alcanzable(url, timeout=TIMEOUT_CONEXION):
    """True si se puede abrir una conexion TCP con el servidor de la URL."""
    p = urlsplit(normalizar_url(url))
    if not p.hostname:
        return False
    puerto = p.port or (443 if p.scheme == "https" else 80)
    try:
        with socket.create_connection((p.hostname, puerto), timeout=timeout):
            return True
    except OSError:
        return False



# indice de la copia local
class Manifiesto:
    """
    Indice de la copia local (contenidos/manifiesto.json).

    recursos: { clave: {
        "clave", "url", "archivo", "mime", "tipo_contenido", "categoria",
        "nombre", "tamano", "activo", "en_servidor", "etag", "modificado",
        "descargado" } }
    orden: [clave, ...]  orden de los contenidos (imagen/video/audio/documento)
    """

    def __init__(self, ruta=MANIFIESTO):
        self.ruta = ruta
        self.datos = self._vacio()
        self.cargar()

    @staticmethod
    def _vacio():
        return {
            "version": 1,
            "origen": "",
            "urls_inicio": [],
            "modo": MODO_AUTOMATICO,
            "puerto": PUERTO_LOCAL,
            "ultima_sincronizacion": "",
            "recursos": {},
            "orden": [],
        }

    def cargar(self):
        try:
            with open(self.ruta, "r", encoding="utf-8") as file:
                datos = json.load(file)
            base = self._vacio()
            base.update(datos)
            self.datos = base
        except FileNotFoundError:
            pass
        except Exception as e:
            logging.error("ManagementContent - manifiesto ilegible: " + str(e))
        return self

    def guardar(self):
        os.makedirs(os.path.dirname(self.ruta), exist_ok=True)
        temporal = self.ruta + ".tmp"
        with open(temporal, "w", encoding="utf-8") as file:
            json.dump(self.datos, file, ensure_ascii=False, indent=1)
        os.replace(temporal, self.ruta)

    # Accesos rapidos
    @property
    def origen(self):
        return self.datos.get("origen", "")

    @property
    def modo(self):
        return self.datos.get("modo", MODO_AUTOMATICO)

    @property
    def puerto(self):
        return int(self.datos.get("puerto") or PUERTO_LOCAL)

    @property
    def recursos(self):
        return self.datos.setdefault("recursos", {})

    @property
    def orden(self):
        return self.datos.setdefault("orden", [])

    def contenidos(self, solo_activos=False):
        """Contenidos (imagen/video/audio/documento) en el orden guardado."""
        recursos = self.recursos
        lista = [recursos[c] for c in self.orden if c in recursos]
        vistos = {r["clave"] for r in lista}
        lista += [r for c, r in recursos.items()
                  if r.get("categoria") in CATEGORIAS_CONTENIDO and c not in vistos]
        if solo_activos:
            lista = [r for r in lista if r.get("activo", True)]
        return lista

    def buscar(self, clave):
        """Busca por clave exacta; si no, por la misma ruta sin la consulta."""
        recurso = self.recursos.get(clave)
        if recurso:
            return recurso
        ruta = clave.split("?", 1)[0]
        for c, r in self.recursos.items():
            if c.split("?", 1)[0] == ruta:
                return r
        return None

    def eliminar(self, clave):
        """Quita un recurso del indice y borra su archivo."""
        recurso = self.recursos.pop(clave, None)
        if recurso:
            _borrar(ruta_archivo(recurso))
        if clave in self.orden:
            self.orden.remove(clave)

    def vaciar(self):
        """Borra toda la copia (se usa al cambiar de servidor)."""
        for recurso in list(self.recursos.values()):
            _borrar(ruta_archivo(recurso))
        modo, puerto = self.modo, self.puerto
        self.datos = self._vacio()
        self.datos["modo"], self.datos["puerto"] = modo, puerto



# Deteccion de rutas dentro de archivos de texto
_EXT = (r"png|jpe?g|gif|webp|svg|bmp|ico|avif|mp4|webm|ogg|ogv|mov|m4v|mkv|"
        r"mp3|wav|m4a|aac|flac|pdf|css|js|mjs|json|woff2?|ttf|otf|eot|html?")
RE_CSS_URL = re.compile(r"""url\(\s*["']?([^"')]+?)["']?\s*\)""", re.I)
RE_CSS_IMPORT = re.compile(r"""@import\s+["']([^"']+)["']""", re.I)
RE_URL_ABSOLUTA = re.compile(r"""https?:(?:\\?/){2}[^\s"'<>()`]+""", re.I)
RE_RUTA_RECURSO = re.compile(
    r"""["'(`]((?:\.{0,2}/)?[\w\-./%~]+\.(?:""" + _EXT + r""")(?:\?[^"'()`\s<>]*)?)["')`]""",
    re.I)


class _ExtractorHTML(HTMLParser):
    """Junta src/href/poster/srcset/style de las etiquetas HTML."""

    ATRIBUTOS = ("src", "poster", "data-src", "data-poster", "data-background",
                 "background", "data")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rutas = []

    def handle_starttag(self, tag, attrs):
        a = {k: v for k, v in attrs if v}
        for nombre in self.ATRIBUTOS:
            if a.get(nombre):
                self.rutas.append(a[nombre])
        # href solo en <link> (estilos, iconos, manifest); los <a> son navegacion
        if tag == "link" and a.get("href"):
            self.rutas.append(a["href"])
        for nombre in ("srcset", "data-srcset"):
            if a.get(nombre):
                self.rutas += [p.strip().split(" ")[0] for p in a[nombre].split(",") if p.strip()]
        if a.get("style"):
            self.rutas += RE_CSS_URL.findall(a["style"])


def extraer_urls(contenido, url_base, mime):
    """Devuelve las URLs absolutas referenciadas por un archivo de texto."""
    # \/ es como JSON escapa las barras: se normaliza antes de buscar rutas
    texto = contenido.decode("utf-8", errors="replace").replace("\\/", "/")
    rutas = []
    if "html" in (mime or ""):
        extractor = _ExtractorHTML()
        try:
            extractor.feed(texto)
        except Exception:
            pass
        rutas += extractor.rutas
    rutas += RE_CSS_URL.findall(texto)
    rutas += RE_CSS_IMPORT.findall(texto)
    rutas += RE_URL_ABSOLUTA.findall(texto)
    rutas += RE_RUTA_RECURSO.findall(texto)

    resultado = set()
    for ruta in rutas:
        ruta = ruta.strip().replace("\\/", "/").rstrip("\\,;")
        if not ruta or ruta.startswith(("data:", "blob:", "javascript:", "mailto:",
                                        "tel:", "#", "about:")):
            continue
        if any(c in ruta for c in "{}$+"):   # plantillas o concatenaciones de JS
            continue
        try:
            url = urljoin(url_base, ruta)
        except ValueError:
            continue
        resultado.add(url.split("#", 1)[0])
    return resultado



# Sincronizacion (corre en un QThread)
class _Cancelado(Exception):
    pass


class Sincronizador(QObject):
    """
    Descarga el reproductor web y sus contenidos a la copia local.
    Uso: moverlo a un QThread y conectar thread.started -> ejecutar.
    """

    progreso = Signal(int, int, str)    # actual, total (0 = indeterminado), mensaje
    terminado = Signal(bool, str)       # ok, mensaje para el usuario

    def __init__(self, urls_inicio, usar_captura=True, parent=None):
        super().__init__(parent)
        self.urls_inicio = [normalizar_url(u) for u in urls_inicio if u and u.strip()]
        self.usar_captura = usar_captura
        self.errores = []
        self._cancelado = False
        self._proceso = None
        self._no_encontrados = set()
        self._paso = (0, 0)

        self._ctx = ssl.create_default_context()
        if not VERIFICAR_SSL:
            self._ctx.check_hostname = False
            self._ctx.verify_mode = ssl.CERT_NONE

    def cancelar(self):
        """Se puede llamar desde el hilo de la interfaz."""
        self._cancelado = True
        proceso = self._proceso
        if proceso is not None and proceso.poll() is None:
            try:
                proceso.kill()
            except Exception:
                pass

    @Slot()
    def ejecutar(self):
        try:
            ok, mensaje = self._sincronizar()
        except Exception as e:
            logging.exception("ManagementContent - sincronizacion")
            ok, mensaje = False, f"Error inesperado durante la descarga:\n{e}"
        self.terminado.emit(ok, mensaje)

    # -----------------------------------------------------------------
    def _sincronizar(self):
        if not self.urls_inicio:
            return False, "No hay una URL de servidor configurada."
        origen = origen_de(self.urls_inicio[0])
        if not origen:
            return False, "La URL del servidor no es válida."
        inicio = [u for u in self.urls_inicio if mismo_origen(u, origen)]

        self.progreso.emit(0, 0, f"Conectando con {origen} ...")
        if not servidor_alcanzable(inicio[0]):
            return False, ("No se pudo conectar con el servidor.\n"
                           "Revise la URL y la conexión de red.")

        manifiesto = Manifiesto()
        if manifiesto.origen and not mismo_origen(manifiesto.origen, origen):
            manifiesto.vaciar()   # copia de otro servidor: se reemplaza
        anteriores = dict(manifiesto.recursos)

        pendientes = deque(inicio)

        # 1. Navegador oculto: anota todo lo que la pagina pide al ejecutarse
        if self.usar_captura:
            self.progreso.emit(0, 0, "Abriendo el reproductor web para detectar sus contenidos ...")
            capturadas = [u for u in self._capturar(inicio) if mismo_origen(u, origen)]
            logging.info(f"ManagementContent - captura: {len(capturadas)} peticiones")
            pendientes.extend(capturadas)
            if self._cancelado:
                return False, "Descarga cancelada."

        # 2. Descarga recorriendo las referencias de cada archivo de texto
        nuevos, vistos, descargados = {}, set(), set()
        while pendientes and not self._cancelado:
            url = pendientes.popleft()
            clave = clave_de(url)
            if clave in vistos:
                continue
            if len(vistos) >= MAX_RECURSOS:
                self.errores.append(f"Se alcanzó el límite de {MAX_RECURSOS} archivos.")
                break
            vistos.add(clave)
            self._paso = (len(vistos), len(vistos) + len(pendientes))
            self.progreso.emit(*self._paso, f"Descargando {nombre_de(url)}")

            recurso = self._descargar(url, anteriores.get(clave))
            if not recurso:
                continue
            nuevos[clave] = recurso
            descargados.add(clave)

            if es_texto(recurso["mime"]):
                try:
                    with open(ruta_archivo(recurso), "rb") as file:
                        contenido = file.read()
                except OSError:
                    continue
                for encontrada in extraer_urls(contenido, url, recurso["mime"]):
                    if mismo_origen(encontrada, origen) and clave_de(encontrada) not in vistos:
                        pendientes.append(encontrada)

        # 3. Combinar con lo que ya habia
        for clave, recurso in anteriores.items():
            if clave in nuevos:
                continue
            if clave in self._no_encontrados or (clave not in vistos and not self._cancelado):
                recurso["en_servidor"] = False
            nuevos[clave] = recurso

        orden = [c for c in manifiesto.orden if c in nuevos]
        orden += [c for c, r in nuevos.items()
                  if r.get("categoria") in CATEGORIAS_CONTENIDO and c not in orden]

        manifiesto.datos.update({
            "origen": origen,
            "urls_inicio": inicio,
            "ultima_sincronizacion": ahora_iso(),
            "recursos": nuevos,
            "orden": orden,
        })
        manifiesto.guardar()

        # 4. Mensaje para el usuario
        n_contenidos = sum(1 for r in nuevos.values() if r.get("categoria") in CATEGORIAS_CONTENIDO)
        mensaje = (f"Copia local: {len(nuevos)} archivos, {n_contenidos} de ellos son "
                   f"contenidos (imágenes, videos, audios o documentos).")
        if self.errores:
            mensaje += f"\n\n{len(self.errores)} archivo(s) no se pudieron descargar:\n"
            mensaje += "\n".join("• " + e for e in self.errores[:8])
            if len(self.errores) > 8:
                mensaje += "\n• ..."

        if self._cancelado:
            return False, "Descarga cancelada. Se guardó lo descargado hasta el momento.\n\n" + mensaje
        if clave_de(inicio[0]) not in descargados:
            return False, "No se pudo descargar la página de inicio del servidor.\n\n" + mensaje
        return True, mensaje

    def _descargar(self, url, previo):
        """Descarga un recurso. Devuelve su registro o None si fallo."""
        clave = clave_de(url)
        cabeceras = {"User-Agent": AGENTE, "Accept": "*/*"}
        if previo and os.path.exists(ruta_archivo(previo)):
            if previo.get("etag"):
                cabeceras["If-None-Match"] = previo["etag"]
            if previo.get("modificado"):
                cabeceras["If-Modified-Since"] = previo["modificado"]

        try:
            respuesta = urlopen(Request(url, headers=cabeceras),
                                timeout=TIMEOUT_DESCARGA, context=self._ctx)
        except HTTPError as e:
            if e.code == 304 and previo:
                recurso = dict(previo)
                recurso["en_servidor"] = True
                return recurso
            if e.code in (404, 410):
                self._no_encontrados.add(clave)
                if clave == "/favicon.ico":   # el navegador lo pide siempre; no es un error real
                    return None
            self.errores.append(f"{nombre_de(url)} (HTTP {e.code})")
            return None
        except (URLError, OSError, ValueError) as e:
            motivo = getattr(e, "reason", e)
            self.errores.append(f"{nombre_de(url)} ({motivo})")
            return None

        with respuesta:
            tipo_contenido = respuesta.headers.get("Content-Type", "")
            if tipo_contenido:
                mime = respuesta.headers.get_content_type()
            else:
                mime = mimetypes.guess_type(urlsplit(url).path)[0] or "application/octet-stream"
            archivo = nombre_archivo(clave, mime, url)
            destino = os.path.join(ARCHIVOS_DIR, archivo)
            temporal = destino + ".part"
            os.makedirs(ARCHIVOS_DIR, exist_ok=True)

            tamano, ultimo_aviso = 0, 0
            try:
                with open(temporal, "wb") as file:
                    while True:
                        if self._cancelado:
                            raise _Cancelado()
                        bloque = respuesta.read(BLOQUE)
                        if not bloque:
                            break
                        file.write(bloque)
                        tamano += len(bloque)
                        if tamano - ultimo_aviso >= 4 * 1024 * 1024:   # archivos grandes
                            ultimo_aviso = tamano
                            self.progreso.emit(*self._paso,
                                               f"Descargando {nombre_de(url)} ({formato_tamano(tamano)})")
                os.replace(temporal, destino)
            except _Cancelado:
                _borrar(temporal)
                return None
            except OSError as e:
                _borrar(temporal)
                self.errores.append(f"{nombre_de(url)} (no se pudo guardar: {e})")
                return None

            etag = respuesta.headers.get("ETag", "")
            modificado = respuesta.headers.get("Last-Modified", "")

        if previo and previo.get("archivo") and previo["archivo"] != archivo:
            _borrar(ruta_archivo(previo))

        return {
            "clave": clave,
            "url": url,
            "archivo": archivo,
            "mime": mime,
            "tipo_contenido": tipo_contenido,
            "categoria": categoria_de(mime, url),
            "nombre": nombre_de(url),
            "tamano": tamano,
            "activo": previo.get("activo", True) if previo else True,
            "en_servidor": True,
            "etag": etag,
            "modificado": modificado,
            "descargado": ahora_iso(),
        }

  
    def _capturar(self, urls):
        """
        Corre este mismo archivo en modo captura (proceso aparte con
        QtWebEngine) y devuelve las URLs que pidio la pagina.
        """
        if getattr(sys, "frozen", False):
            # En un ejecutable empaquetado no hay interprete para el proceso aparte;
            # se usa solo la deteccion por lectura de archivos.
            logging.info("ManagementContent - captura omitida (aplicacion empaquetada)")
            return []

        comando = [sys.executable, os.path.abspath(__file__), "--capturar",
                   "--segundos", str(TIEMPO_CAPTURA), *urls]
        salida = ""
        try:
            self._proceso = subprocess.Popen(comando, stdout=subprocess.PIPE,
                                             stderr=subprocess.DEVNULL, text=True)
            limite = time.monotonic() + TIEMPO_CAPTURA * len(urls) + 45
            while self._proceso.poll() is None:
                if self._cancelado or time.monotonic() > limite:
                    self._proceso.kill()
                    break
                time.sleep(0.3)
            if self._proceso.stdout:
                salida = self._proceso.stdout.read()
        except Exception as e:
            logging.warning("ManagementContent - captura no disponible: " + str(e))
            return []
        finally:
            self._proceso = None

        for linea in reversed(salida.splitlines()):
            if linea.startswith(MARCA_CAPTURA):
                try:
                    return json.loads(linea[len(MARCA_CAPTURA):])
                except ValueError:
                    break
        return []


# Servidor local
class _Catalogo:
    """Lo que el servidor local puede entregar. Se recarga si cambia el manifiesto."""

    def __init__(self, origen_local):
        self.origen_local = origen_local
        self._lock = threading.Lock()
        self._mtime = -1
        self.manifiesto = Manifiesto()
        self._por_ruta = {}
        self._reemplazos = []
        self._recargar()

    def _recargar(self):
        try:
            mtime = os.path.getmtime(MANIFIESTO)
        except OSError:
            mtime = None
        if mtime == self._mtime:
            return
        with self._lock:
            self.manifiesto = Manifiesto()
            self._mtime = mtime
            self._por_ruta = {}
            for clave in self.manifiesto.recursos:
                self._por_ruta.setdefault(clave.split("?", 1)[0], clave)
            self._reemplazos = self._crear_reemplazos()

    def _crear_reemplazos(self):
        origen = self.manifiesto.origen
        if not origen:
            return []
        host = urlsplit(origen).netloc
        local = self.origen_local
        host_local = urlsplit(local).netloc
        pares = [
            (origen, local),                                            # https://host:8806
            (origen.replace("/", "\\/"), local.replace("/", "\\/")),    # https:\/\/host:8806 (JSON)
            ("//" + host, "//" + host_local),                           # //host:8806 y http://host:8806
            ("\\/\\/" + host, "\\/\\/" + host_local),
        ]
        return [(a.encode("utf-8"), b.encode("utf-8")) for a, b in pares]

    def buscar(self, clave):
        self._recargar()
        recursos = self.manifiesto.recursos
        recurso = recursos.get(clave)
        if recurso is None:
            alterna = self._por_ruta.get(clave.split("?", 1)[0])
            recurso = recursos.get(alterna) if alterna else None
        return recurso

    def reescribir(self, datos):
        for original, local in self._reemplazos:
            datos = datos.replace(original, local)
        return datos

    def lista_contenidos(self):
        self._recargar()
        return [{
            "posicion": i,
            "nombre": r.get("nombre", ""),
            "tipo": r.get("categoria", ""),
            "mime": r.get("mime", ""),
            "url": self.origen_local + r["clave"],
            "url_original": r.get("url", ""),
        } for i, r in enumerate(self.manifiesto.contenidos(solo_activos=True), start=1)]


class _Manejador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "CMediaLocal/1.0"

    def log_message(self, formato, *args):
        logging.debug("ServidorLocal: " + (formato % args))

    # Metodos
    def do_GET(self):
        self._servir(True)

    def do_HEAD(self):
        self._servir(False)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        # Sin servidor no se pueden enviar datos: se responde claro y rapido
        largo = int(self.headers.get("Content-Length") or 0)
        if largo:
            self.rfile.read(largo)
        self._json(503, {"sin_conexion": True,
                         "mensaje": "El reproductor está usando la copia local; "
                                    "esta acción necesita conexión con el servidor."})

    do_PUT = do_PATCH = do_DELETE = do_POST

    # Ayudas
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS")

    def _json(self, codigo, objeto, cuerpo=True):
        datos = json.dumps(objeto, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        if cuerpo:
            self.wfile.write(datos)

    def _servir(self, cuerpo):
        catalogo = self.server.catalogo
        partes = urlsplit(self.path)
        clave = (partes.path or "/") + ("?" + partes.query if partes.query else "")

        if partes.path == "/__cmedia/estado":
            return self._json(200, {"ok": True, "origen": catalogo.manifiesto.origen}, cuerpo)
        if partes.path == "/__cmedia/contenidos.json":
            return self._json(200, catalogo.lista_contenidos(), cuerpo)

        recurso = catalogo.buscar(clave)
        if recurso is None or (recurso.get("categoria") in CATEGORIAS_CONTENIDO
                               and not recurso.get("activo", True)):
            return self._json(404, {"error": "No disponible en la copia local", "ruta": clave}, cuerpo)

        ruta = ruta_archivo(recurso)
        try:
            tamano = os.path.getsize(ruta)
        except OSError:
            return self._json(404, {"error": "Archivo no encontrado en disco", "ruta": clave}, cuerpo)

        mime = recurso.get("mime") or "application/octet-stream"
        tipo = recurso.get("tipo_contenido") or mime

        try:
            # Se reescriben las URLs del servidor para que apunten aqui
            if es_texto(mime):
                with open(ruta, "rb") as file:
                    datos = catalogo.reescribir(file.read())
                self.send_response(200)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(datos)))
                self.send_header("Cache-Control", "no-cache")
                self._cors()
                self.end_headers()
                if cuerpo:
                    self.wfile.write(datos)
                return

            # Binario: con soporte de rangos (necesario para adelantar videos)
            inicio, fin, codigo = 0, tamano - 1, 200
            rango = re.match(r"bytes=(\d*)-(\d*)$", (self.headers.get("Range") or "").strip())
            if rango and (rango.group(1) or rango.group(2)):
                if rango.group(1):
                    inicio = int(rango.group(1))
                    fin = int(rango.group(2)) if rango.group(2) else tamano - 1
                else:
                    inicio = max(0, tamano - int(rango.group(2)))
                fin = min(fin, tamano - 1)
                if inicio >= tamano or inicio > fin:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{tamano}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                codigo = 206

            largo = max(0, fin - inicio + 1)
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(largo))
            self.send_header("Accept-Ranges", "bytes")
            if codigo == 206:
                self.send_header("Content-Range", f"bytes {inicio}-{fin}/{tamano}")
            self.send_header("Cache-Control", "no-cache")
            self._cors()
            self.end_headers()
            if cuerpo:
                with open(ruta, "rb") as file:
                    file.seek(inicio)
                    restante = largo
                    while restante > 0:
                        bloque = file.read(min(BLOQUE, restante))
                        if not bloque:
                            break
                        self.wfile.write(bloque)
                        restante -= len(bloque)
        except (BrokenPipeError, ConnectionResetError):
            pass   # el navegador cancela la peticion (normal al saltar un video)


class _ServidorHTTP(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


_servidor = None
_servidor_lock = threading.Lock()


def _origen_local(puerto):
    return f"http://127.0.0.1:{puerto}"


def _estado_ok(puerto):
    """True si en ese puerto ya hay un servidor de contenidos (otra ventana del player)."""
    try:
        abridor = build_opener(ProxyHandler({}))
        with abridor.open(_origen_local(puerto) + "/__cmedia/estado", timeout=1) as r:
            return json.loads(r.read().decode("utf-8")).get("ok", False)
    except Exception:
        return False


def iniciar_servidor_local(puerto=None):
    """
    Arranca (una sola vez por proceso) el servidor de la copia local.
    :return: str origen local ('http://127.0.0.1:8807') o None si no se pudo.
    """
    global _servidor
    puerto = puerto or Manifiesto().puerto
    with _servidor_lock:
        if _servidor is not None:
            return _servidor.catalogo.origen_local
        try:
            servidor = _ServidorHTTP(("127.0.0.1", puerto), _Manejador)
        except OSError as e:
            if _estado_ok(puerto):
                return _origen_local(puerto)
            logging.error(f"ManagementContent - no se pudo abrir el puerto {puerto}: {e}")
            return None
        servidor.catalogo = _Catalogo(_origen_local(puerto))
        hilo = threading.Thread(target=servidor.serve_forever, name="CMediaServidorLocal", daemon=True)
        hilo.start()
        _servidor = servidor
        logging.info(f"ManagementContent - servidor local en {_origen_local(puerto)}")
        return servidor.catalogo.origen_local


def detener_servidor_local():
    global _servidor
    with _servidor_lock:
        if _servidor is not None:
            _servidor.shutdown()
            _servidor.server_close()
            _servidor = None


# API para el reproductor (WebViewFrame)
def resolver_url_inicio(url, forzar_local=False):
    """
    URL que debe abrir el reproductor segun el modo configurado.
    - Sin copia local de ese servidor -> la URL original.
    - en_linea      -> la URL original.
    - automatico    -> la original si el servidor responde; si no, la copia local.
    - sin_conexion  -> la copia local.
    Nunca lanza excepciones: ante cualquier problema devuelve la URL original.
    """
    try:
        manifiesto = Manifiesto()
        if not manifiesto.recursos or not mismo_origen(url, manifiesto.origen):
            return url
        if manifiesto.buscar(clave_de(url)) is None:
            return url
        if not forzar_local:
            if manifiesto.modo == MODO_EN_LINEA:
                return url
            if manifiesto.modo == MODO_AUTOMATICO and servidor_alcanzable(url):
                return url
        local = iniciar_servidor_local(manifiesto.puerto)
        if not local:
            return url
        logging.info(f"ManagementContent - usando copia local para {url}")
        return local + clave_de(url)
    except Exception as e:
        logging.error("ManagementContent - resolver_url_inicio: " + str(e))
        return url


def respaldo_local(url):
    """
    URL de la copia local para usar cuando la pagina en linea no cargo.
    Devuelve None si el modo es 'siempre en linea' o no hay copia.
    """
    if Manifiesto().modo == MODO_EN_LINEA:
        return None
    local = resolver_url_inicio(url, forzar_local=True)
    return local if local != url else None



# Modo captura
def _modo_captura(argumentos):
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--capturar", action="store_true")
    parser.add_argument("--segundos", type=int, default=TIEMPO_CAPTURA)
    parser.add_argument("urls", nargs="+")
    args = parser.parse_args(argumentos)

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        # Chromium no arranca como root con el sandbox activo
        os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
    banderas = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
        banderas + " --ignore-certificate-errors --mute-audio"
                   " --autoplay-policy=no-user-gesture-required").strip()

    from PySide6.QtCore import QCoreApplication, Qt, QTimer, QUrl
    from PySide6.QtWidgets import QApplication
    from PySide6.QtWebEngineCore import (QWebEnginePage, QWebEngineProfile,
                                         QWebEngineSettings, QWebEngineUrlRequestInterceptor)

    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication([sys.argv[0]])
    vistas = set()

    class Interceptor(QWebEngineUrlRequestInterceptor):
        def interceptRequest(self, info):
            url = info.requestUrl().toString()
            if url.startswith(("http://", "https://")):
                vistas.add(url)

    perfil = QWebEngineProfile()            # sin nombre = solo en memoria
    interceptor = Interceptor(perfil)
    perfil.setUrlRequestInterceptor(interceptor)
    pagina = QWebEnginePage(perfil)
    pagina.settings().setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
    pagina.certificateError.connect(lambda error: error.acceptCertificate())

    cola = list(args.urls)

    def siguiente():
        if not cola:
            app.quit()
            return
        pagina.setUrl(QUrl(cola.pop(0)))
        QTimer.singleShot(args.segundos * 1000, siguiente)

    QTimer.singleShot(0, siguiente)
    app.exec()

    sys.stdout.write(MARCA_CAPTURA + json.dumps(sorted(vistas)) + "\n")
    sys.stdout.flush()
    os._exit(0)   # evita los avisos de QtWebEngine al destruir el perfil


if __name__ == "__main__" and "--capturar" in sys.argv:
    _modo_captura(sys.argv[1:])
