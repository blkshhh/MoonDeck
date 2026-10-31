"""Fondos del panel con la API de Unsplash (compartido por Linux y Windows).

Cada usuario pone su clave de acceso. Las condiciones de Unsplash piden usar sus URL
de imagen, así que las fotos no se guardan en disco: solo sus datos, en la configuración.
"""

import json
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from idioma import _

API = "https://api.unsplash.com/photos/random"
UTM = "utm_source=moondeck&utm_medium=referral"
WEB = f"https://unsplash.com/?{UTM}"
LOTE = 10          # fotos por petición: el plan gratuito permite 50 peticiones por hora
HISTORIAL = 30     # las que se recuerdan para ir hacia atrás
ESPERA_TECLEO = 3  # segundos sin escribir antes de buscar
MODOS = (("minutos", "Cada X minutos"), ("inicio", "En cada inicio"), ("manual", "Solo a mano"))
POR_DEFECTO = {"activo": False, "clave": "", "etiquetas": "", "modo": "minutos", "minutos": 15,
               "pausado": False, "historial": [], "indice": -1}


def etiquetas(texto):
    return [t.strip() for t in texto.split(",") if t.strip()]


def _foto(d):
    """Lo que hace falta de una foto de la API."""
    return {"url": d["urls"]["raw"], "autor": d["user"]["name"],
            "perfil": f"{d['user']['links']['html']}?{UTM}",
            "descarga": d["links"]["download_location"], "contada": False}


class Fondos:
    """`version` sube con cada foto nueva (y `imagen` trae sus bytes); la interfaz la vigila."""

    def __init__(self, cfg, guardar):
        for clave, valor in POR_DEFECTO.items():
            cfg.setdefault(clave, valor)
        self.cfg, self.guardar = cfg, guardar
        self.imagen = None
        self.version = 0
        self.error = ""
        self.ocupado = False
        self.tam = (1920, 1080)
        self._proximo = 0.0
        self._sin_guardar = False
        self._tecleo = 0.0

    @property
    def foto(self):
        h, i = self.cfg["historial"], self.cfg["indice"]
        return h[i] if 0 <= i < len(h) else None

    # --- órdenes -----------------------------------------------------------------

    def arrancar(self):
        if not self.cfg["activo"]:
            return
        if self.cfg["modo"] == "inicio" or not self.foto:
            self.siguiente()
        else:
            self._trabajar(self._cargar)

    def siguiente(self):
        self._trabajar(self._siguiente)

    def anterior(self):
        if self.cfg["indice"] > 0 and not self.ocupado:
            self.cfg["indice"] -= 1
            self._trabajar(self._cargar)

    def alternar_pausa(self):
        self.cfg["pausado"] = not self.cfg["pausado"]
        self._reprogramar()
        self.guardar()

    def configurar(self, **cambios):
        self.cfg.update(cambios)
        self._reprogramar()
        self.guardar()

    def escribir(self, **cambios):
        """Clave o etiquetas según se teclean: quedan apuntadas al momento, aunque se cierre
        la página, y la búsqueda nueva espera a que se deje de escribir."""
        self.cfg.update(cambios)
        self._sin_guardar = True
        self._tecleo = time.monotonic()

    def comprobar(self):
        """Llamar cada segundo desde la interfaz: cambia de fondo cuando toca y guarda lo pendiente."""
        if self._sin_guardar and not self.ocupado:
            self._sin_guardar = False
            self.guardar()
        if self._tecleo and time.monotonic() - self._tecleo >= ESPERA_TECLEO and not self.ocupado:
            self._tecleo = 0.0
            # Con otra clave o etiquetas, las fotos que aún no se han visto ya no valen.
            del self.cfg["historial"][self.cfg["indice"] + 1:]
            if self.cfg["activo"]:
                self.siguiente()
        if self.restante() == 0 and not self.ocupado:
            self.siguiente()

    def restante(self):
        """Segundos hasta el próximo cambio, o None si no hay cuenta atrás."""
        c = self.cfg
        if not c["activo"] or c["modo"] != "minutos" or c["pausado"] or not self._proximo:
            return None
        return max(0, int(self._proximo - time.monotonic()))

    # --- trabajo en segundo plano --------------------------------------------------

    def _reprogramar(self):
        self._proximo = time.monotonic() + max(1, self.cfg["minutos"]) * 60

    def _trabajar(self, fn):
        if self.ocupado:
            return
        self.ocupado = True

        def hilo():
            try:
                fn()
                self.error = ""
            except urllib.error.HTTPError as e:
                self.error = {401: _("Unsplash no acepta la clave de acceso."),
                              403: _("Límite de Unsplash alcanzado: prueba dentro de una hora."),
                              404: _("Unsplash no tiene fotos con esas etiquetas.")}.get(
                                  e.code, _("Unsplash ha fallado ({codigo}).").format(codigo=e.code))
            except (OSError, ValueError, KeyError, TypeError):
                self.error = _("No se pudo conectar con Unsplash.")
            finally:
                self._reprogramar()
                self.ocupado = False
                self.version += 1
        threading.Thread(target=hilo, daemon=True).start()

    def _siguiente(self):
        c = self.cfg
        if c["indice"] + 1 >= len(c["historial"]):
            c["historial"].extend(self._pedir_lote())
        c["indice"] += 1
        sobran = len(c["historial"]) - HISTORIAL - LOTE
        if sobran > 0:
            del c["historial"][:sobran]
            c["indice"] -= sobran
        self._cargar()

    def _pedir(self, url):
        peticion = urllib.request.Request(url, headers={
            "Authorization": f"Client-ID {self.cfg['clave']}", "Accept-Version": "v1",
            "User-Agent": "MoonDeck"})
        with urllib.request.urlopen(peticion, timeout=20) as r:
            return r.read()

    def _pedir_lote(self):
        if not self.cfg["clave"].strip():
            raise ValueError
        ancho, alto = self.tam
        datos = {"count": LOTE, "content_filter": "high",
                 "orientation": "landscape" if ancho >= alto else "portrait"}
        tags = etiquetas(self.cfg["etiquetas"])
        if tags:
            datos["query"] = random.choice(tags)  # cada lote, una de las etiquetas
        return [_foto(d) for d in json.loads(self._pedir(f"{API}?{urllib.parse.urlencode(datos)}"))]

    def _cargar(self):
        foto = self.foto
        if not foto:
            return
        ancho = max(self.tam)
        # La URL de la API se usa tal cual (conserva su ixid); solo se añade el tamaño.
        peticion = urllib.request.Request(f"{foto['url']}&w={ancho}&q=80&fm=jpg", headers={"User-Agent": "MoonDeck"})
        with urllib.request.urlopen(peticion, timeout=30) as r:
            self.imagen = r.read()
        if not foto["contada"]:  # Unsplash pide avisar cuando una foto se usa de verdad
            self._pedir(foto["descarga"])
            foto["contada"] = True
        self._sin_guardar = True  # guardar la configuración no es cosa de este hilo
