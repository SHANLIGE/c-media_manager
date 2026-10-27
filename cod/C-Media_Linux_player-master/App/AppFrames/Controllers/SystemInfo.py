import psutil
import platform
import netifaces
import datetime
import subprocess
import os

import logging
import json

from PySide6 import QtCore

from ..Event import Event

class SystemInfo(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.event = Event("")
        self.system_on = self._get_system_on()
        self.player_on = datetime.datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")
        self.SO = platform.system()
        self.version = platform.version()
        try:
            self.version = self.version[self.version.find("~")+1:self.version.find(" ")]
        except Exception as e:
            logging.warning(e)
        self.arch = platform.architecture()[0] #x64
        self.name = platform.node()
        self.ip = self._get_ip()
        self.vendor = None
        self.screens = self._get_screens()

        ##Estados
        self.disk = self._get_disks()
        self.nucleus = os.cpu_count()
        self.cpu = psutil.cpu_percent(interval=1)
        self.ram = self._get_ram()


    def _get_ip(self):

        interfaces = netifaces.interfaces()
        for interface in interfaces:
            if interface != 'lo':
                try:
                    direccion_ip = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']
                    return direccion_ip
                except KeyError:
                    pass
        return "Error en dirección IP"
    
    def _get_system_on(self):
        return datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%d/%m/%Y %I:%M:%S %p")

    def _get_screens(self):
        salida = subprocess.run(['xrandr'], capture_output=True, text=True)
        lineas = salida.stdout.splitlines()

        monitores = {}
        for i,linea in enumerate(lineas):
            if ' connected' in linea:
                nombre_monitor = linea.split()[0]
                try:
                    resolution = lineas[i+1].split()[0]
                    monitores[nombre_monitor] = resolution
                except IndexError:
                    monitores[nombre_monitor] = "NN"
        return monitores

    def _get_disks(self): 
        discos = psutil.disk_partitions(all=False)
        espacio_disponible = {}
        for disco in discos:
            if "/dev/sd" in disco.device:
                try:
                    if ("/dev/sd"+disco.device[7]) in espacio_disponible.keys():
                        espacio = psutil.disk_usage(disco.mountpoint)
                        dev = espacio_disponible["/dev/sd"+disco.device[7]]
                        dev['total'] += espacio.total/1024**2
                        dev['usado'] += espacio.used/1024**2
                        dev['libre'] = dev['total']-dev['usado']
                        dev['porcentaje_usado'] = round(dev['usado']/dev['total']*100, 2)
                        espacio_disponible["/dev/sd"+disco.device[7]] = dev
                    else:
                        espacio = psutil.disk_usage(disco.mountpoint)
                        espacio_disponible["/dev/sd"+disco.device[7]] = {
                                'montaje': disco.mountpoint,
                                'total': espacio.total/1024**2,
                                'usado': espacio.used/1024**2,
                                'libre': espacio.free/1024**2,
                                'porcentaje_usado': espacio.percent
                        }

                except PermissionError:
                    continue
        return espacio_disponible

    def _get_ram(self):
        memoria = psutil.virtual_memory()
        total_ram = memoria.total
        ram_disponible = memoria.available
        ram_usada = memoria.used
        porcentaje_ram_usada = memoria.percent

        return {
            "total": total_ram,
            "disponible": ram_disponible,
            "usada": ram_usada,
            "porcentaje_usado": porcentaje_ram_usada
        }

    QtCore.Slot()
    def get_player_info(self):
        return json.dumps({
            "s_on" : self.system_on,
            "p_on" : self.player_on,
            "SO" : self.SO,
            "version" : self.version,
            "arch" : self.arch,
            "name" : self.name,
            "IP" : self.ip,
            "vendor" : self.vendor,
            "screens" : self.screens
        })

    QtCore.Slot()
    def get_estados(self):
        self.disk = self._get_disks()
        self.nucleus = os.cpu_count()
        self.cpu = psutil.cpu_percent(interval=1)
        self.ram = self._get_ram()

        return json.dumps({
            "disk": self.disk,
            "nucleus": self.nucleus,
            "CPU": self.cpu,
            "RAM" : self.ram
        })
    
    def get_event(self):
        return self.event










