"""Escena animada del widget del tiempo en el arte Cómic (compartida por Linux y Windows).

Se dibuja con el lienzo común (LienzoCairo / LienzoQt). El tiempo no se pone encima de un dibujo:
cambia la propia escena (colores, pose del guardián, lluvia que choca con el paraguas...).
Las coordenadas son las de una tarjeta de 340 x 290; Pincel las lleva al tamaño real. Lo que no
se mueve se guarda en capas (lienzo.capa), que solo se dibujan una vez.
"""

import math

from idioma import _

W, H = 340, 290
GX, GY = 242, 200  # los pies del guardián
PARAGUAS_X, PARAGUAS_Y = GX + 14, GY - 168

# (clave, nombre): el orden en que salen en Configuración
GUARDIANES = (("roca", "Musgo"), ("seta", "Boletus"), ("oveja", "Lanuda"), ("tocon", "Tocón"), ("rana", "Charca"))
GUARDIAN_POR_DEFECTO = "roca"
FPS_MIN, FPS_MAX = 10, 60


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


def _mezcla(a, b, k):
    return tuple(x + (y - x) * k for x, y in zip(a, b))


def _alfa(c, a):
    return (*c[:3], a)


def _azar(n):
    x = math.sin(n * 127.1 + 311.7) * 43758.5453
    return x - math.floor(x)


TINTA = _rgb("#17151c")
BLANCO = (1.0, 1.0, 1.0)
AMARILLO, NARANJA, ROJO = _rgb("#ffd84d"), _rgb("#ffb52e"), _rgb("#e4322b")


class _Negro(dict):
    """La paleta del contraluz del rayo: todo tinta."""

    def __missing__(self, _clave):
        return TINTA


SILUETA = _Negro()

_CLAVES = ("cieloA", "cieloB", "lejos", "cerca", "suelo", "sueloD", "tronco", "troncoD", "hoja", "hojaL", "hojaD",
           "piedra", "piedraD", "musgo", "musgoL", "musgoD", "niebla", "nube", "nubeD", "charco", "sombra")
_MOMENTOS = {
    "dia": ("#4fb7e5 #c6edf2 #86cdb0 #57b37a #8fcf5c #5fa844 #8a5a34 #5f3a20 #2f9a5b #63c46d #1f7148 "
            "#c9ad8c #9c7f63 #6fbf4a #a6dd62 #3f8f3c #eef2ec #ffffff #cfe3ee #7fd0ea #4d8f3c"),
    "tarde": ("#f2655a #ffc65c #c7657a #8e4a76 #b9893f #7d5a36 #5b2f3a #3c1f2e #7c3f63 #d86a55 #51294f "
              "#d99a78 #9c5b5e #b79a3c #f0c253 #7d6232 #ffd9b8 #ffd3a8 #e88a78 #ff9a6b #6e4d36"),
    "noche": ("#0f1b46 #2a3a7a #22407a #1b3262 #1f4a5e #143349 #2b2a4f #1a1a38 #1c4a66 #2f7286 #123352 "
              "#6a7aa6 #465584 #3a8a7c #5fbfa0 #25605f #6f86b8 #4a5a92 #2c3a6e #3c6ea8 #123042"),
}
_AJUSTE = {"sol": (0, "#ffffff"), "nubes": (.2, "#9aa8b4"), "lluvia": (.45, "#6f8296"),
           "tormenta": (.62, "#4a5670"), "niebla": (.55, "#d9e0e0"), "nieve": (.3, "#dfe9f2")}
_MANTO = {"dia": "#f7fbff", "tarde": "#ffe6d2", "noche": "#b9cdf0"}
_PARAGUAS = {"dia": ("#ffd21f", "#d9880b"), "tarde": ("#ffc02e", "#c9601f"), "noche": ("#d9b23a", "#7f6230")}
# sep, ojos y boca de cada guardián; piel, pielD, capa, capaL y capaD si no usa la paleta de la escena
_RASGOS = {
    "roca": (19, -15, 19, None),
    "seta": (17, -6, 17, "#f2e3c4 #cdb48e #d9432f #f0705a #9c2a22"),
    "oveja": (15, -12, 17, "#f6f0e2 #cfc4ae #a97f62 #c9a183 #7d5a44"),
    "tocon": (19, -10, 19, "#a9744a #7a4f2f #e3c48f #f0dcae #b8935c"),
    "rana": (27, -40, 34, "#62b84f #3f8f3c #d9eca0 #eef7c2 #a9c96e"),
}


def paleta(clima, momento, tipo):
    k, gris = _AJUSTE[clima]
    gris = _rgb(gris)
    if momento != "dia":
        k *= .5
    p = {c: _mezcla(_rgb(v), gris, k) for c, v in zip(_CLAVES, _MOMENTOS[momento].split())}
    if clima == "nieve":
        blanco = _rgb(_MANTO[momento])
        p.update(suelo=blanco, sueloD=_mezcla(blanco, p["cieloA"], .28), manto=blanco)
        p["sombra"] = p["sueloD"]
    p["lluvia"] = _rgb("#a8c4f0" if momento == "noche" else "#f2f8ff")
    p["paraguas"], p["paraguasD"] = (_rgb(c) for c in _PARAGUAS[momento])
    pieles = _RASGOS[tipo][3]
    if pieles:
        def luz(color):
            v = _mezcla(_rgb(color), gris, k * .5)
            if momento == "tarde":
                return _mezcla(v, _rgb("#e8734f"), .22)
            return _mezcla(v, _rgb("#22306e"), .55) if momento == "noche" else v
        for clave, color in zip(("piedra", "piedraD", "musgo", "musgoL", "musgoD"), pieles.split()):
            p[clave] = luz(color)
    return p


def clima_de(codigo):
    """De los códigos de Open-Meteo (tiempo.py) a las escenas que hay."""
    if codigo in (45, 48):
        return "niebla"
    if codigo >= 95:
        return "tormenta"
    if 71 <= codigo <= 77 or codigo in (85, 86):
        return "nieve"
    if codigo >= 51:
        return "lluvia"
    return "nubes" if codigo >= 2 else "sol"


def momento_de(de_dia, hora, puesta):
    """hora y puesta: "HH:MM" de la ciudad. La última hora de sol es el atardecer."""
    if not de_dia:
        return "noche"
    try:
        falta = int(puesta[:2]) * 60 + int(puesta[3:5]) - int(hora[:2]) * 60 - int(hora[3:5])
    except (TypeError, ValueError):
        return "dia"
    return "tarde" if 0 <= falta <= 60 else "dia"


def _suavizar(pts, cerrada=True):
    """Curvas entre los puntos: el lienzo solo sabe de polígonos."""
    n, sale = len(pts), []
    tramos = range(n) if cerrada else range(1, n - 1)
    if not cerrada:
        sale.append(pts[0])
    for i in tramos:
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        x0, y0 = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if not cerrada and i == 1:
            x0, y0 = a
        x1, y1 = (b[0] + c[0]) / 2, (b[1] + c[1]) / 2
        if not cerrada and i == n - 2:
            x1, y1 = c
        for t in (0, .25, .5, .75):
            q = 1 - t
            sale.append((q * q * x0 + 2 * q * t * b[0] + t * t * x1, q * q * y0 + 2 * q * t * b[1] + t * t * y1))
    if not cerrada:
        sale.append(pts[-1])
    return sale


def _ovalo(cx, cy, rx, ry, ang=0.0, n=12):
    co, se = math.cos(ang), math.sin(ang)
    sale = []
    for i in range(n):
        a = i / n * math.tau
        x, y = math.cos(a) * rx, math.sin(a) * ry
        sale.append((cx + x * co - y * se, cy + x * se + y * co))
    return sale


def _temblor(pts, semilla, a=.55):
    """El temblor del trazo a mano: cambia unas veces por segundo y da vida a la tinta."""
    return [(x + (_azar(semilla * 13 + i) - .5) * a * 2, y + (_azar(semilla * 29 + i + 7) - .5) * a * 2)
            for i, (x, y) in enumerate(pts)]


def _dentro(pts, x, y):
    si = False
    j = len(pts) - 1
    for i, (xi, yi) in enumerate(pts):
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            si = not si
        j = i
    return si


class Pincel:
    """El lienzo en coordenadas de la escena."""

    def __init__(self, l, e, ox, oy):
        self.l, self.e, self.ox, self.oy = l, e, ox, oy

    def p(self, x, y):
        return self.ox + x * self.e, self.oy + y * self.e

    def _puntos(self, pts):
        return [self.p(x, y) for x, y in pts]

    def rect(self, x, y, w, h, color):
        self.l.rect(*self.p(x, y), w * self.e, h * self.e, 0, color)

    def circulo(self, x, y, r, relleno=None, grosor=0, tinta=TINTA):
        if relleno:
            self.l.circulo(*self.p(x, y), r * self.e, relleno)
        if grosor:
            self.l.contorno(self._puntos(_ovalo(x, y, r, r, 0, 16)), grosor * self.e, tinta)

    def linea(self, pts, color=TINTA, grosor=2.0, suave=True):
        if suave and len(pts) > 2:
            pts = _suavizar(pts, False)
        self.l.contorno(self._puntos(pts), grosor * self.e, color, False)

    def poli(self, pts, relleno=None, grosor=0.0, tinta=TINTA):
        pts = self._puntos(pts)
        if relleno:
            self.l.poligono(pts, relleno)
        if grosor:
            self.l.contorno(pts, grosor * self.e, tinta)

    def forma(self, pts, relleno=None, grosor=3.0, tinta=TINTA):
        self.poli(_suavizar(pts), relleno, grosor, tinta)

    def trama(self, dentro, color, paso, x0, y0, x1, y1, radio):
        """Puntos de tamaño radio(x, y) donde dentro(x, y) sea cierto."""
        y, fila = y0, 0
        while y <= y1:
            x = x0 + (fila % 2) * paso / 2
            while x <= x1:
                r = radio(x, y)
                if r > .15 and dentro(x, y):
                    self.l.circulo(*self.p(x, y), r * self.e, color)
                x += paso
            y += paso * .86
            fila += 1

    def texto(self, texto, x, y, q, color, fuente):
        cx, cy = self.p(x, y)
        ancho = 200 * self.e
        self.l.texto(texto, cx - ancho / 2, cy - ancho / 2, ancho, ancho, q * self.e, color, "negrita", 0.5, 0.5, fuente)


# --- capas fijas --------------------------------------------------------------

_COPAS = ((20, 40, 60), (86, 28, 62), (132, 62, 40), (34, 86, 46), (96, 88, 44), (-6, 92, 36))


def _cielo(pc, p, izq, alto):
    pc.rect(izq, -alto, W - izq, alto + H + alto, p["cieloA"])
    pc.rect(izq, 150, W - izq, alto + H, p["cieloB"])
    pc.trama(lambda _x, _y: True, p["cieloB"], 8, izq, 0, W, 154, lambda _x, y: min(y / 150, 1) ** 1.25 * 5.4)


def _tierra(pc, p, clima, momento, izq, alto):
    nieve = clima == "nieve"
    abajo = H + alto
    lejos = [(izq - 80, 150), (-40, 152), (40, 128), (120, 146), (200, 124), (280, 144), (380, 126), (1200, 126), (1200, abajo), (izq - 80, abajo)]
    pc.forma(lejos, p["lejos"], 2.5)
    if nieve:
        for x, y, r in ((40, 128, 30), (200, 124, 32), (345, 130, 30)):
            pc.forma(_ovalo(x, y + 6, r, 8, 0, 10), p["manto"], 0)
    cerca = [(izq - 80, 170), (-40, 174), (60, 158), (150, 170), (240, 156), (380, 170), (1200, 170), (1200, abajo), (izq - 80, abajo)]
    pc.forma(cerca, _mezcla(p["manto"], p["cerca"], .25) if nieve else p["cerca"], 2.5)

    # El árbol
    pc.poli([(38, 196), (52, 168), (56, 96), (84, 96), (86, 168), (104, 196), (80, 192), (62, 194)], p["tronco"], 3)
    pc.linea([(66, 104), (64, 140), (68, 178)], p["troncoD"], 2.5)
    pc.linea([(76, 110), (78, 138), (74, 160)], p["troncoD"], 2)
    for x, y, r in _COPAS:
        pc.circulo(x, y, r + 3, TINTA)
    for x, y, r in _COPAS:
        pc.circulo(x, y, r, p["hoja"])
    for x, y, r in _COPAS:
        pc.forma(_ovalo(x - r * .24, y - r * .3, r * .55, r * .46, -.3, 10), p["manto"] if nieve else p["hojaL"], 0)
    en_copa = lambda x, y: any((x - a) ** 2 + (y - b) ** 2 < r * r for a, b, r in _COPAS)
    pc.trama(en_copa, p["hojaD"], 6.5, -40, 48, 180, 140, lambda _x, y: max(0, (y - 48) / 84) * 3.1)
    for x, y in ((38, 62), (100, 50), (72, 96), (132, 72), (-4, 98)):
        pc.linea([(x - 7, y), (x, y + 6), (x + 7, y)], p["hojaD"], 2)

    # El suelo
    suelo = [(izq - 80, 186), (-40, 188), (90, 177), (200, 187), (380, 177), (1200, 177), (1200, abajo), (izq - 80, abajo)]
    pc.forma(suelo, p["suelo"], 3)
    pc.trama(lambda _x, _y: True, p["sueloD"], 7, izq, 215, W + 6, H + 4, lambda _x, y: max(0, (y - 215) / 75) * 2.7)
    if not nieve:
        for i in range(24):
            x, y = _azar(i + 3) * W, 188 + _azar(i + 40) * 96
            if abs(x - GX) >= 58 or y >= 214:
                pc.linea([(x - 4, y - 5), (x, y), (x + 4, y - 6)], p["sueloD"], 2, False)
    if clima == "sol" and momento == "dia":
        for i, (x, y) in enumerate(((132, 190), (30, 208), (176, 218), (300, 240), (90, 262), (190, 272))):
            for j in range(5):
                pc.circulo(x + math.cos(j * 1.256) * 4, y - 8 + math.sin(j * 1.256) * 4, 2.5, BLANCO if i % 2 else AMARILLO, 1)
            pc.circulo(x, y - 8, 2, ROJO)
            pc.linea([(x, y - 4), (x, y + 2)], p["musgoD"], 2)
    if clima in ("lluvia", "tormenta"):
        for x, y, a, b in _CHARCOS:
            pc.forma(_ovalo(x, y, a, b, 0, 14), p["charco"], 2.5)
    if nieve:
        for x, y, a, b in ((120, 184, 42, 12), (190, 190, 26, 8), (20, 190, 34, 10)):
            pc.forma(_ovalo(x, y, a, b, 0, 12), p["manto"], 0)


_CHARCOS = ((132, 197, 42, 8), (22, 214, 30, 7), (318, 214, 26, 6), (110, 252, 64, 12), (262, 268, 44, 9))


# --- cielo que se mueve ---------------------------------------------------------

def _sol(pc, x, y, r, t, color, centro):
    giro = math.floor(t * 3) / 3 * .25
    puntas = []
    for i in range(24):
        a, d = i / 24 * math.tau + giro, r * (1.18 if i % 2 else 1.62)
        puntas.append((x + math.cos(a) * d, y + math.sin(a) * d))
    pc.poli(puntas, color, 3)
    pc.circulo(x, y, r, centro, 3)


def _luna(pc, x, y, r):
    pc.circulo(x, y, r, _rgb("#f6edc4"), 3)
    for a, b, q in ((-7, -5, 4.5), (7, 6, 3.2), (-3, 10, 2.4), (9, -8, 2.2)):
        pc.circulo(x + a, y + b, q, _rgb("#ddcea0"))


def _estrellas(pc, t):
    color = _rgb("#fff3bd")
    for i in range(22):
        x, y = _azar(i + 70) * W, _azar(i + 90) * 115
        r = 2 + (math.sin(math.floor(t * 4) / 4 * 1.7 + i * 1.3) + 1) * 1.15
        q = r * .35
        d = r * 1.7
        pc.poli([(x, y - d), (x + q, y - q), (x + d, y), (x + q, y + q), (x, y + d), (x - q, y + q), (x - d, y), (x - q, y - q)], color)


def _nube(pc, x, y, s, claro, oscuro):
    bolas = [(x + a * s, y + d * s, r * s) for a, d, r in ((-34, 6, 18), (-13, -7, 24), (14, -5, 21), (36, 7, 15), (2, 11, 22))]
    for a, d, r in bolas:
        pc.circulo(a, d, r + 2.6, TINTA)
    for a, d, r in bolas:
        pc.circulo(a, d, r, claro)
    for a, d, r in bolas[:2]:
        pc.circulo(a + r * .2, d + r * .45, r * .55, oscuro)


_NUBES = {"sol": (), "niebla": (),
          "nubes": ((10, 60, .95, 7), (190, 28, 1.05, 5), (320, 92, .8, 8)),
          "lluvia": ((0, 24, 1.3, 5), (130, 34, 1.5, 4), (270, 22, 1.35, 6), (350, 60, 1, 7)),
          "tormenta": ((0, 22, 1.45, 11), (120, 36, 1.7, 9), (250, 22, 1.5, 12), (360, 58, 1.2, 10)),
          "nieve": ((40, 26, 1.2, 3), (210, 30, 1.3, 4), (340, 54, .95, 3))}


def _nubes(pc, p, clima, t):
    oscuro = clima in ("lluvia", "tormenta")
    claro = _mezcla(p["nube"], p["nubeD"], .55) if oscuro else p["nube"]
    sombra = _mezcla(p["nubeD"], TINTA, .38 if oscuro else 0)
    for x, y, s, v in _NUBES[clima]:
        _nube(pc, (x + t * v) % (W + 180) - 90, y, s, claro, sombra)


# --- el paraguas amarillo ------------------------------------------------------

def _inclinacion(clima):
    return -.36 if clima == "tormenta" else -.27  # se inclina hacia la lluvia


def _arco(x, viento):
    d = (x - PARAGUAS_X) / 72
    return PARAGUAS_Y + 34 * d * d + viento * (x - PARAGUAS_X)


def _rima(x, viento):
    return PARAGUAS_Y + 39 + viento * (x - PARAGUAS_X)


def _paraguas(pc, p, viento):
    gajos = 6
    copa = [(PARAGUAS_X - 72 + i / 18 * 144, _arco(PARAGUAS_X - 72 + i / 18 * 144, viento)) for i in range(19)]
    for i in range(gajos, -1, -1):
        x = PARAGUAS_X - 72 + i / gajos * 144
        copa.append((x, _rima(x, viento) + 4))
        if i:
            copa.append((x - 12, _rima(x - 12, viento) - 4))
    pc.poli(copa, p["paraguas"], 3)
    # La mitad en sombra, de gajo en gajo
    for i in range(3, gajos):
        a, b = PARAGUAS_X - 72 + i / gajos * 144, PARAGUAS_X - 72 + (i + 1) / gajos * 144
        trozo = [(a + (b - a) * j / 4, _arco(a + (b - a) * j / 4, viento) + 1) for j in range(5)]
        pc.poli([*trozo, (b, _rima(b, viento) + 2), (a, _rima(a, viento) - 2)], _alfa(p["paraguasD"], .45))
    pc.poli(copa, None, 3)
    tope = _arco(PARAGUAS_X, viento)
    for i in range(1, gajos):
        x = PARAGUAS_X - 72 + i / gajos * 144
        pc.linea([(PARAGUAS_X, tope + 1), ((x + PARAGUAS_X) / 2 + (x - PARAGUAS_X) * .1, _arco((x + PARAGUAS_X) / 2, viento) + 7),
                  (x, _rima(x, viento) + 3)], TINTA, 1.9)
    pc.linea([(PARAGUAS_X, tope), (PARAGUAS_X + viento * 9, tope - 9)], TINTA, 3.4, False)
    pc.circulo(PARAGUAS_X + viento * 10, tope - 10, 2.6, p["paraguasD"], 2)


# --- el guardián ---------------------------------------------------------------

def _silueta(tipo, gx, cy):
    n, pts = 40 if tipo == "oveja" else 24, []
    for i in range(n):
        a = i / n * math.tau
        co, s = math.cos(a), math.sin(a)
        if tipo == "seta":
            pts.append((gx + co * 40 * (1.1 if s > 0 else 1), cy + 6 + s * 52))
        elif tipo == "oveja":
            r = 3.4 * math.cos(a * 16)
            pts.append((gx + co * (50 + r), cy + s * (60 + r)))
        elif tipo == "tocon":
            pts.append((gx + math.copysign(abs(co) ** .45, co) * 46, cy + math.copysign(abs(s) ** .45, s) * 58))
        elif tipo == "rana":
            pts.append((gx + co * 62 * (1 if s > 0 else .92), cy + 14 + s * (48 if s < 0 else 44)))
        else:
            ancho = 46 * (1 + s * .1 if s > 0 else 1 + s * .13)
            pts.append((gx + co * ancho, cy + s * (62 if s < 0 else 58)))
    return pts


def _adornos(pc, p, tipo, gx, cy, negro):
    if tipo == "seta":
        copa = [(gx - 66, cy - 25), (gx - 62, cy - 44), (gx - 36, cy - 62), (gx, cy - 68), (gx + 36, cy - 62), (gx + 62, cy - 44),
                (gx + 66, cy - 25), (gx + 34, cy - 21), (gx, cy - 20), (gx - 34, cy - 21)]
        pc.forma(copa, p["musgo"])
        if not negro:
            for a, b, r in ((-40, -38, 8), (-12, -52, 7), (18, -40, 10), (45, -36, 6)):
                pc.circulo(gx + a, cy + b, r, p["piedra"], 2)
    elif tipo == "oveja":
        pc.forma(_ovalo(gx - 41, cy - 20, 14, 6.5, -.5, 10), p["musgoD"], 2.6)
        pc.forma(_ovalo(gx + 41, cy - 20, 14, 6.5, .5, 10), p["musgoD"], 2.6)
        pc.forma(_ovalo(gx, cy - 6, 32, 28, 0, 14), p["musgo"], 2.6)
        if not negro:
            for a, b, r in ((-20, -42, 11), (0, -50, 13), (20, -42, 11)):
                pc.circulo(gx + a, cy + b, r, p["piedra"], 2.4)
    elif tipo == "tocon":
        pc.linea([(gx + 34, cy - 50), (gx + 46, cy - 66), (gx + 60, cy - 72)], p["piedraD"], 5)
        pc.forma(_ovalo(gx + 64, cy - 76, 11, 5, -.5, 8), p["hojaL"], 2.4)
        pc.forma(_ovalo(gx + 48, cy - 76, 10, 4.6, -1.2, 8), p["hojaL"], 2.4)
        pc.forma(_ovalo(gx, cy - 49, 44, 12, 0, 16), p["musgo"])
        if not negro:
            pc.forma(_ovalo(gx, cy - 49, 30, 8, 0, 14), None, 1.7, p["musgoD"])
            pc.forma(_ovalo(gx, cy - 49, 15, 4, 0, 10), None, 1.7, p["musgoD"])
            for a, b, q in ((-34, -26, 22), (-22, 18, 26), (32, 16, 30), (24, -28, 16)):
                pc.linea([(gx + a, cy + b), (gx + a + 2, cy + b + q / 2), (gx + a, cy + b + q)], p["piedraD"], 2)
    elif tipo == "rana":
        pc.circulo(gx - 27, cy - 40, 17, p["piedra"], 3)
        pc.circulo(gx + 27, cy - 40, 17, p["piedra"], 3)
        if not negro:
            pc.forma(_ovalo(gx, cy + 26, 40, 26, 0, 14), p["musgo"], 0)
            for a, b, r in ((-42, 4, 4), (44, 12, 5), (-30, -14, 3)):
                pc.circulo(gx + a, cy + b, r, p["piedraD"])


def _cuerpo(pc, p, E, trazo, negro):
    """Lo que no se mueve del guardián: va a una capa por cada temblor del trazo."""
    clima, tipo = E["clima"], E["tipo"]
    gx, gy, cy = GX, GY, GY - 58
    dormido = E["dormido"]
    if not negro:
        pc.forma(_ovalo(gx, gy + 2, 56, 8, 0, 14), p["sombra"], 0)
    pc.forma(_temblor(_ovalo(gx - 25, gy - 1, 15, 8), trazo), p["piedraD"])
    pc.forma(_temblor(_ovalo(gx + 25, gy - 1, 15, 8), trazo + 1), p["piedraD"])
    detras = (gx - 44, cy + 28, 10, 22, .22) if dormido else (gx - 46, cy + 18, 10, 22, .32)
    pc.forma(_temblor(_ovalo(*detras), trazo + 2), p["piedraD"])

    roca = _temblor(_silueta(tipo, gx, cy), trazo, .5)
    pc.forma(roca, p["piedra"])
    if negro:
        _adornos(pc, p, tipo, gx, cy, True)
        return
    curva = _suavizar(roca)
    pc.trama(lambda x, y: _dentro(curva, x, y), p["piedraD"], 6, gx - 56, cy - 64, gx + 66, cy + 62,
             lambda x, y: max(0, (x - gx + 8) / 54) * 3 + max(0, (y - cy - 22) / 36) * 2)
    if tipo == "roca":
        pc.linea([(gx - 30, cy + 26), (gx - 22, cy + 34), (gx - 26, cy + 44)], p["piedraD"], 2)
        pc.linea([(gx + 22, cy + 22), (gx + 16, cy + 32), (gx + 23, cy + 40)], p["piedraD"], 2)
        pc.forma(_ovalo(gx - 12, cy + 38, 5, 3.4, .2, 8), p["musgo"], 1.8)
        pc.forma(_ovalo(gx + 27, cy + 8, 4, 3, -.3, 8), p["musgo"], 1.8)
        # Manto de musgo: la parte de la roca por encima de un borde con goterones
        def borde(x):
            i = round((gx + 58 - x) / 116 * 12)
            return cy - 24 + (12 + (7 if i % 4 == 1 else 0) if i % 2 else -7) + abs(x - gx) * .12
        manto = [(x, y) for x, y in curva if y < borde(x)]
        filo = [(gx + 58 - i / 12 * 116, borde(gx + 58 - i / 12 * 116)) for i in range(13)]
        filo = [(x, y) for x, y in filo if _dentro(curva, x, y)]
        pc.forma([*sorted(manto, key=lambda q: math.atan2(q[1] - cy, q[0] - gx)), *filo], p["musgo"], 2.6)
        for a, b, q, w in ((-22, -46, 10, 6), (8, -52, 13, 6), (28, -38, 7, 5)):
            pc.forma(_ovalo(gx + a, cy + b, q, w, -.2, 8), p["musgoL"], 0)
        pc.forma(roca, None)
    else:
        _adornos(pc, p, tipo, gx, cy, False)
    if clima == "nieve":
        pc.forma([(gx - 36, cy - 37), (gx - 28, cy - 54), (gx - 8, cy - 68), (gx + 12, cy - 68), (gx + 30, cy - 54), (gx + 36, cy - 39),
                  (gx + 24, cy - 41), (gx + 15, cy - 35), (gx + 3, cy - 42), (gx - 10, cy - 34), (gx - 22, cy - 41)], p["manto"], 2.6)
        pc.forma([(gx + 22, cy + 8), (gx + 30, cy + 10), (gx + 46, cy + 24), (gx + 62, cy + 26), (gx + 58, cy + 36), (gx + 40, cy + 38),
                  (gx + 20, cy + 20)], ROJO, 2.6)
        pc.forma([(gx - 44, cy - 2), (gx, cy + 6), (gx + 45, cy - 2), (gx + 46, cy + 11), (gx, cy + 21), (gx - 45, cy + 12)], ROJO, 2.6)


def _brote(pc, p, E, t, sub):
    gx, cabeza = GX, GY - 120 - sub
    caido = 1 if E["paraguas"] or E["clima"] == "nieve" else 0
    mece = math.sin(math.floor(t * 6) / 6 * 1.8) * 3
    px, py = gx + 3 + mece + caido * 8, cabeza - 19 + caido * 8
    pc.linea([(gx + 2, cabeza + 2), (gx + 1, cabeza - 8), (px, py)], p["musgoD"], 3.4)
    pc.forma(_ovalo(px - 11, py - 4 + caido * 8, 12, 5.4, .45 + caido * .75, 8), p["musgoL"], 2.4)
    pc.forma(_ovalo(px + 11, py - 5 + caido * 8, 12, 5.4, -.45 + caido * .75, 8), p["musgoL"], 2.4)


def _cara(pc, p, E, t, sub, gx, negro):
    clima, momento, tipo = E["clima"], E["momento"], E["tipo"]
    dormido = E["dormido"]
    sep, ojo, boca, _pieles = _RASGOS[tipo]
    cy = GY - 58
    ey = cy + ojo - sub * .3
    modo = "abierto"
    if dormido:
        modo = "dormido"
    elif clima == "sol" and momento == "dia":
        modo = "feliz"
    elif clima == "sol" and momento == "tarde":
        modo = "medio"
    elif clima == "tormenta":
        modo = "susto"
    elif math.floor(t * 10) % 44 < 2:
        modo = "parpadeo"
    mx, my = {"nubes": (math.sin(t * .5) * 3.5, -3.4), "lluvia": (0, -4.4), "tormenta": (-3, -2),
              "nieve": (math.sin(t * .8) * 3, -1.5), "niebla": (math.sin(t * .6) * 4.2, 0), "sol": (2.6, 0)}[clima]
    for lado in (-1, 1):
        x = gx + lado * sep
        if modo == "feliz":
            pc.linea([(x - 9, ey + 3), (x, ey - 7), (x + 9, ey + 3)], TINTA, 3.4)
        elif modo == "dormido":
            pc.linea([(x - 9, ey - 2), (x, ey + 6), (x + 9, ey - 2)], TINTA, 3.4)
        elif modo == "parpadeo":
            pc.linea([(x - 9, ey), (x + 9, ey)], TINTA, 3.2, False)
        else:
            pc.circulo(x, ey, 13 if modo == "susto" else 11.5, BLANCO, 3)
            pc.circulo(x + mx, ey + my, 2.9 if modo == "susto" else 5.2, TINTA)
            if modo != "susto":
                pc.circulo(x + mx + 1.7, ey + my - 1.7, 1.5, BLANCO)
            if modo == "medio":
                pc.poli(_ovalo(x, ey - 6.5, 11.5, 6, 0, 12), p["piedra"])
                pc.linea([(x - 11.5, ey - 2), (x + 11.5, ey - 2)], TINTA, 3, False)
    if negro:
        return
    if modo in ("feliz", "medio", "dormido"):
        for lado in (-1, 1):
            pc.circulo(gx + lado * (sep + 9), ey + 12, 5, _rgb("#f28f7c"))
    by = ey + boca
    if tipo == "rana" and not dormido and clima != "tormenta":
        pc.linea([(gx - 34, by - 3), (gx, by + 6), (gx + 34, by - 3)], TINTA, 2.8)
    elif dormido:
        pc.circulo(gx, by, 2.2 + (sub + 2.2) * .55, TINTA)
    elif modo == "feliz":
        pc.forma([(gx - 9, by - 2), (gx + 9, by - 2), (gx, by + 9)], _rgb("#a23c34"), 2.6)
    elif clima == "tormenta":
        pc.linea([(gx - 9, by + 2), (gx - 5, by - 1), (gx - 1, by + 2), (gx + 3, by - 1), (gx + 7, by + 2)], TINTA, 2.5, False)
    elif clima in ("niebla", "nubes"):
        pc.linea([(gx - 4, by), (gx + 4, by)], TINTA, 2.8, False)
    else:
        pc.linea([(gx - 7, by - 2), (gx, by + 3), (gx + 7, by - 2)], TINTA, 2.8)


def _brazos(pc, p, E, t, gx, negro):
    cy = GY - 58
    if E["paraguas"]:
        # El palo sale del centro del paraguas; la mano lo agarra abajo, al lado del cuerpo.
        viento = _inclinacion(E["clima"])
        tope = _arco(PARAGUAS_X, viento)
        mx, my = PARAGUAS_X - viento * (cy + 16 - tope), cy + 16
        pc.linea([(PARAGUAS_X, tope), (mx, my)], TINTA, 4.4, False)
        pc.linea([(mx, my), (mx + 2, my + 13), (mx - 4, my + 21), (mx - 11, my + 17)], TINTA, 4.4)
        if E["clima"] == "tormenta":
            viento += math.sin(math.floor(t * 8) * 1.1) * .035
        _paraguas(pc, p, viento)
        pc.forma(_ovalo(gx + 45, cy + 12, 10, 21, -.42), p["piedra"])
        pc.circulo(mx, my, 7.5, p["piedra"], 3)
    elif E["farol"]:
        mx, my = gx + 56, cy + 22
        cuelga = math.sin(t * 1.6) * 2
        pc.forma(_ovalo(gx + 49, cy + 8, 10, 20, -.55), p["piedra"])
        fx, fy = mx + 4 + cuelga, my + 27
        if not negro:
            brillo = 26 + math.floor(t * 7) % 3 * 2
            pc.circulo(fx, fy, brillo + 16, _alfa(AMARILLO, .28))
            pc.circulo(fx, fy, brillo, _alfa(_rgb("#ffe995"), .4))
        pc.linea([(mx, my), (fx, fy - 15)], TINTA, 2.2, False)
        pc.forma(_ovalo(fx, fy, 9, 12.5, 0, 10), AMARILLO, 2.8)
        pc.linea([(fx - 6, fy - 12), (fx + 6, fy - 12)], TINTA, 3, False)
        pc.linea([(fx - 6, fy + 13), (fx + 6, fy + 13)], TINTA, 3, False)
    else:
        a = (gx + 44, cy + 28, 10, 22, -.22) if E["dormido"] else (gx + 46, cy + 18, 10, 22, -.32)
        pc.forma(_ovalo(*a), p["piedra"])


# --- lo que pasa delante y detrás ----------------------------------------------

def _gotas(n, semilla, inclina, clima, fondo):
    viento, sale = _inclinacion(clima), []
    for i in range(n):
        v = (220 if fondo else 340) + _azar(i + semilla) * 130
        ph = _azar(i + semilla + 50) * 400
        x0 = _azar(i + semilla + 100) * (W + 130) - 105
        meta = 196 + _azar(i + 4) * 14 if fondo else 182 + _azar(i + semilla + 9) * 104
        if not fondo:
            for y in range(0, int(meta), 2):
                x = x0 + y * inclina
                if PARAGUAS_X - 72 < x < PARAGUAS_X + 72 and y >= _arco(x, viento):
                    meta = y
                    break
        sale.append((x0, v, ph, meta, (9 if fondo else 15) + _azar(i + 200) * 9))
    return sale


def _lluvia(pc, gotas, t, inclina, color, grosor):
    l, e, ox, oy = pc.l, pc.e, pc.ox, pc.oy
    for x0, v, ph, meta, largo in gotas:
        y = (ph + t * v) % 400
        if y < meta:
            x = x0 + y * inclina
            l.linea(ox + x * e, oy + y * e, ox + (x - largo * inclina) * e, oy + (y - largo) * e, grosor * e, color, True)
        elif y < meta + v * .11:
            x, y = x0 + meta * inclina, meta
            pc.linea([(x - 6, y - 1), (x - 3, y - 6)], color, 2, False)
            pc.linea([(x + 6, y - 1), (x + 3, y - 6)], color, 2, False)
            pc.linea([(x, y - 2), (x, y - 8)], color, 2, False)


def _ondas(pc, t):
    for i, (x, y, a, _b) in enumerate(_CHARCOS):
        for n in range(2):
            f = (math.floor(t * 8) / 8 * .8 + _azar(i) + n * .5) % 1
            if f > .02:
                pc.poli(_ovalo(x + (i - 2) * 6, y, a * .7 * f, a * .7 * f * .24, 0, 14), None, 1.6, _alfa(BLANCO, 1 - f))


def _goteo(pc, clima, t):
    viento = _inclinacion(clima)
    for x, d in ((PARAGUAS_X - 72, 0), (PARAGUAS_X + 72, .4), (PARAGUAS_X - 24, .75), (PARAGUAS_X + 24, .2)):
        f = (t * .9 + d) % 1
        if abs(x - PARAGUAS_X) < 30 and f > .4:
            continue  # las de en medio caen sobre el guardián y se acaban
        y0 = _rima(x, viento) + 5
        y = y0 + f * f * (GY - y0)
        pc.poli([(x, y - 5), (x + 3, y + 1), (x, y + 3.5), (x - 3, y + 1)], _rgb("#d9f1ff"), 1.8)


def _nieve(pc, t, n, semilla, grande):
    for i in range(n):
        v = 16 + _azar(i + semilla) * 24
        y = (_azar(i + semilla + 7) * (H + 24) + t * v) % (H + 24) - 12
        x = (_azar(i + semilla + 3) * (W + 30) + math.sin(t * .8 + i) * 13 + t * 4) % (W + 30) - 15
        if grande and i % 3 == 0:
            pc.circulo(x, y, 3 + _azar(i) * 2.2, BLANCO, 1.6)
        else:
            pc.circulo(x, y, 2.4 if grande else 1.6, BLANCO)


def _banda_niebla(pc, y, v, t, color):
    d = t * v % 44
    pts = [(-60 + i * 22 + d, y + (-11 if i % 2 else 10)) for i in range(22)]
    pc.forma([*pts, (W + 80, y + 54), (-70, y + 54)], color, 0)


def _mariposa(pc, t):
    a = t * .9
    x, y = GX + math.cos(a) * 36, GY - 142 + math.sin(a * 2) * 13
    ab = 8 if math.floor(t * 10) % 2 else 4.5
    color = _rgb("#ff8a3d")
    pc.poli([(x, y), (x - ab, y - 6), (x - ab, y + 5)], color, 1.5)
    pc.poli([(x, y), (x + ab, y - 6), (x + ab, y + 5)], color, 1.5)


def _zetas(pc, t, fuente):
    for i in range(3):
        f = (t * .24 + i / 3) % 1
        x, y = GX - 54 - f * 28 + math.sin(f * 7) * 5, GY - 92 - f * 56
        pc.texto("Z", x + 1.5, y + 1.5, 15 + f * 15, TINTA, fuente)
        pc.texto("Z", x, y, 15 + f * 15, _rgb("#fff3bd"), fuente)


def _luciernagas(pc, t):
    for i in range(9):
        if math.floor(t * 3 + i * 1.7) % 4 == 0:
            continue
        x = 18 + _azar(i + 5) * 300 + math.sin(t * .7 + i * 2) * 15
        y = 118 + _azar(i + 15) * 82 + math.cos(t * .9 + i) * 10
        pc.circulo(x, y, 6.5, _rgb("#fff27a") + (.35,))
        pc.circulo(x, y, 2.2, _rgb("#fffbc4"))


def _vaho(pc, t):
    f = t * .42 % 1
    if f <= .75:
        pc.forma(_ovalo(GX + 7 + f * 20, GY - 52 - f * 20, 4 + f * 8, 3 + f * 6, 0, 8), _alfa(BLANCO, 1 - f), 1.8, _alfa(TINTA, 1 - f))


def _rayo(pc, x):
    pc.poli([(x, -6), (x + 22, -6), (x + 8, 42), (x + 28, 42), (x - 8, 112), (x + 2, 60), (x - 18, 60)], _rgb("#ffe45c"), 3)


def _estallido(pc, x, y, r, q, fuente):
    pts = []
    for i in range(18):
        a, d = i / 18 * math.tau, r * (.66 if i % 2 else 1) * (1 + _azar(i) * .16)
        pts.append((x + math.cos(a) * d * 1.3, y + math.sin(a) * d))
    pc.poli(pts, AMARILLO, 3)
    texto = _("¡BRRUM!")
    pc.texto(texto, x + 1.5, y + 2, q, TINTA, fuente)
    pc.texto(texto, x, y, q, ROJO, fuente)


class Escena:
    """Una escena. Quien la pinta guarda una y le pasa el tiempo que hace con poner()."""

    def __init__(self):
        self.E = None
        self.gotas = self.gotas_fondo = ()
        self.inclina = .12
        self.poner("nubes", "dia", GUARDIAN_POR_DEFECTO)

    def poner(self, clima, momento, tipo):
        if tipo not in _RASGOS:
            tipo = GUARDIAN_POR_DEFECTO
        E = self.E
        if E and (E["clima"], E["momento"], E["tipo"]) == (clima, momento, tipo):
            return
        paraguas = clima in ("lluvia", "tormenta")
        dormido = momento == "noche" and clima == "sol"
        self.E = {"clima": clima, "momento": momento, "tipo": tipo, "paraguas": paraguas, "dormido": dormido,
                  "farol": clima == "niebla" or (momento == "noche" and not dormido)}
        self.p = paleta(clima, momento, tipo)
        self.inclina = .34 if clima == "tormenta" else .12
        if paraguas:
            self.gotas = _gotas(95 if clima == "tormenta" else 72, 5, self.inclina, clima, False)
            self.gotas_fondo = _gotas(60, 900, self.inclina, clima, True)

    def pintar(self, l, x, y, w, h, suelo, t, cartelas=(), papel=(1, 1, 1), tinta=TINTA, fuente=None):
        """Llena el rectángulo x, y, w, h. suelo: la altura (en la tarjeta) donde pisa el guardián.
        cartelas: rectángulos de papel para los textos, con los colores del tema."""
        E, p = self.E, self.p
        clima, momento, tipo = E["clima"], E["momento"], E["tipo"]
        e = min(w / W, max(suelo - y, 1) / 170)
        ox, oy = x + w - W * e, suelo - GY * e
        pc = Pincel(l, e, ox, oy)
        izq, alto = -ox / e - 1, H * 2

        def capa(nombre, dibujar):
            clave = ("escena", nombre, clima, momento, tipo, round(e, 3), round(oy), w, h)
            l.capa(clave, x, y, w, h, lambda otro: dibujar(Pincel(otro, e, ox - x, oy - y)))

        ciclo = t % 6.5
        flash = clima == "tormenta" and (ciclo < .22 or .36 < ciclo < .52)
        l.recortar(x, y, w, h, 0)
        if flash:
            l.rect(x, y, w, h, 0, _rgb("#fff6c8"))
            _rayo(pc, 118 + math.floor(t / 6.5) % 3 * 40)
            capa("tierra negra", lambda q: _tierra(q, SILUETA, clima, momento, izq, alto))
        else:
            capa("cielo", lambda q: _cielo(q, p, izq, alto))
            if momento == "noche" and clima in ("sol", "nubes"):
                _estrellas(pc, t)
            if clima in ("sol", "nubes"):
                if momento == "dia":
                    _sol(pc, 300, 42, 23, t, NARANJA, AMARILLO)
                elif momento == "tarde":
                    _sol(pc, 166, 128, 30, t, NARANJA, _rgb("#ffe07a"))
                else:
                    _luna(pc, 298, 44, 23)
            if clima == "nubes":
                _nube(pc, 294, 62, 1.15, p["nube"], p["nubeD"])
            _nubes(pc, p, clima, t)
            if E["paraguas"]:
                _lluvia(pc, self.gotas_fondo, t, self.inclina, _mezcla(p["lluvia"], p["cieloA"], .35), 1.3)
            elif clima == "nieve":
                _nieve(pc, t, 26, 60, False)
            capa("tierra", lambda q: _tierra(q, p, clima, momento, izq, alto))
        if clima == "niebla":
            _banda_niebla(pc, 84, 7, t, _alfa(p["niebla"], .8))
            _banda_niebla(pc, 134, -10, t, _alfa(p["niebla"], .82))
        if E["paraguas"] and not flash:
            _ondas(pc, t)

        # El guardián
        paleta_g = SILUETA if flash else p
        trazo = math.floor(t * 5) % 4
        aire = math.sin(t * 1.1) * 2.2 if E["dormido"] else math.sin(t * 2.2) * 1.2
        sub = round(aire * 2) / 2
        temblando = math.sin(math.floor(t * 12) * 2.6) * 1.1 if clima == "tormenta" else 0
        gx = GX + temblando
        clave = ("guardian", tipo, clima, momento, flash, trazo, round(e, 3), round(oy), w, h)
        l.capa(clave, x + round(temblando * e), y - round(sub * .5 * e), w, h,
               lambda otro: _cuerpo(Pincel(otro, e, ox - x, oy - y), paleta_g, E, trazo, flash))
        if tipo == "roca":
            _brote(pc, paleta_g, E, t, sub)
        _cara(pc, paleta_g, E, t, sub, gx, flash)
        _brazos(pc, paleta_g, E, t, gx, flash)

        if not flash:
            if E["paraguas"]:
                _goteo(pc, clima, t)
                _lluvia(pc, self.gotas, t, self.inclina, p["lluvia"], 2.1)
            elif clima == "nieve":
                _nieve(pc, t, 26, 120, True)
                _vaho(pc, t)
            elif clima == "niebla":
                _banda_niebla(pc, 192, 12, t, _alfa(p["niebla"], .62))
            elif clima == "sol" and momento == "dia":
                _mariposa(pc, t)
            elif clima == "sol" and momento == "noche":
                _luciernagas(pc, t)
                _zetas(pc, t, fuente)
            elif clima == "sol" and momento == "tarde":
                _luciernagas(pc, t + 4)
        if clima == "tormenta" and ciclo < 1.5:
            q = 1 if math.floor(ciclo * 8) % 2 else 1.04
            _estallido(pc, 182, 100, 42 * q, 27 * q, fuente)
        for cx, cy, cw, ch in cartelas:
            l.rect(cx + 3, cy + 3, cw, ch, 0, tinta)
            l.rect(cx, cy, cw, ch, 0, papel)
            l.contorno([(cx, cy), (cx + cw, cy), (cx + cw, cy + ch), (cx, cy + ch)], 2.5, tinta)
        l.sin_recorte()
