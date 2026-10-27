import json
import inspect
import logging


from PySide6 import QtCore
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *


class JSBridge(QtCore.QObject):
    """
    Clase que permite la interaccipn entre la url y la aplicacion local
    :param page:  QWebEnginePage, nevegador donde se corre la url
    :param api: dic. informacion del nombre y objeto de los controladores
    """

    def __init__(self, page, api):
        """
        Constructor de clase
        :param page: QWebEnginePage, nevegador donde se corre la url
        :param api: dic. informacion del nombre y objeto de los controladores
        """
        super().__init__()
        self.page = page
        self.api = api

    @QtCore.Slot(str, str, str, int)
    def call(self, func_name, controller, param, val_id):
        """
        Llama a las funciones de los controladores y guarda los retornos o errores en un objeto del navegador
        :param func_name: str. nombre de la funcion a llamar
        :param controller: str. nombre del controlador donde se encuentra la funcion
        :param param: dic. parametros que seran enviados a la funcion
        :param id: int. identificacion del llamado de la funcion
        """
        def _call():
            try:
                func = getattr(self.api[controller], func_name, None)
                if func is None:
                    raise AttributeError(
                        "No existe la funcion '{0}' en el controlador '{1}'".format(func_name, controller)
                    )

                func_params = json.loads(param)

                if isinstance(func_params, dict):
                    args = list(func_params.values())
                elif isinstance(func_params, list):
                    args = func_params
                else:
                    args = [func_params]

                print(">>> JSBridge.call: controller={0} func={1} args={2}".format(controller, func_name, args))

                result = func(*args)

                print(">>> JSBridge.call: resultado={0}".format(result))

                result = json.dumps(result).replace('\\', '\\\\').replace('\'', '\\\'')
                code = 'window.api.returnValues["{0}"]["{1}"]["{2}"] = {{value:\'{3}\'}}'.format(
                    controller, func_name, val_id, result
                )
            except Exception as e:
                error = {
                    "message": str(e),
                }
                result = json.dumps(error).replace('\\', '\\\\').replace('\'', '\\\'')
                code = 'window.api.returnValues["{0}"]["{1}"]["{2}"] = {{isError: true, value:\'{3}\'}}'.format(
                    controller, func_name, val_id, result
                )
                logging.error(str(e))

            self.page.runJavaScript(code)

        # Se ejecuta en el hilo de la GUI para evitar errores de acceso a objetos Qt desde hilos secundarios
        QtCore.QTimer.singleShot(0, _call)

    def parse_api_js(self):
        """
        Carga la api en el navegador
        """
        def get_args(func):
            """
            Devuelve la lista de los argumentos de una funcion
            :param func: funct. funcion a extraer los argumentos
            :return: list. argumentos de la funcion
            """
            return list(inspect.getfullargspec(func).args)

        def generate_func():
            """
            Genera la api y las funciones que seran llamadas en el navegador
            :return: str. codigo JavaScript que sera ejecutado por el navegador (carga de funciones)
            """
            functions = {}
            for controllerName, controller in self.api.items():
                methods = {}
                for name in dir(controller):
                    if inspect.ismethod(getattr(controller, name)) and not name.startswith('_'):
                        methods[name] = get_args(getattr(controller, name))[1:]
                functions[controllerName] = methods
            funs = []
            for controller, methods in functions.items():
                method = [{"func": name, "params":params} for name, params in methods.items()]
                funs.append({"controller": controller, "methods":method})
                print("Puente activado")
            #se modifico conexion con puente y se actualizo la funcion de llamada a imprimir
            js = """window.api = {
                        _createApi: function(controllerList){
                        for(var i = 0; i < controllerList.length; i++){
                            var methodList = controllerList[i].methods;
                            var controller = controllerList[i].controller; 
                            window.api[controller] = {}; 
                            window.api.returnValues[controller] = {}; 
                            for(var j = 0; j < methodList.length; j++){
                            var funcName = methodList[j].func; 
                            // NOTA: antes se generaba cada funcion con
                            // "new Function(params, funcBody)", que es
                            // equivalente a eval() y queda bloqueado por
                            // Content-Security-Policy sin 'unsafe-eval'
                            // (falla silenciosamente y window.api.* nunca
                            // se crea). Se reemplaza por un closure normal,
                            // que no requiere evaluar strings como codigo.
                            window.api[controller][funcName] = (function(funcName, controller){
                                return function(){
                                    var id = (Math.random()+'').substring(10);
                                    var promise = new Promise(function(resolve, reject){
                                        window.api._checkValue(funcName, controller, resolve, reject, id);
                                    });
                                    window.api._bridge.call(funcName, controller, arguments, id);
                                    return promise;
                                };
                            })(funcName, controller);
                            window.api.returnValues[controller][funcName] = {}
                            };
                        };
                    },
                _bridge:{
                        _channel: null,
                        _queue: [],
                        _ready: false,
                        _init: function(){
                            if(window.api._bridge._ready) return;
                            new QWebChannel(qt.webChannelTransport, function(channel) {
                                window.api._bridge._channel = channel;
                                window.api._bridge._ready = true;
                                window.speak_func = channel.objects.speech ? channel.objects.speech.start : null;
                                var q = window.api._bridge._queue;
                                window.api._bridge._queue = [];
                                for(var i=0;i<q.length;i++) q[i](channel);
                            });
                        },
                        call: function (funcName, controller, params, id){
                            var doCall = function(channel){
                                console.log(">>> JSBridge JS: enviando a Python ->", controller, funcName, params);
                                channel.objects.external.call(funcName, controller, JSON.stringify(params), id);
                            };
                            if(window.api._bridge._ready){
                                doCall(window.api._bridge._channel);
                            } else {
                                window.api._bridge._queue.push(doCall);
                                window.api._bridge._init();
                            }
                        }
                    },
                _checkValue: function(funcName, controller, resolve, reject, id){
                        
                        var check = setInterval(function(){
                            var returnObj = window.api.returnValues[controller][funcName][id];
                            if(returnObj){
                                var value = returnObj.value;
                                var isError = returnObj.isError;
                                
                                delete window.api.returnValues[controller][funcName][id];

                                clearInterval(check);
                                if (isError){
                                    var pyError = JSON.parse(value);
                                    var error = new Error(pyError.message);
                                    reject(error);
                                } else {
                                    resolve(JSON.parse(value));
                                }
                            }
                        }, 100)
                    }, 
                    returnValues: {}
            }
	    window.api._createApi(%s);

          window.external = {
    lanzarMensaje: function(msg){

        console.log("external funcionando");
 
        window.api.printer.imprimir(msg);
        
    }
};
    
        function updateOnlineStatus () {
            if(navigator.onLine){
                window.api.network.connected()
            }else{
                window.api.network.disconnected()
            }
        }

        window.addEventListener('online', updateOnlineStatus);
        window.addEventListener('offline', updateOnlineStatus);
        window.speechSynthesis = window.api.speech;
        window.api._bridge._init();

        // ------------------------------------------------------------------
        // Cola de sintesis de voz
        // ------------------------------------------------------------------
        // ANTES: la cola era "var queue = []", una variable de closure.
        // Python intentaba vaciarla con awake_js("window.queue = []"), lo
        // que solo creaba una global NUEVA y no tocaba la del closure. La
        // cola nunca se vaciaba, asi que cada speak() enviaba el arreglo
        // completo: la segunda locucion mandaba dos elementos, la tercera
        // tres, y se repetian locuciones ya dichas.
        //
        // AHORA: la cola vive en window.__cielSpeechQueue, que Python si
        // puede alcanzar. Se vacia con length = 0 para conservar el mismo
        // objeto; si se reasignara con = [] se crearia otro arreglo y
        // Python seguiria limpiando el anterior.
        window.__cielSpeechQueue = window.__cielSpeechQueue || [];

        window.speechSynthesis.speak = function(speech){
            // Solo se envia el texto: el objeto SpeechSynthesisUtterance
            // completo no viaja bien por el WebChannel.
            window.__cielSpeechQueue.push({
                text: (speech && speech.text) ? String(speech.text) : String(speech || "")
            });
            if (window.speak_func) {
                window.speak_func(window.__cielSpeechQueue);
            } else {
                console.warn("VOZ: window.speak_func no esta disponible todavia");
            }
        };

        window.speechSynthesis.cancel = function(){
            window.__cielSpeechQueue.length = 0;
            window.api.speech.cancel_speech();
        };

        // Se agrega compatibilidad con navegadores  

        // \\r\\n.
        if (typeof window.SpeechSynthesisUtterance === 'undefined') {
            window.SpeechSynthesisUtterance = function (text) {
                this.text = text;
            };
        }

            """
            print("Generando funciones para el puente JSBridge")
            return js % funs
        return generate_func()
        
