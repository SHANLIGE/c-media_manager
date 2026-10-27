"""
Diagnostico y mapeo del tactil para C-Media Player.

El problema: en X11 una pantalla tactil mapea su superficie sobre TODO el
escritorio virtual, no sobre un monitor. Con un solo monitor la relacion es
1 a 1 y todo funciona. Al conectar un segundo monitor el escritorio pasa a
medir, por ejemplo, 2732x768 en vez de 1366x768, y el tactil sigue repartiendo
sus coordenadas sobre ese ancho total: tocar el centro fisico de la pantalla
mueve el cursor al borde entre los dos monitores.

Por eso el tactil "deja de funcionar" justo al agregar mas pantallas.

Uso:
    python3 mapear_tactil.py                 # solo diagnostico
    python3 mapear_tactil.py --mapear DP-2   # mapea el tactil a ese monitor
"""

import subprocess
import sys
import re


def ejecutar(comando):
    """
    Ejecuta un comando y devuelve su salida
    :param comando: list[str]
    :return: str
    """
    try:
        return subprocess.run(comando, capture_output=True, text=True,
                              timeout=10).stdout
    except Exception as e:
        print(f"No se pudo ejecutar {' '.join(comando)}: {e}")
        return ""


def listar_dispositivos_tactiles():
    """
    Busca dispositivos de entrada que parezcan pantallas tactiles
    :return: list[dict]. [{"id": str, "nombre": str}, ...]
    """
    salida = ejecutar(["xinput", "list"])
    dispositivos = []

    for linea in salida.splitlines():
        if "slave" not in linea or "pointer" not in linea:
            continue

        coincidencia = re.search(r"↳\s+(.+?)\s+id=(\d+)", linea)
        if not coincidencia:
            continue

        nombre = coincidencia.group(1).strip()
        identificador = coincidencia.group(2)

        # Nombres tipicos de paneles tactiles
        clave = nombre.lower()
        if any(t in clave for t in ["touch", "tactil", "táctil", "elan",
                                    "egalax", "ilitek", "goodix", "silead",
                                    "digitizer", "hid"]):
            dispositivos.append({"id": identificador, "nombre": nombre})

    return dispositivos


def listar_salidas():
    """
    Salidas de video conectadas segun xrandr
    :return: list[dict]. [{"nombre": str, "geometria": str}, ...]
    """
    salida = ejecutar(["xrandr", "--query"])
    conectadas = []

    for linea in salida.splitlines():
        if " connected" not in linea:
            continue
        nombre = linea.split()[0]
        geo = re.search(r"(\d+x\d+\+\d+\+\d+)", linea)
        conectadas.append({"nombre": nombre,
                           "geometria": geo.group(1) if geo else "?"})

    return conectadas


def diagnostico():
    """
    Muestra el estado del tactil y los monitores
    """
    print("=" * 70)
    print("SALIDAS DE VIDEO CONECTADAS")
    print("=" * 70)

    salidas = listar_salidas()
    for s in salidas:
        print(f"  {s['nombre']:12} {s['geometria']}")

    print()
    print("=" * 70)
    print("DISPOSITIVOS TACTILES DETECTADOS")
    print("=" * 70)

    dispositivos = listar_dispositivos_tactiles()
    if not dispositivos:
        print("  No se detecto ningun dispositivo tactil.")
        print("  Revise la lista completa con: xinput list")
    else:
        for d in dispositivos:
            print(f"  id={d['id']:4} {d['nombre']}")
            matriz = ejecutar(["xinput", "list-props", d["id"]])
            for linea in matriz.splitlines():
                if "Coordinate Transformation Matrix" in linea:
                    print(f"        {linea.strip()}")

    print()
    print("=" * 70)
    print("DIAGNOSTICO")
    print("=" * 70)

    if len(salidas) > 1 and dispositivos:
        print(f"Hay {len(salidas)} monitores y {len(dispositivos)} dispositivo(s) tactil(es).")
        print("Si el tactil no responde bien, es porque esta repartido sobre")
        print("todo el escritorio virtual en lugar de un solo monitor.")
        print()
        print("Para corregirlo, elija el monitor donde esta el panel tactil:")
        for s in salidas:
            print(f"    python3 mapear_tactil.py --mapear {s['nombre']}")
    elif len(salidas) == 1:
        print("Solo hay un monitor: el tactil deberia funcionar sin mapeo.")
    else:
        print("No hay dispositivos tactiles que mapear.")


def mapear(monitor):
    """
    Mapea todos los dispositivos tactiles a un monitor
    :param monitor: str. Nombre de la salida, por ejemplo DP-2
    """
    salidas = [s["nombre"] for s in listar_salidas()]
    if monitor not in salidas:
        print(f"El monitor '{monitor}' no esta conectado.")
        print("Conectados: " + ", ".join(salidas))
        return

    dispositivos = listar_dispositivos_tactiles()
    if not dispositivos:
        print("No se detecto ningun dispositivo tactil que mapear.")
        return

    for d in dispositivos:
        print(f"Mapeando '{d['nombre']}' (id={d['id']}) -> {monitor}")
        resultado = subprocess.run(
            ["xinput", "map-to-output", d["id"], monitor],
            capture_output=True, text=True)
        if resultado.returncode == 0:
            print("   OK")
        else:
            print("   Error: " + resultado.stderr.strip())

    print()
    print("Este mapeo se pierde al reiniciar la sesion.")
    print("Para dejarlo permanente, agregue estos comandos al arranque")
    print("(por ejemplo en ~/.xprofile o en el autostart del escritorio):")
    print()
    for d in dispositivos:
        print(f'    xinput map-to-output "{d["nombre"]}" {monitor}')


if __name__ == "__main__":
    if "--mapear" in sys.argv:
        indice = sys.argv.index("--mapear")
        if indice + 1 < len(sys.argv):
            mapear(sys.argv[indice + 1])
        else:
            print("Falta el nombre del monitor. Ejemplo: --mapear DP-2")
    else:
        diagnostico()
