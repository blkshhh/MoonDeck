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
               "vejiga": .1, "tripa": .1, "ultimo": 0, "manchas": [], "mojado": 0.0}
NUM_BARRO = 24  # uno por cada ancla del esqueleto


class Partida:
    def __init__(self, datos, guardar):
        for clave, valor in POR_DEFECTO.items():
            datos.setdefault(clave, list(valor) if isinstance(valor, list) else valor)
        self.d, self.guardar = datos, guardar
        if len(datos.get("barro", ())) != NUM_BARRO:
            datos["barro"] = [round(max(0, 1 - datos["limpieza"]) * (.5 + (i * 7 % 10) / 10), 3) for i in range(NUM_BARRO)]
        self.espuma = [0.0] * NUM_BARRO
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
        for i, b in enumerate(d["barro"]):  # unas zonas se ensucian antes que otras
            d["barro"][i] = min(1.0, b + BAJA["limpieza"] * horas * (.5 + (i * 7 % 10) / 10))
        self._limpieza()
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

    def _limpieza(self):
        self.d["limpieza"] = 1 - sum(self.d["barro"]) / NUM_BARRO

    def frotar(self, herramienta, zonas, cuanto):
        """El baño: la esponja hace espuma y suelta el barro solo en las zonas que toca."""
        d = self.d
        if herramienta == "esponja":
            for i in zonas:
                self.espuma[i] = min(1.0, self.espuma[i] + cuanto * 1.6)
                d["barro"][i] = max(0.0, d["barro"][i] - cuanto * self.espuma[i])
        elif herramienta == "ducha":
            for i in zonas:
                self.espuma[i] = max(0.0, self.espuma[i] - cuanto * 2.5)
            d["mojado"] = min(1.0, d["mojado"] + cuanto * .12)
        elif zonas:
            d["mojado"] = max(0.0, d["mojado"] - cuanto * .3)
        self._limpieza()

    def acabar_bano(self):
        self.espuma = [0.0] * NUM_BARRO
        self.d["animo"] = min(1.0, self.d["animo"] + .15)
        self.guardar()

    def pensamiento(self):
        """Lo que le ronda la cabeza, lo más urgente primero. None si está bien."""
        d = self.d
        for clave, idea, tope in (("hambre", "hambre", .35), ("sed", "sed", .35), ("limpieza", "sucio", .45), ("animo", "cariño", .4)):
            if d[clave] < tope:
                return idea
        return None

    def aliento(self):
        """De 0 a 1: lo bien que se encuentra. Se le nota en la postura."""
        d = self.d
        return min(1.0, .35 + min(d["hambre"], d["sed"], d["animo"]) * 1.3)

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
