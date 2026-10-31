"""Los relojes propios de cada tipo de arte, dibujados con el lienzo común (ver esferas.py).

Todos reciben (l, pal, w, h, hora, ahora, o, fecha): hora es el texto "12:34" ya formateado y o las
opciones del reloj. Los elige artes.py según el arte activo.
"""

import getpass
import math

from esferas import _alto_fecha, _pie
from idioma import _

DIGITOS = {"0": "111101101101111", "1": "010110010010111", "2": "111001111100111", "3": "111001111001111",
           "4": "101101111001001", "5": "111100111001111", "6": "111100111101111", "7": "111001001001001",
           "8": "111101111101111", "9": "111101111001111"}


def _alfa(color, alfa):
    return (*color[:3], alfa)


def _rgb(hexa):
    return tuple(int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5))


def _segundos(ahora, o):
    return ahora.second if o["segundos"] else 0


# --- cifras de bloques ---------------------------------------------------------

def _ancho_digitos(texto, b):
    return sum(2 * b if c == ":" else 4 * b for c in texto) - b


def _cifras_validas(texto):
    return "".join(c for c in texto if c in DIGITOS or c == ":")


def _bloques(l, texto, x, y, b, color, apagado=None):
    """El texto (cifras y dos puntos) en una rejilla de 3 x 5 bloques de lado b."""
    for c in texto:
        if c == ":":
            l.rect(x + b * 0.5, y + b, b, b, 0, color)
            l.rect(x + b * 0.5, y + 3 * b, b, b, 0, color)
            x += 2 * b
            continue
        for i, v in enumerate(DIGITOS[c]):
            if v == "1" or apagado:
                l.rect(x + (i % 3) * b, y + (i // 3) * b, b, b, 0, color if v == "1" else apagado)
        x += 4 * b


def _lado(texto, ancho, alto):
    """El mayor lado de bloque con el que el texto cabe en ancho x alto."""
    unidades = _ancho_digitos(texto, 1)
    return max(1, int(min(ancho / unidades, alto / 5)))


# --- Pixel art -----------------------------------------------------------------

def p_cifras(l, pal, w, h, hora, ahora, o, fecha):
    texto = _cifras_validas(hora)
    alto = _alto_fecha(o, h, 110, min(26, h * 0.16))
    barra = 14 if o["segundos"] else 0
    b = _lado(texto, w * 0.92, (h - alto - barra) * 0.72)
    x, y = (w - _ancho_digitos(texto, b)) / 2, (h - alto - barra - 5 * b) / 2
    _bloques(l, texto, x + max(2, b // 4), y + max(2, b // 4), b, _alfa(pal["tenue"], 0.2))
    _bloques(l, texto, x, y, b, pal["azul"])
    if o["segundos"]:
        paso = (w - 16) / 60
        for i in range(60):
            l.rect(round(8 + i * paso), h - alto - 12, max(1, round(paso) - 1), 6, 0,
                   pal["verde"] if i <= ahora.second else _alfa(pal["tenue"], 0.15))
    _pie(l, pal, w, h, alto, fecha, ahora, o)


def p_dia(l, pal, w, h, hora, ahora, o, fecha):
    horas = ahora.hour + ahora.minute / 60
    dia = 7 <= horas < 20
    b = max(3, round(min(w, h) / 45))
    l.rect(0, 0, w, h, 0, _rgb("#73eff7" if dia else "#29366f"))
    if not dia:
        for i in range(26):
            l.rect((i * 83 % w) // b * b, (i * 47 % max(1, round(h * 0.6))) // b * b, b, b, 0, (0.96, 0.96, 0.96))
    f = (horas - 7) / 13 if dia else ((horas + 4) % 24) / 11
    sx, sy = w * f, h * 0.62 - math.sin(f * math.pi) * h * 0.5
    astro = _rgb("#ffcd75") if dia else (0.96, 0.96, 0.96)
    s = 2 * b
    l.rect(round((sx - 2 * s) / b) * b, round((sy - s) / b) * b, 4 * s, 2 * s, 0, astro)
    l.rect(round((sx - s) / b) * b, round((sy - 2 * s) / b) * b, 2 * s, 4 * s, 0, astro)
    for base, color, curva, altura in ((0.68, "#38b764", 30, 2), (0.82, "#257179", 19, 1)):
        for x in range(0, w + 2 * b, 2 * b):
            y = round((h * base + round(math.sin(x / curva * 2.8 / b * 3 + base * 6) * altura) * 2 * b) / b) * b
            l.rect(x, y, 2 * b, h - y, 0, _rgb(color))
    texto = _cifras_validas(hora)
    lado = _lado(texto, w * 0.5, h * 0.2)
    x, y = (w - _ancho_digitos(texto, lado)) / 2, h - 5 * lado - 2 * b
    _bloques(l, texto, x + lado // 2 + 1, y + lado // 2 + 1, lado, _rgb("#1a1c2c"))
    _bloques(l, texto, x, y, lado, (0.96, 0.96, 0.96))


def p_consola(l, pal, w, h, hora, ahora, o, fecha):
    oscuro, medio, claro, pantalla = (_rgb(c) for c in ("#0f380f", "#306230", "#8bac0f", "#9bbc0f"))
    l.rect(0, 0, w, h, 0, pantalla)
    texto = _cifras_validas(hora)
    b = _lado(texto, w * 0.84, h * 0.46)
    x, y = (w - _ancho_digitos(texto, b)) / 2, h * 0.5 - 3 * b
    _bloques(l, texto, x + 3, y + 3, b, claro)
    _bloques(l, texto, x, y, b, oscuro)
    if o["segundos"]:
        l.texto(f":{ahora.second:02d}", 0, h - 34, w, 24, max(10, h * 0.09), medio, "normal", familia="Press Start 2P")
    for x in range(0, w, 4):
        l.rect(x, 0, 1, h, 0, _alfa(oscuro, 0.09))
    for y in range(0, h, 4):
        l.rect(0, y, w, 1, 0, _alfa(oscuro, 0.09))


# --- Terminal ------------------------------------------------------------------

def _usuario():
    try:
        return getpass.getuser()
    except Exception:  # noqa: BLE001 - sin usuario en el entorno
        return "moondeck"


def t_ascii(l, pal, w, h, hora, ahora, o, fecha):
    plex = "IBM Plex Mono"
    px = max(10, h * 0.08)
    l.texto("$ moondeck --hora", 10, 6, w - 20, px * 1.5, px, pal["gris"], "normal", 0, familia=plex)
    texto = _cifras_validas(hora)
    b = _lado(texto, w - 24, h * 0.5)
    ancho = _ancho_digitos(texto, b)
    y = (h - 5 * b) / 2
    _bloques(l, texto, (w - ancho) / 2, y, b, pal["texto"], _alfa(pal["azul"], 0.1))
    if o["segundos"]:
        marcas = ahora.second // 4
        l.rect(10, h - px - 8, marcas * 6, px * 0.8, 0, pal["gris"])
        for x in range(1, marcas):
            l.rect(10 + x * 6 - 2, h - px - 8, 2, px * 0.8, 0, (0, 0, 0))


def t_comandos(l, pal, w, h, hora, ahora, o, fecha):
    plex = "IBM Plex Mono"
    linea = h / 6
    px = min(max(10, linea * 0.62), w / 32)
    aviso = f"{_usuario()}@moondeck:~$"
    l.texto(aviso + " date", 10, 6, w - 20, linea, px, pal["gris"], "normal", 0, familia=plex)
    grande = min(h * 0.36, w / 4.2)
    l.texto(hora, 10, linea + 6, w - 20, h * 0.42, grande, pal["texto"], "negrita", 0, familia=plex)
    resto = fecha + (f"  :{ahora.second:02d}" if o["segundos"] else "")
    l.texto(resto, 10, h - 2 * linea - 4, w - 20, linea, px, pal["gris"], "normal", 0, familia=plex)
    l.texto(aviso, 10, h - linea - 4, w - 20, linea, px, pal["gris"], "normal", 0, familia=plex)
    if ahora.second % 2:
        ancho, _alto = l.medir(aviso + " ", px, "normal", plex)
        l.rect(10 + ancho, h - linea, px * 0.6, px * 1.1, 0, pal["texto"])


def t_radar(l, pal, w, h, hora, ahora, o, fecha):
    cx, cy, r = w * 0.36, h / 2, min(h * 0.44, w * 0.32)
    for k in (0.33, 0.66, 1):
        l.arco(cx, cy, r * k, 0, 2 * math.pi, 1, _alfa(pal["azul"], 0.35))
    segundo = _segundos(ahora, o)

    def punto(angulo, q):
        return cx + math.cos(angulo) * r * q, cy + math.sin(angulo) * r * q
    for i in range(36):
        a = (segundo - i * 0.4) * math.pi / 30 - math.pi / 2
        l.linea(cx, cy, *punto(a, 1), 2, _alfa(pal["azul"], 0.3 * (1 - i / 36)))
    l.linea(cx, cy, *punto(segundo * math.pi / 30 - math.pi / 2, 1), 2, pal["azul"])
    l.circulo(*punto((ahora.hour % 12) * math.pi / 6 - math.pi / 2, 0.45), 5, pal["texto"])
    l.circulo(*punto(ahora.minute * math.pi / 30 - math.pi / 2, 0.85), 5, pal["texto"])
    l.texto(hora, w * 0.66, 0, w * 0.34, h, min(w * 0.11, h * 0.26), pal["texto"], "negrita", familia="VT323")


# --- Cómic ---------------------------------------------------------------------

BANGERS = "Bangers"


def _papel(pal):
    return _rgb("#fff4d6") if sum(pal["texto"][:3]) < 1.5 else _rgb("#16161a")


def _trama(l, w, h, color):
    paso = 14
    for f in range(h // paso + 2):
        for c in range(w // paso + 2):
            r = 4.6 * (1 - (c + f) * paso / (w + h))
            if r > 0.5:
                l.circulo(c * paso + (f % 2) * paso / 2, f * paso, r, color)


def _elipse(cx, cy, rx, ry):
    return [(cx + math.cos(i * math.pi / 24) * rx, cy + math.sin(i * math.pi / 24) * ry) for i in range(48)]


def _estrella(cx, cy, rx, ry, picos=11, dentro=0.68):
    return [(cx + math.cos(i * math.pi / picos - 0.2) * rx * (dentro if i % 2 else 1),
             cy + math.sin(i * math.pi / picos - 0.2) * ry * (dentro if i % 2 else 1)) for i in range(2 * picos)]


def _rotulo(l, texto, x, y, w, h, px, color, borde):
    """Texto con el contorno de tinta de las onomatopeyas."""
    for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, -2), (-2, 2), (2, 2)):
        l.texto(texto, x + dx, y + dy, w, h, px, borde, "normal", familia=BANGERS)
    l.texto(texto, x, y, w, h, px, color, "normal", familia=BANGERS)


def c_bocadillo(l, pal, w, h, hora, ahora, o, fecha):
    tinta, papel = pal["texto"], _papel(pal)
    l.rect(0, 0, w, h, 0, _rgb("#3b6fb5"))
    _trama(l, w, h, (1, 1, 1, 0.28))
    cx, cy, rx, ry = w / 2, h * 0.44, w * 0.42, h * 0.36
    cola = [(w * 0.28, h * 0.68), (w * 0.17, h * 0.96), (w * 0.46, h * 0.76)]
    l.poligono(_elipse(cx, cy, rx + 3, ry + 3), tinta)
    l.poligono([(cola[0][0] - 5, cola[0][1]), (cola[1][0] - 4, cola[1][1] + 6), (cola[2][0] + 5, cola[2][1] + 2)], tinta)
    l.poligono(cola, papel)
    l.poligono(_elipse(cx, cy, rx, ry), papel)
    l.texto(_("¡SON LAS"), 0, h * 0.14, w, h * 0.2, min(h * 0.13, w * 0.09), tinta, "normal", familia=BANGERS)
    l.texto(hora, 0, h * 0.28, w, h * 0.38, min(h * 0.36, w * 0.24), pal["azul"], "normal", familia=BANGERS)


def c_explosion(l, pal, w, h, hora, ahora, o, fecha):
    tinta = pal["texto"] if sum(pal["texto"][:3]) < 1.5 else (0.1, 0.1, 0.12)
    l.rect(0, 0, w, h, 0, pal["amarillo"])
    _trama(l, w, h, _alfa(pal["rojo"], 0.45))
    cx, cy, rx, ry = w / 2, h / 2, min(w * 0.48, h * 0.72), h * 0.47
    l.poligono(_estrella(cx + 5, cy + 6, rx, ry), tinta)
    l.poligono(_estrella(cx, cy, rx + 2, ry + 2), tinta)
    l.poligono(_estrella(cx, cy, rx - 3, ry - 3), pal["azul"])
    _rotulo(l, hora, 0, 0, w, h, min(h * 0.34, w * 0.24), (1, 1, 1), tinta)
    if o["segundos"]:
        marca = _("¡TAC!") if ahora.second % 2 else _("¡TIC!")
        l.texto(marca, 0, 6, w - 10, h * 0.2, min(h * 0.14, w * 0.09), tinta, "normal", 1, familia=BANGERS)


def c_vinetas(l, pal, w, h, hora, ahora, o, fecha):
    tinta = pal["texto"] if sum(pal["texto"][:3]) < 1.5 else (0.1, 0.1, 0.12)
    horas, minutos = (hora.split(":") + ["00"])[:2]
    partes = [(horas, pal["amarillo"]), (minutos[:2], _rgb("#9ed3f2"))]
    if o["segundos"]:
        partes.append((f"{ahora.second:02d}", _rgb("#f6b2a8")))
    n = len(partes)
    ancho = (w - 12 - 4 * (n - 1)) / n
    for i, (texto, color) in enumerate(partes):
        x0 = 6 + i * (ancho + 4)
        izq = 6 if i else 0
        der = 6 if i < n - 1 else 0
        cerca = [(x0 + izq, 6), (x0 + ancho + der, 6), (x0 + ancho - der, h - 6), (x0 - izq, h - 6)]
        l.poligono(cerca, tinta)
        l.poligono([(x0 + izq + 3, 9), (x0 + ancho + der - 3, 9), (x0 + ancho - der - 3, h - 9), (x0 - izq + 3, h - 9)], color)
        l.texto(texto, x0, 0, ancho, h, min(h * 0.4, ancho * 0.62), (0.1, 0.1, 0.12), "normal", familia=BANGERS)


DIBUJOS = {"p_cifras": p_cifras, "p_dia": p_dia, "p_consola": p_consola, "t_ascii": t_ascii, "t_comandos": t_comandos,
           "t_radar": t_radar, "c_bocadillo": c_bocadillo, "c_explosion": c_explosion, "c_vinetas": c_vinetas}
ALTOS = {clave: 180 for clave in DIBUJOS}
