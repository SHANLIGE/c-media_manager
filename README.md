# C-Media Player Linux X86_64 

## Descripción

El propósito del desarrollo en el presente repositorio es ofrecer un reproductor de C-Media que pueda ser instalado en Ubuntu/Linux. El reproductor utiliza el control navegador de C-Media a través del cual se accede al despliegue de un Player/Windows. Además, se ofrece la posibilidad de usar impresoras seriales y lectores.

Versión actual: 2.2


## Documentos complementarios 
---
| Documento | |
|:---|:---|
| Manual Actualizado de Instalación y Configuración de C-Media Player (Versión 2.2) | `Docs/Manual Actualizado de Instalación y Configuración de C-Media Player (Versión 2.2).docx` |

## Pre-requisitos

![ci](https://img.shields.io/badge/ubuntu-24.04-red)


Qt WebEngine 6 — https://doc.qt.io/qt-6/qtwebengine-index.html


![ci](https://img.shields.io/badge/Python-3.10-3670A0?logo=python&logoColor=ffdd54)

## Información técnica ​
---
### Lenguajes

- Python 3.10
- JavaScript (Qt WebEngine / C-Media Web)
- Bash (scripts de entorno)

### Arquitectura

- Aplicación de escritorio Qt (PySide6)
- Navegador embebido con Qt WebEngine
- Módulo de periféricos (impresora tèrmica, lector de códigos)

### Patrones usados

- POO
- SOLID
- Abstracción (Interfaces)
- Arquitectura por capas

## Otros conceptos

- Hilos de fondo (daemon threads)
- Detección automática de arquitectura (`platform.machine()`)
- Monitoreo de display en tiempo real
- Variables de entorno condicionales por plataforma
- Empaquetado con PyInstaller (`C-Media_Player.spec`)


## Archivos de configuración

La app espera estos archivos en `~/.config/Ciel/C-Media_Player/`. Son indispensables para que corra el programa.

```
~/.config/Ciel/C-Media_Player/
├── configs/
│   └── config.json          -- Configuración general de la app
├── Media/
│   ├── SplashScreen.png     -- Pantalla de carga
│   └── Logo-CMedia_lx.png  -- Ícono de la ventana
└── logs/
    └── log.log              -- Archivo de logs
```

Si "Ruta" en config.json empieza con $, se trata como variable de entorno. Ejemplo: `$HOME/pantallas.json`


## Instrucciones para ejecutar en debug

```bash
cd cmediaplayerlinux/cod/C-Media_Linux_player-master
python3 -m venv entornoVirtual
source entornoVirtual/bin/activate
pip install -r requerimientos.txt
cd App
```

Ejecutar configuración:
```bash
python3 -m App.App.py --config
```

Ejecutar Player:
```bash
python3 -m App.App.py
```


## Empaquetar con PyInstaller

Se usa un archivo .spec para controlar el empaquetado:

```bash
pyinstaller CMediaPlayer.spec
```

**Importaciones requeridas (no detectados automáticamente):**

```
serial, serial.serialposix, serial.serialutil, serial.tools.list_ports,
serial.tools.list_ports_posix, PySide6.QtWebEngineCore,
PySide6.QtWebEngineWidgets, cryptography.fernet, cv2, netifaces, psutil, gtts
```


## Visuals 
---


## Autores 🖌️

- **Andrés Mauricio Gómez** (Actualización)
- **@n.luque** (Desarrollo, codificación, Bugs)
- **@v.hernadez** (Implementación de hardware)
- **@w.ramos** (Pruebas de hardware)

