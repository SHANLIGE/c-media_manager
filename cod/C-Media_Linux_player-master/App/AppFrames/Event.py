import json
import logging

from PySide6.QtCore import QMetaObject, Qt, Q_ARG


class Event(object):
    """
    Envio de eventos desde Python hacia el player web.
    """

    BASE_JS = "Ciel.MPC.WebPlayer.Controles."

    # Orden de preferencia al resolver el lector activo.
    _LISTA_LECTORES_JS = (
        "[O.Honeywell,O.Newland,O.NSTAR,O.RTScan,O.MAGUELLAN,O.SwellA100,"
        "(O.CODE&&O.CODE.CR1021),(O.Motorola&&O.Motorola.DS9208)]"
    )

    MAX_QUEUE = 200

    def __init__(self, nombre_js):
        self.isLoaded = False
        self.queue = []
        self.value = False
        self.nombre_js = nombre_js
        self.function = ""
        self.params = ""
        self.page = None

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    @staticmethod
    def js_string(valor):
        """Literal string de JavaScript, con comillas y escapes."""
        if valor is None:
            valor = ""
        return json.dumps(str(valor), ensure_ascii=False)

    @staticmethod
    def js_object(dic):
        """Literal objeto de JavaScript a partir de un dict."""
        return json.dumps(dic or {}, ensure_ascii=False)

    @staticmethod
    def encode_documento(doc):
        """
        Encoding del player para las funciones ESTATICAS
        (EstablecerJsonDocumento a nivel de rama).

        Se conserva por compatibilidad, pero awake_documento() ya no lo
        necesita porque llama al metodo de instancia.
        """
        s = json.dumps(doc or {}, ensure_ascii=False, separators=(',', ':'))
        return s.replace('{', '$#$').replace('}', '#$#').replace(',', '%#')

    # ------------------------------------------------------------------
    # Construccion de JS
    # ------------------------------------------------------------------

    def _wrap(self, cuerpo):
        """Envuelve en try/catch para que nada se pierda en silencio."""
        return "try{{{0}}}catch(e){{console.error('EVENT ERROR:',e.message,{1});}}".format(
            cuerpo, json.dumps(cuerpo)
        )

    def _build_js(self, function, params):
        """Llamada directa sobre self.nombre_js (modo heredado)."""
        partes = [p if isinstance(p, str) else str(p) for p in (params or [])]
        llamada = "{0}{1}.{2}({3})".format(
            self.BASE_JS, self.nombre_js, function, ",".join(partes)
        )
        return self._wrap(llamada)

    def _build_js_lector(self, metodo, arg_js, acciones_key=""):
        """
        Resuelve el lector a usar y llama el metodo sobre su instancia.

        """
        cuerpo = (
            "var O=Ciel.MPC.WebPlayer.Controles.Omnidireccional,"
            "L={lista},C=[],i,ob,n,best=null,bn=-1,k={key};"
            "for(i=0;i<L.length;i++){{if(L[i]&&L[i].controlActual)"
            "{{C.push(L[i].controlActual);}}}}"
            "if(!C.length){{console.error('EVENT: ningun lector "
            "omnidireccional registrado en este recurso');return;}}"
            "for(i=0;i<C.length;i++){{ob=C[i].ObjetoBase||{{}};"
            "n=k?((ob[k]||[]).length):0;"
            "console.log('EVENT candidato: '+C[i].Nombre+'  '+k+'='+n);"
            "if(n>bn){{bn=n;best=C[i];}}}}"
            "if(k&&bn<=0){{console.warn('EVENT: ningun control tiene '+k+"
            "' configurado. Se usa '+best.Nombre+' pero el player no "
            "ejecutara acciones.');}}"
            "if(typeof best.{metodo}!=='function'){{console.error("
            "'EVENT: '+best.Nombre+' no expone {metodo}');return;}}"
            "console.log('EVENT -> '+best.Nombre+'.{metodo}');"
            "best.{metodo}({arg});"
        ).format(
            lista=self._LISTA_LECTORES_JS,
            key=json.dumps(acciones_key),
            metodo=metodo,
            arg=arg_js,
        )

        return self._wrap("(function(){" + cuerpo + "})()")

    # ------------------------------------------------------------------
    # Envio
    # ------------------------------------------------------------------

    def _run(self, js):
        """
        Ejecuta en el hilo de Qt, o encola si el player no esta listo.

        Siempre con invokeMethod + QueuedConnection: el lector corre en un
        hilo de puerto serial y una llamada directa a runJavaScript desde
        otro hilo puede no ejecutarse nunca.
        """
        if self.isLoaded and self.page:
            QMetaObject.invokeMethod(
                self.page,
                "ejecutarJavaScript",
                Qt.QueuedConnection,
                Q_ARG(str, js),
            )
            return True

        if len(self.queue) >= self.MAX_QUEUE:
            self.queue.pop(0)

        self.queue.append(js)
        logging.info("Player no listo, evento encolado (%d en cola)", len(self.queue))
        return False

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------

    def awake_js(self, js):
        return self._run(js)

    def awake(self, function, params):
        """
        Modo heredado: llama sobre self.nombre_js.

        Solo funciona si el recurso trae exactamente ese control. Para los
        lectores conviene awake_documento / awake_codigo.
        """
        self.value = True
        self.function = function
        self.params = params
        enviado = self._run(self._build_js(function, params))
        self.clear()
        return enviado

    # Arreglo de acciones que ejecuta el player para cada TipoDocumento.
    ACCIONES_POR_TIPO = {
        "0": "AccionesAlCapturarCedulaColombina",
        "1": "AccionesAlCapturarCedulaExtranjeria",
        "2": "AccionesAlCapturarTarjetaIdentidad",
        "3": "AccionesAlCapturarPasaporte",
    }

    def awake_lector(self, metodo, arg_js, acciones_key=""):
        """Llama 'metodo' sobre el lector mas apropiado del recurso."""
        return self._run(self._build_js_lector(metodo, arg_js, acciones_key))

    def awake_documento(self, doc):
        """
        Dispara la ruta de documento de identidad.

        Segun TipoDocumento el player ejecuta:
            "0" -> AccionesAlCapturarCedulaColombina
            "1" -> AccionesAlCapturarCedulaExtranjeria
            "2" -> AccionesAlCapturarTarjetaIdentidad
            "3" -> AccionesAlCapturarPasaporte   (solo Newland)

        Cualquier otro valor no entra en ningun case y no hace nada.
        """
        doc = dict(doc or {})
        tipo = str(doc.get("TipoDocumento", "0"))
        doc["TipoDocumento"] = tipo

        # El player hace n.FechaDeNacimiento.slice(0,10): si viene vacia
        # lanza TypeError antes de ejecutar las acciones.
        if not doc.get("FechaDeNacimiento"):
            doc["FechaDeNacimiento"] = "01/01/1900"

        for k, v in list(doc.items()):
            doc[k] = "" if v is None else str(v)

        clave = self.ACCIONES_POR_TIPO.get(tipo, "")
        return self.awake_lector(
            "EstablecerJsonDocumento", self.js_object(doc), clave
        )

    def awake_codigo(self, codigo):
        """
        Ruta de codigo generico.

        Requiere AccionesAlCapturarCodigo poblado en el control elegido.
        """
        return self.awake_lector(
            "EstablecerCodigo", self.js_string(codigo), "AccionesAlCapturarCodigo"
        )

    def notificar_error(self, mensaje):
        """
        Notifica un error al player, que lo muestra en pantalla y lo loguea
        en la consola de JS.
        """
        cuerpo = (
            "var m={msg};console.warn('LECTOR:',m);"
            "if(typeof window.LectorNotificarError==='function')"
            "{{window.LectorNotificarError(m);}}"
        ).format(msg=self.js_string(mensaje))
        return self._run(self._wrap("(function(){" + cuerpo + "})()"))

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------

    def clear(self):
        self.value = False
        self.function = ""
        self.params = ""

    def get(self):
        return self.value

    def set_page(self, page):
        self.page = page
        self.isLoaded = False

    def loaded(self):
        self.isLoaded = True

        if not self.page:
            logging.warning("loaded() sin pagina asignada")
            self.isLoaded = False
            return

        pendientes = list(self.queue)
        self.queue = []
        for js in pendientes:
            QMetaObject.invokeMethod(
                self.page,
                "ejecutarJavaScript",
                Qt.QueuedConnection,
                Q_ARG(str, js),
            )

    def unloaded(self):
        """
        Marca el player como no listo y vacia la cola de eventos.
        """
        self.isLoaded = False