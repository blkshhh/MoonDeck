"""La partida de los perros: necesidades, manchas y lo que se le hace (sin dibujo ni ventanas).

Se guarda en el config (app.config["perros"]). El tiempo pasa aunque MoonDeck esté cerrado, con
un tope para que una semana fuera no se note más que un día.
"""

import time

TOPE_FUERA = 24 * 3600
# Lo que baja por hora, de 1 (perfecto) a 0
BAJA = {"hambre": .12, "sed": .16, "limpieza": .04, "animo": .08}
SUBE_VEJIGA, SUBE_TRIPA = .22, .1
POR_DEFECTO = {"diseno": "bizcocho", "fuera": True, "hambre": .8, "sed": .8, "limpieza": .7, "animo": .8,
               "vejiga": .1, "tripa": .1, "ultimo": 0, "manchas": []}


class Partida:
    def __init__(self, datos, guardar):
        for clave, valor in POR_DEFECTO.items():
            datos.setdefault(clave, list(valor) if isinstance(valor, list) else valor)
        self.d, self.guardar = datos, guardar
        if not datos["ultimo"]:
            datos["ultimo"] = time.time()
        self.avanzar()

    def avanzar(self):
        """Devuelve "pis" o "caca" si no aguanta más."""
        d, ahora = self.d, time.time()
        horas = min(max(ahora - d["ultimo"], 0), TOPE_FUERA) / 3600
        d["ultimo"] = ahora
        for clave, baja in BAJA.items():
            d[clave] = max(0.0, d[clave] - baja * horas)
        if d["hambre"] < .25 or d["sed"] < .25:
            d["animo"] = max(0.0, d["animo"] - .1 * horas)
        d["vejiga"] = min(1.0, d["vejiga"] + SUBE_VEJIGA * horas)
        d["tripa"] = min(1.0, d["tripa"] + SUBE_TRIPA * horas)
        return "pis" if d["vejiga"] >= 1 else "caca" if d["tripa"] >= 1 else None

    def _sube(self, clave, cuanto):
        self.d[clave] = min(1.0, self.d[clave] + cuanto)
        self.guardar()

    def comer(self):
        self._sube("hambre", .4)
        self.d["tripa"] = min(1.0, self.d["tripa"] + .08)

    def beber(self):
        self._sube("sed", .5)
        self.d["vejiga"] = min(1.0, self.d["vejiga"] + .1)

    def lavar(self):
        self._sube("limpieza", 1)

    def acariciar(self, cuanto=.01):
        self.d["animo"] = min(1.0, self.d["animo"] + cuanto)

    def mancha(self, tipo, x, y):
        self.d["vejiga" if tipo == "pis" else "tripa"] = 0.0
        self.d["manchas"].append({"tipo": tipo, "x": round(x), "y": round(y)})
        self.guardar()

    def quitar_mancha(self, mancha):
        if mancha in self.d["manchas"]:
            self.d["manchas"].remove(mancha)
            self.d["animo"] = min(1.0, self.d["animo"] + .05)
            self.guardar()
