"""
cierre_player.py

JavaScript que se inyecta en el player para que funcione el boton oculto
de cierre.

EL PROBLEMA
-----------
El boton tiene configurada, en todos los recursos, esta accion:

    {"TipoAccion": "Sistema.CerrarAplicacion", "NombreAplicacion": "", ...}

Pero el switch de Ciel.MPC.WebPlayer.Acciones.Sistema.EjecutarAccion solo
contempla:

    Sistema.BaseDatos, Sistema.SistemaEmail, Sistema.Alerta,
    Sistema.Expresion.Booleana, Sistema.Expresion.Cadena,
    Sistema.Variable, Sistema.LimpiarVariables

"Sistema.CerrarAplicacion" no esta en la lista. La accion llega al
despachador (se le llega a asignar timerRetraso), entra al switch y sale
sin coincidir con ningun case. Ni ejecuta ni reporta error.

LA SOLUCION
-----------
Se envuelve Acciones.Sistema.EjecutarAccion: si el TipoAccion es
"Sistema.CerrarAplicacion" se cierra la aplicacion; en cualquier otro caso
se delega en la implementacion original del player.

Asi el recurso queda tal como esta y funciona en todas las sedes, porque
todas usan el mismo TipoAccion.

Como respaldo opcional se puede enganchar tambien un listener de click
directo al div del boton (parametro con_listener), util si en alguna sede
el boton quedo sin la accion configurada.
"""

import json


PLANTILLA = r"""
(function(){
    var PANTALLA     = %(pantalla)s;
    var CONTROL      = %(control)s;
    var CON_LISTENER = %(con_listener)s;

    if (typeof Ciel === 'undefined' || !Ciel.MPC || !Ciel.MPC.WebPlayer) {
        console.error('CIERRE: el player aun no esta cargado');
        return;
    }

    // ---- Cierre efectivo ---------------------------------------------
    // Guarda contra doble disparo: la accion del recurso y el listener
    // opcional podrian llamar los dos.
    function cerrarApp(origen){
        if (window.__cierreSolicitado) {
            console.log('CIERRE: ya habia una solicitud en curso (' + origen + ')');
            return;
        }
        window.__cierreSolicitado = true;

        if (window.api && window.api.app && window.api.app.cerrar) {
            console.log('CIERRE: solicitando cierre desde ' + origen);
            window.api.app.cerrar();
        } else {
            window.__cierreSolicitado = false;
            console.error('CIERRE: window.api.app.cerrar no existe. '
                        + 'Falta registrar AppController en set_apis().');
        }
    }

    // Disponible para probar a mano desde la consola
    window.CerrarAplicacion = function(){ cerrarApp('consola'); };

    // ---- 1. Soporte de "Sistema.CerrarAplicacion" ---------------------
    // El player no implementa este TipoAccion. Se envuelve el despachador
    // conservando el comportamiento original para todo lo demas.
    var A = Ciel.MPC.WebPlayer.Acciones;
    if (A && A.Sistema && !A.Sistema.__cierreParcheado) {
        var original = A.Sistema.EjecutarAccion;

        A.Sistema.EjecutarAccion = function(n){
            try {
                if (n && n.TipoAccion === 'Sistema.CerrarAplicacion') {
                    console.log('CIERRE: accion Sistema.CerrarAplicacion "'
                                + (n.Nombre || '') + '"');
                    if (n.NombreAplicacion) {
                        console.warn('CIERRE: NombreAplicacion="'
                                     + n.NombreAplicacion
                                     + '" no se usa; se cierra el player.');
                    }
                    cerrarApp('accion del recurso');
                    return;
                }
            } catch (e) {
                console.error('CIERRE: error evaluando la accion', e);
            }
            return original.apply(this, arguments);
        };

        A.Sistema.__cierreParcheado = true;
        console.log('CIERRE: despachador Sistema.EjecutarAccion extendido '
                    + 'con Sistema.CerrarAplicacion');
    }

    // ---- 2. Respaldo opcional: listener directo en el boton -----------
    if (!CON_LISTENER) { return; }

    function engancharBoton(){
        var ctl = Ciel.MPC.WebPlayer.Utilidad.ObtenerControl(PANTALLA, CONTROL);
        if (!ctl || !ctl.DivContenedor) { return false; }
        if (ctl.__cierreEnganchado)     { return true;  }

        ctl.DivContenedor.on('click', function(){
            cerrarApp('listener del boton');
        });
        ctl.__cierreEnganchado = true;
        console.log('CIERRE: listener de respaldo agregado a "' + CONTROL + '"');
        return true;
    }

    if (!engancharBoton()) {
        var intentos = 0;
        var t = setInterval(function(){
            intentos++;
            if (engancharBoton() || intentos > 40) {
                clearInterval(t);
                if (intentos > 40) {
                    console.warn('CIERRE: no se encontro el control "'
                                 + CONTROL + '" en "' + PANTALLA + '". '
                                 + 'La accion del recurso sigue funcionando.');
                }
            }
        }, 250);
    }
})();
"""


def js_cierre(pantalla="Utilidad", control="Cerrar", con_listener=False):
    """
    Devuelve el JavaScript listo para inyectar.

    :param pantalla: nombre de la pantalla que contiene el boton
    :param control:  nombre del control (boton) de cierre
    :param con_listener: bool. True agrega ademas un listener de click
                         directo al div del boton. Solo hace falta si en
                         alguna sede el boton quedo sin la accion
                         "Sistema.CerrarAplicacion" configurada.
    :return: str. codigo JavaScript
    """
    return PLANTILLA % {
        "pantalla": json.dumps(pantalla),
        "control": json.dumps(control),
        "con_listener": "true" if con_listener else "false",
    }
