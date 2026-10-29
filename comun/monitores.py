"""Estilos de monitor para CPU, GPU y Memoria, dibujados una sola vez (como esferas.py).

Cada estilo recibe `medidas`: lista de dicts con
    frac     0-1, ya animada (la vista la mueve poco a poco hacia la lectura)
    color    nombre de la paleta ("azul", "naranja"...)
    nombre   "Uso", "Temp", "VRAM"...
    texto    la cifra ya formateada ("37 %", "54 °C")
La primera es la principal (la cifra grande); las demás acompañan.

`alinear` (0 izquierda, 0.5 centro, 1 derecha) coloca el dibujo en el ancho que sobre;
`cifra` = False lo dibuja sin la cifra principal. `x` trae lo demás que algunos usan:
    t        segundos (para lo que se mueve solo: burbujas, ondas...)
    fase     vueltas acumuladas, más rápido cuanto más carga (engranajes, órbitas...)
    burbujas lo que han subido las burbujas (acumulado, como `fase`)
    agitacion  0-1, cuánto se mueve ahora la medida principal (el líquido chapotea)
    fases    vueltas acumuladas de cada celda, cada una a la velocidad de su carga
    latidos  latidos acumulados (electrocardiograma), más seguidos cuanto más carga
    desde, intervalo  segundos desde la última lectura y entre lecturas (para deslizar entre ellas)
    edades   lo que hace que llegó cada lectura del historial, en lecturas (1.5 = hace un intervalo y medio)
    estado   un dict de la vista que el estilo puede usar para recordar cosas entre fotogramas
Cada medida trae también "valor" (el número sin formatear, animado).
    celdas   fracs de cada núcleo (CPU) o de cada medida (GPU, Memoria) en la última lectura
    nombres  el rótulo de cada celda ("0", "1"... o "Uso", "VRAM"...)
    historial  las `celdas` de las últimas lecturas, la más nueva al final
    serie    las fracs de las `medidas` de las últimas lecturas, la más nueva al final
Los estilos de ANIMADOS se redibujan continuamente mientras se ven.
"""

import math

from esferas import con_alfa, mezcla, px_que_quepa

# (clave, nombre en el menú). "clasico" = cifra grande + gráfica, como siempre.
ESTILOS = (("clasico", "Clásico"), ("aguja", "Aguja"), ("anillos", "Anillos"), ("arcos", "Arcos"),
           ("steampunk", "Steampunk"), ("segmentos", "Pantalla de 7 segmentos"), ("deposito", "Depósito de líquido"),
           ("calor", "Mapa de calor por núcleo"), ("barras", "Barras por núcleo"), ("cascada", "Cascada"),
           ("espectrograma", "Espectrograma"), ("arana", "Radar (araña)"), ("osciloscopio", "Osciloscopio"),
           ("liquido", "Líquido en el widget"), ("sparkline", "Sparkline"), ("barrido", "Radar con barrido"),
           ("hexagonos", "Rejilla hexagonal"), ("hud", "Retícula HUD"), ("orbital", "Núcleo orbital"),
           ("iso", "Barras 3D isométricas"), ("paisaje", "Paisaje del historial"), ("chip", "Chip en isométrico"),
           ("cubo", "Cubo 3D"), ("llamas", "Llamas"), ("lava", "Lámpara de lava"),
           ("electro", "Electrocardiograma"), ("aurora", "Aurora"), ("ondas", "Ondas"),
           ("hiperespacio", "Salto al hiperespacio"), ("donut", "Donut ASCII"), ("vumetro", "Vúmetro de estudio"),
           ("tunel", "Túnel infinito"), ("galaxia", "Galaxia espiral"), ("esfera", "Esfera de partículas"),
           ("planeta", "Planeta con anillos"), ("agujero", "Agujero negro"), ("paletas", "Tablero de aeropuerto"),
           ("terminal", "Terminal de fósforo ámbar"), ("leds", "Matriz de LEDs"), ("f1", "Luces de cambio (F1)"),
           ("arena", "Reloj de arena"), ("tormenta", "Tormenta"), ("plasma", "Bola de plasma"),
           ("vida", "Juego de la vida"), ("arbol", "Árbol fractal"), ("newton", "Péndulo de Newton"),
           ("lissajous", "Lissajous"), ("reactor", "Reactor de arco"), ("codigo", "Lluvia de código"),
           ("globo", "Globo con viento"))
CLAVES = {c for c, _n in ESTILOS}
ANIMADOS = {"steampunk", "deposito", "liquido", "barrido", "hud", "orbital", "cubo", "llamas", "lava", "electro",
            "aurora", "ondas", "paisaje", "hiperespacio", "donut", "vumetro", "tunel", "galaxia", "esfera",
            "planeta", "agujero", "paletas", "terminal", "f1", "arena", "tormenta", "plasma", "vida", "arbol",
            "newton", "lissajous", "reactor", "codigo", "globo"}
# Los que cuestan más de dibujar se redibujan menos veces por segundo (el resto, a 60).
FPS = {"paisaje": 30, "donut": 30, "codigo": 30, "vida": 30, "globo": 30}
# El widget entero es el recipiente: la tarjeta pinta el líquido de fondo (ver fondo_liquido).
DE_FONDO = {"liquido"}

def estilos_para(tipo, actual=None):
    """Los estilos que se ofrecen para ese monitor: todos (aunque alguno pinte poco en alguno)."""
    return list(ESTILOS)


def dibujar(l, pal, w, h, medidas, estilo, alinear=0.5, cifra=True, x=None):
    if not medidas or w < 20 or h < 20:
        return
    if not cifra:
        medidas = [dict(medidas[0], texto="")] + medidas[1:]
    ancho = min(w, _ancho(estilo, w, h, medidas, len((x or {}).get("celdas") or ())))
    x0 = (w - ancho) * alinear
    fn = globals().get(f"_{estilo}", _anillos)
    fn(Desplazado(l, x0) if x0 else l, pal, ancho, h, medidas, x or {"t": 0.0, "fase": 0.0})


def _ancho(estilo, w, h, medidas, n_celdas=0):
    """Lo que ocupa el dibujo a lo ancho con ese alto (lo que sobre es para alinearlo)."""
    leyenda = 16 if len(medidas) > 1 else 0
    if estilo == "aguja":
        return 2 * ((h - leyenda - 10) / 1.37) * 1.07 + 12
    if estilo == "arcos":
        return 2 * ((h - (16 if len(medidas) > 2 else 0)) / 1.5) + 8
    if estilo == "steampunk":
        return h * (1.0 + 0.32 * min(2, len(medidas) - 1)) + 6
    if estilo == "segmentos":
        return max(h * 1.9, 150)
    if estilo == "deposito":
        return (h - 4) + (len(medidas) - 1) * max(30.0, h * 0.3)
    if estilo in ("arana", "barrido", "hud"):
        return h + 40
    if estilo == "orbital":
        return h * 1.9
    if estilo == "cubo":
        return h + 130
    if estilo == "lava":
        return h * 0.5 + 130
    if estilo == "ondas":
        return h * 1.6
    if estilo in ("planeta", "agujero", "reactor", "plasma", "globo"):
        return h * 1.5
    if estilo == "arena":
        return h * 0.55 + 130
    if estilo == "newton":
        return h * 1.5
    if estilo == "vumetro":
        return min(2, len(medidas)) * h * 1.35 + 8
    if estilo == "barras":
        return max(150.0, n_celdas * 26.0 + 16)
    if estilo == "anillos":
        # Con sitio, la leyenda va al lado; si no, debajo y ocupa todo el ancho.
        if len(medidas) == 1:
            return h
        return h + 150 if w > h * 1.6 else w
    return w  # los demás llenan todo el ancho (paneles, fondos, rejillas...)


class Desplazado:
    """El mismo lienzo, corrido `dx` a la derecha (para alinear el dibujo)."""

    def __init__(self, l, dx):
        self.l, self.dx = l, dx

    def rect(self, x, y, w, h, radio, color):
        self.l.rect(x + self.dx, y, w, h, radio, color)

    def circulo(self, cx, cy, r, color):
        self.l.circulo(cx + self.dx, cy, r, color)

    def arco(self, cx, cy, r, a0, a1, grosor, color, redondo=False):
        self.l.arco(cx + self.dx, cy, r, a0, a1, grosor, color, redondo)

    def linea(self, x0, y0, x1, y1, grosor, color, redondo=False):
        self.l.linea(x0 + self.dx, y0, x1 + self.dx, y1, grosor, color, redondo)

    def poligono(self, puntos, color):
        self.l.poligono([(x + self.dx, y) for x, y in puntos], color)

    def medir(self, texto, px, peso="normal"):
        return self.l.medir(texto, px, peso)

    def texto(self, texto, x, y, w, h, px, color, peso="normal", h_al=0.5, v_al=0.5):
        self.l.texto(texto, x + self.dx, y, w, h, px, color, peso, h_al, v_al)


def _color(pal, m):
    return pal.get(m["color"], pal["azul"])


def _leyenda(l, pal, x, y, w, h, medidas, alinear=0.5):
    """Las medidas secundarias en una línea: punto de color, nombre y cifra."""
    if not medidas or h < 9:
        return
    px = max(8.0, min(12.0, h * 0.8))
    partes = []
    total = 0
    for m in medidas:
        txt = f"{m['nombre']} {m['texto']}"
        tw, _th = l.medir(txt, px, "normal")
        partes.append((m, txt, tw))
        total += tw + px * 1.3  # punto + hueco
    total -= px * 0.4
    if total > w:  # no cabe: más pequeño
        px *= w / total
        total = w
    cx = x + (w - total) * alinear
    for m, txt, _tw in partes:
        tw, _th = l.medir(txt, px, "normal")
        l.circulo(cx + px * 0.3, y + h / 2, px * 0.28, _color(pal, m))
        l.texto(txt, cx + px * 0.75, y, tw + 2, h, px, pal["gris"], "normal", 0.0, 0.5)
        cx += tw + px * 1.3


def _cifra(l, pal, x, y, w, h, texto, color=None, peso="fino"):
    if not texto:
        return
    px = px_que_quepa(l, texto, w, h, peso)
    l.texto(texto, x, y, w, h, px, color or pal["texto"], peso)


# --- aguja ------------------------------------------------------------------------


def _aguja(l, pal, w, h, medidas, x=None):
    """Medio reloj de coche: rayas, zona roja y aguja; la cifra debajo del eje.
    La segunda medida va como un arco fino por fuera."""
    principal, resto = medidas[0], medidas[1:]
    alto_ley = 16 if resto else 0
    hh = h - alto_ley
    # Semicírculo que quepa: ancho 2r y alto r + la cifra de debajo (0.3 r), más lo que asoma
    # por fuera del radio: el grosor del arco y el arco fino de la segunda medida (~0.07 r + 4).
    r = min((w / 2 - 6) / 1.07, (hh - 10) / 1.37)
    if r < 18:
        return
    cx, cy = w / 2, 2 + r * 1.07 + 4
    a0, a1 = math.pi, 2 * math.pi
    color = _color(pal, principal)
    grueso = max(2.0, r * 0.035)
    l.arco(cx, cy, r, a0, a1, grueso, con_alfa(pal["tenue"], 0.25))
    l.arco(cx, cy, r - r * 0.07, a0 + math.pi * 0.85, a1, max(2.0, r * 0.05), con_alfa(pal["rojo"], 0.7))
    if principal["frac"] > 0:
        l.arco(cx, cy, r, a0, a0 + math.pi * principal["frac"], max(3.0, r * 0.06), color)
    if resto:  # segunda medida: arco exterior fino
        m = resto[0]
        r2 = r + max(3.0, r * 0.06)
        if r2 < w / 2 - 1:
            l.arco(cx, cy, r2, a0, a1, 2, con_alfa(pal["tenue"], 0.12))
            if m["frac"] > 0:
                l.arco(cx, cy, r2, a0, a0 + math.pi * m["frac"], 2, _color(pal, m))
    for i in range(21):
        a = a0 + math.pi * i / 20
        largo, grosor, alfa = (0.14, 0.03, 0.85) if i % 5 == 0 else (0.07, 0.015, 0.45)
        r_in = r * (0.9 - largo)
        l.linea(cx + math.cos(a) * r_in, cy + math.sin(a) * r_in,
                cx + math.cos(a) * r * 0.9, cy + math.sin(a) * r * 0.9,
                max(1.0, r * grosor), con_alfa(pal["tenue"], alfa))
    a = a0 + math.pi * max(0.0, min(1.0, principal["frac"]))
    largo = r * 0.86
    l.linea(cx - math.cos(a) * r * 0.1, cy - math.sin(a) * r * 0.1,
            cx + math.cos(a) * largo, cy + math.sin(a) * largo, max(2.0, r * 0.035), color, True)
    l.circulo(cx, cy, max(4.0, r * 0.08), color)
    l.circulo(cx, cy, max(2.0, r * 0.04), pal["texto"])
    # La cifra, debajo del eje.
    alto = min(r * 0.3, hh - cy - 4)
    if alto > 8:
        _cifra(l, pal, cx - r, cy + 4, 2 * r, alto, principal["texto"])
    if resto:
        _leyenda(l, pal, 0, h - alto_ley, w, alto_ley, resto)


# --- anillos ------------------------------------------------------------------------


def _anillos(l, pal, w, h, medidas, x=None):
    """Anillos concéntricos (como los de actividad de un reloj): uno por medida,
    la principal por fuera; la cifra en el centro y la leyenda al lado o debajo."""
    n = len(medidas[:3])
    al_lado = w > h * 1.6 and n > 1
    if al_lado:
        lado = min(h, w * 0.55)
        cx, cy = lado / 2 + 2, h / 2
    else:
        lado = min(w, h - (16 if n > 1 else 0))
        cx, cy = w / 2, lado / 2
    r = lado / 2 - 3
    if r < 16:
        return
    grueso = max(5.0, r * (0.17 if n > 1 else 0.2))
    hueco = grueso * 0.35
    inicio = -math.pi / 2
    for i, m in enumerate(medidas[:3]):
        rr = r - grueso / 2 - i * (grueso + hueco)
        if rr < grueso:
            break
        color = _color(pal, m)
        l.arco(cx, cy, rr, 0, 2 * math.pi, grueso, con_alfa(color, 0.13))
        f = max(0.0, min(1.0, m["frac"]))
        if f > 0.003:
            # Degradado a trozos: de más oscuro a su color, con la punta redonda.
            trozos = max(2, int(40 * f))
            oscuro = mezcla(color, (0, 0, 0), 0.35)
            for k in range(trozos):
                f0, f1 = f * k / trozos, f * (k + 1) / trozos
                c = mezcla(oscuro, color, (k + 1) / trozos)
                l.arco(cx, cy, rr, inicio + 2 * math.pi * f0, inicio + 2 * math.pi * f1 + 0.01, grueso, c,
                       k in (0, trozos - 1))
    r_dentro = r - n * (grueso + hueco) + hueco
    if r_dentro > 10:
        lado_txt = r_dentro * 1.35
        _cifra(l, pal, cx - lado_txt / 2, cy - lado_txt * 0.3, lado_txt, lado_txt * 0.6, medidas[0]["texto"])
    if n > 1 or al_lado:
        if al_lado:
            x = cx + r + 12
            filas = medidas[:3]
            alto_fila = min(22.0, h / max(1, len(filas)))
            y = cy - alto_fila * len(filas) / 2
            for m in filas:
                px = max(8.0, min(13.0, alto_fila * 0.6))
                l.circulo(x + px * 0.3, y + alto_fila / 2, px * 0.3, _color(pal, m))
                txt = f"{m['nombre']}  {m['texto']}"
                l.texto(txt, x + px, y, w - x - px, alto_fila, px, pal["gris"], "normal", 0.0, 0.5)
                y += alto_fila
        else:
            _leyenda(l, pal, 0, h - 16, w, 16, medidas[:3])


# --- arcos ------------------------------------------------------------------------

ARCO = math.radians(240)
INICIO = math.radians(150)


def _arcos(l, pal, w, h, medidas, x=None):
    """Arco de segmentos que se encienden (del color al rojo según suben), y por dentro
    otro más fino con la segunda medida. La cifra en el centro."""
    principal, resto = medidas[0], medidas[1:]
    alto_ley = 16 if len(resto) > 1 else 0
    hh = h - alto_ley
    r = min(w / 2 - 4, hh / (1 + math.sin(math.radians(30))) - 4)
    if r < 18:
        return
    cx, cy = w / 2, 4 + r
    grueso = max(6.0, r * 0.15)
    rm = r - grueso / 2
    n = 30 if r > 50 else 20
    paso = ARCO / n
    f = max(0.0, min(1.0, principal["frac"]))
    color = _color(pal, principal)
    for i in range(n):
        a = INICIO + paso * i
        pos = (i + 0.5) / n
        if pos <= f:
            # Los últimos segmentos se calientan: del color al naranja y al rojo.
            c = color if pos < 0.6 else mezcla(color, pal["naranja"], (pos - 0.6) / 0.25) if pos < 0.85 \
                else mezcla(pal["naranja"], pal["rojo"], (pos - 0.85) / 0.15)
        else:
            c = con_alfa(pal["tenue"], 0.08)
        l.arco(cx, cy, rm, a + paso * 0.12, a + paso * 0.88, grueso, c)
    r_in = rm - grueso / 2 - max(4.0, r * 0.06)
    if resto and r_in > 14:
        m = resto[0]
        g2 = max(3.0, r * 0.05)
        l.arco(cx, cy, r_in, INICIO, INICIO + ARCO, g2, con_alfa(pal["tenue"], 0.1), True)
        if m["frac"] > 0.003:
            l.arco(cx, cy, r_in, INICIO, INICIO + ARCO * max(0.0, min(1.0, m["frac"])), g2, _color(pal, m), True)
    hueco = r_in * 1.2
    _cifra(l, pal, cx - hueco / 2, cy - r * 0.25, hueco, r * 0.38, principal["texto"])
    if resto and r > 40:
        m = resto[0]
        px = max(8.0, min(12.0, r * 0.12))
        l.texto(f"{m['nombre']} {m['texto']}", cx - r, cy + r * 0.16, 2 * r, px * 1.4, px, _color(pal, m), "normal")
    if alto_ley:
        _leyenda(l, pal, 0, h - alto_ley, w, alto_ley, resto[1:])


# --- steampunk ----------------------------------------------------------------------

LATON = (0.78, 0.6, 0.3)
LATON_OSCURO = (0.38, 0.25, 0.1)
LATON_CLARO = (0.97, 0.85, 0.55)
CREMA = (0.94, 0.89, 0.76)
TINTA = (0.16, 0.11, 0.07)


def _engranaje(l, cx, cy, r, dientes, giro, color, hueco):
    """Rueda dentada: dientes trapezoidales, y un agujero del color de lo de detrás."""
    puntos = []
    r_in = r * 0.8
    for i in range(dientes):
        a = giro + 2 * math.pi * i / dientes
        paso = 2 * math.pi / dientes
        for da, rr in ((-0.3, r_in), (-0.17, r), (0.17, r), (0.3, r_in)):
            puntos.append((cx + math.cos(a + da * paso) * rr, cy + math.sin(a + da * paso) * rr))
    l.poligono(puntos, color)
    l.circulo(cx, cy, r_in * 0.82, mezcla(color, LATON_OSCURO, 0.25))
    for i in range(4):  # radios
        a = giro + math.pi / 2 * i + math.pi / 4
        l.circulo(cx + math.cos(a) * r_in * 0.48, cy + math.sin(a) * r_in * 0.48, r_in * 0.18, hueco)
    l.circulo(cx, cy, r_in * 0.2, LATON_OSCURO)


def _steampunk(l, pal, w, h, medidas, x=None):
    """Manómetro de latón con remaches, esfera crema y aguja negra; engranajes que giran
    más deprisa cuanto más carga hay, y tubos de cristal con las demás medidas."""
    principal, resto = medidas[0], medidas[1:3]
    r = (h - 6) / 2
    if r < 20:
        return
    fase = (x or {}).get("fase", 0.0)
    cx, cy = r + 3, h / 2
    # Engranajes detrás del manómetro (asoman por abajo y por arriba).
    hueco = (0.14, 0.09, 0.04)
    _engranaje(l, cx + r * 0.78, cy + r * 0.62, r * 0.42, 12, fase * 2 * math.pi, LATON_OSCURO, hueco)
    _engranaje(l, cx - r * 0.72, cy - r * 0.66, r * 0.3, 9, -fase * 2 * math.pi * 12 / 9 + 0.2,
               mezcla(LATON_OSCURO, LATON, 0.4), hueco)
    # Bisel de latón (anillos que simulan el brillo) y esfera.
    l.circulo(cx, cy, r, LATON_OSCURO)
    l.circulo(cx, cy, r * 0.97, LATON)
    l.arco(cx, cy, r * 0.9, math.radians(200), math.radians(290), r * 0.06, con_alfa(LATON_CLARO, 0.8), True)
    l.circulo(cx, cy, r * 0.86, LATON_OSCURO)
    l.circulo(cx, cy, r * 0.84, CREMA)
    for i in range(8):  # remaches
        a = 2 * math.pi * i / 8 + math.pi / 8
        rx, ry = cx + math.cos(a) * r * 0.925, cy + math.sin(a) * r * 0.925
        l.circulo(rx, ry, max(1.5, r * 0.035), LATON_OSCURO)
        l.circulo(rx - r * 0.008, ry - r * 0.008, max(1.0, r * 0.02), LATON_CLARO)
    # Escala de 270° con zona roja.
    a0, arco = math.radians(135), math.radians(270)
    re = r * 0.72
    l.arco(cx, cy, re, a0 + arco * 0.8, a0 + arco, max(2.0, r * 0.07), (0.7, 0.12, 0.08))
    for i in range(11):
        a = a0 + arco * i / 10
        largo = 0.14 if i % 5 == 0 else 0.08
        l.linea(cx + math.cos(a) * re * (1 - largo), cy + math.sin(a) * re * (1 - largo),
                cx + math.cos(a) * re * 1.04, cy + math.sin(a) * re * 1.04, max(1.0, r * 0.02), TINTA)
    if r > 40:
        px = max(7.0, r * 0.11)
        for v in (0, 50, 100):
            a = a0 + arco * v / 100
            l.texto(str(v), cx + math.cos(a) * re * 0.68 - 15, cy + math.sin(a) * re * 0.68 - 8, 30, 16, px,
                    TINTA, "normal")
    if principal["texto"]:
        _cifra(l, pal, cx - r * 0.4, cy + r * 0.3, r * 0.8, r * 0.26, principal["texto"], TINTA, "normal")
    if r > 40:
        l.texto(principal["nombre"].upper(), cx - r * 0.4, cy - r * 0.42, r * 0.8, r * 0.16, max(7.0, r * 0.09),
                con_alfa(TINTA, 0.7), "negrita")
    # Aguja de hierro con contrapeso.
    a = a0 + arco * max(0.0, min(1.0, principal["frac"]))
    l.linea(cx - math.cos(a) * r * 0.16, cy - math.sin(a) * r * 0.16,
            cx + math.cos(a) * re * 0.95, cy + math.sin(a) * re * 0.95, max(2.0, r * 0.035), TINTA, True)
    l.circulo(cx - math.cos(a) * r * 0.14, cy - math.sin(a) * r * 0.14, max(2.0, r * 0.05), TINTA)
    l.circulo(cx, cy, max(3.0, r * 0.08), LATON_OSCURO)
    l.circulo(cx, cy, max(1.5, r * 0.04), LATON_CLARO)
    # Tubos de cristal (uno por medida secundaria) con su líquido.
    tx = cx + r + 8
    ancho_t = max(10.0, r * 0.26)
    for m in resto:
        if tx + ancho_t > w:
            break
        alto_t = h - 30
        y0 = 12
        l.rect(tx - 2, y0 - 6, ancho_t + 4, 6, 2, LATON)                   # tapa
        l.rect(tx - 2, y0 + alto_t, ancho_t + 4, 6, 2, LATON)               # base
        l.rect(tx, y0, ancho_t, alto_t, ancho_t / 2, con_alfa(CREMA, 0.12))  # cristal
        f = max(0.0, min(1.0, m["frac"]))
        if f > 0.01:
            nivel = alto_t * f
            l.rect(tx + 2, y0 + alto_t - nivel, ancho_t - 4, nivel, (ancho_t - 4) / 2, _color(pal, m))
        l.linea(tx + ancho_t * 0.3, y0 + 4, tx + ancho_t * 0.3, y0 + alto_t - 4, 1.5, con_alfa((1, 1, 1), 0.25), True)
        px = max(7.0, min(11.0, ancho_t * 0.5))
        l.texto(m["texto"], tx - 10, h - 16, ancho_t + 20, 16, px, LATON_CLARO, "normal")
        tx += ancho_t + max(12.0, r * 0.2)


# --- pantalla de 7 segmentos ---------------------------------------------------------

def _segmentos(l, pal, w, h, medidas, x=None):
    """Display fluorescente (VFD): cifras de 7 segmentos con los apagados en fantasma,
    una barra de LEDs debajo y las demás medidas en pequeño."""
    from esferas import SEGMENTOS, _segmento
    principal, resto = medidas[0], medidas[1:3]
    color = mezcla(_color(pal, principal), (1, 1, 1), 0.25)
    l.rect(0, 0, w, h, 8, (0.02, 0.03, 0.03, 0.55))
    fantasma = con_alfa(color, 0.07)
    # El número (sin la unidad), alineado a la derecha en 3 cifras, como un display.
    texto = principal["texto"]
    numero = "".join(c for c in texto.split(" ")[0] if c.isdigit())[-3:]
    unidad = texto[len(texto.split(" ")[0]):].strip()
    alto_led = max(6.0, h * 0.09)
    alto_resto = 15
    zona_h = h - alto_led - 22 - alto_resto * len(resto)
    ancho_unidad = max(40.0, w * 0.2)
    ch = min(zona_h, (w - 24 - ancho_unidad) / 1.95)  # 3 cifras de 0.5 ch + 2 huecos + el grosor
    cw = ch * 0.5
    grueso = max(2.5, ch * 0.12)
    sep = cw * 0.35
    x0 = 12 + grueso / 2
    y0 = 10 + (zona_h - ch) / 2
    if texto:
        for i in range(3):
            d = numero.rjust(3)[i]
            xx = x0 + i * (cw + sep) + ch * 0.06
            for s in "abcdefg":
                _segmento(l, s, xx, y0, cw, ch, grueso, color if d != " " and s in SEGMENTOS.get(d, "") else fantasma)
        px = max(9.0, ch * 0.3)
        xu = x0 + 3 * cw + 2 * sep + grueso + 6
        l.texto(unidad, xu, y0 + ch - px * 1.3, w - xu - 8, px * 1.3, px, color, "negrita", 0.0, 1.0)
        l.texto(principal["nombre"].upper(), xu, y0, w - xu - 8, px * 1.3, max(8.0, px * 0.7), con_alfa(color, 0.7),
                "negrita", 0.0, 0.0)
    # Barra de LEDs.
    n = 20
    yb = y0 + ch + 10
    ancho_b = w - 24
    paso = ancho_b / n
    f = max(0.0, min(1.0, principal["frac"]))
    for i in range(n):
        pos = (i + 0.5) / n
        c = color if pos < 0.7 else pal["amarillo"] if pos < 0.88 else pal["rojo"]
        l.rect(12 + i * paso, yb, paso * 0.72, alto_led, 1.5, c if pos <= f else con_alfa(c, 0.08))
    # Las demás medidas: su nombre, una barrita de LEDs de su color y la cifra.
    y = yb + alto_led + 6
    for m in resto:
        cm = mezcla(_color(pal, m), (1, 1, 1), 0.25)
        px = 9.0
        ancho_txt = 46
        l.texto(m["nombre"].upper(), 12, y, ancho_txt, alto_resto, px, con_alfa(cm, 0.8), "negrita", 0.0, 0.5)
        l.texto(m["texto"], w - 12 - 70, y, 70, alto_resto, px, cm, "negrita", 1.0, 0.5)
        x_b, ancho_b2 = 12 + ancho_txt, w - 24 - ancho_txt - 76
        fm = max(0.0, min(1.0, m["frac"]))
        if ancho_b2 > 20:
            for i in range(n):
                l.rect(x_b + i * ancho_b2 / n, y + alto_resto * 0.3, ancho_b2 / n * 0.7, alto_resto * 0.4, 1,
                       cm if (i + 0.5) / n <= fm else con_alfa(cm, 0.08))
        y += alto_resto


# --- depósito de líquido --------------------------------------------------------------

def _deposito(l, pal, w, h, medidas, x=None):
    """Matraz redondo que se llena: la superficie ondula (más cuanto más carga) y suben
    burbujas. Las demás medidas en probetas al lado."""
    x = x or {}
    t = x.get("t", 0.0)
    principal, resto = medidas[0], medidas[1:3]
    r = (h - 4) / 2
    if r < 18:
        return
    cx, cy = r + 2, h / 2
    color = _color(pal, principal)
    f = max(0.0, min(1.0, principal["frac"]))
    l.circulo(cx, cy, r, con_alfa(pal["tenue"], 0.07))
    if f > 0.005:
        ri = r - 3
        nivel = cy + ri - 2 * ri * f
        amp = ri * (0.02 + 0.05 * f + 0.08 * x.get("agitacion", 0.0)) if 0.02 < f < 0.98 else 0
        dy = max(-ri + 0.5, min(ri - 0.5, nivel - cy))
        hw = math.sqrt(max(0.0, ri * ri - dy * dy))
        puntos = []
        pasos = 28
        for i in range(pasos + 1):
            px_ = cx - hw + 2 * hw * i / pasos
            ola = math.sin(px_ / ri * 5 + t * 2.4) * amp + math.sin(px_ / ri * 9 - t * 3.1) * amp * 0.4
            borde = i in (0, pasos)
            puntos.append((px_, nivel if borde else nivel + ola))
        a_der = math.atan2(dy, hw)
        a_izq = math.pi - a_der
        for i in range(1, 24):
            a = a_der + (a_izq - a_der) * i / 24
            puntos.append((cx + math.cos(a) * ri, cy + math.sin(a) * ri))
        l.poligono(puntos, con_alfa(mezcla(color, (0, 0, 0), 0.15), 0.85))
        # Brillo de la superficie y burbujas que suben.
        l.linea(cx - hw * 0.7, nivel + 2, cx - hw * 0.2, nivel + 2, 1.5, con_alfa((1, 1, 1), 0.2), True)
        prof = cy + ri - nivel
        for i in range(int(4 + 8 * f)):
            sem = (i * 0.618) % 1
            bx = cx + (sem - 0.5) * hw * 1.4
            avance = (x.get("burbujas", 0.0) * 1.6 * (0.6 + sem) + sem * 3.7) % 1
            by = cy + ri - 4 - avance * (prof - 6)
            if (bx - cx) ** 2 + (by - cy) ** 2 < (ri - 3) ** 2:
                l.circulo(bx, by, 1 + 2.2 * sem * ri / 60, con_alfa((1, 1, 1), 0.28))
    # Cristal: borde y reflejo.
    l.arco(cx, cy, r - 1, 0, 2 * math.pi, 2, con_alfa(pal["texto"], 0.35))
    l.arco(cx, cy, r * 0.8, math.radians(200), math.radians(250), max(2.0, r * 0.06), con_alfa((1, 1, 1), 0.3), True)
    if principal["texto"]:
        _cifra(l, pal, cx - r * 0.6, cy - r * 0.22, r * 1.2, r * 0.44, principal["texto"], pal["texto"], "normal")
    # Probetas.
    ancho_p = max(16.0, r * 0.32)
    px0 = cx + r + 12
    for m in resto:
        if px0 + ancho_p > w:
            break
        alto_p = h - 22
        l.rect(px0, 2, ancho_p, alto_p, ancho_p / 2, con_alfa(pal["tenue"], 0.07))
        fm = max(0.0, min(1.0, m["frac"]))
        if fm > 0.01:
            nivel = (alto_p - 4) * fm
            l.rect(px0 + 2, 2 + alto_p - 2 - nivel, ancho_p - 4, nivel, (ancho_p - 4) / 2,
                   con_alfa(_color(pal, m), 0.85))
        l.rect(px0, 2, 1.5, alto_p, 0, con_alfa(pal["texto"], 0.25))
        l.rect(px0 + ancho_p - 1.5, 2, 1.5, alto_p, 0, con_alfa(pal["texto"], 0.25))
        l.texto(m["texto"], px0 - 12, h - 18, ancho_p + 24, 16, max(8.0, min(11.0, ancho_p * 0.45)), pal["gris"],
                "normal")
        px0 += ancho_p + max(14.0, r * 0.3)


# --- por núcleo: mapa de calor, barras y cascada ------------------------------------------

# De frío a caliente: azul oscuro, cian, verde, amarillo y rojo.
TERMICA = ((0.0, (0.1, 0.16, 0.38)), (0.3, (0.16, 0.62, 0.88)), (0.55, (0.3, 0.84, 0.42)),
           (0.8, (1.0, 0.82, 0.2)), (1.0, (0.95, 0.24, 0.2)))


def calor(f):
    f = max(0.0, min(1.0, f))
    for (f0, c0), (f1, c1) in zip(TERMICA, TERMICA[1:]):
        if f <= f1:
            return mezcla(c0, c1, (f - f0) / (f1 - f0))
    return TERMICA[-1][1]


def _cabecera(l, pal, w, h, medidas):
    """Cifra principal a la izquierda y las demás medidas a la derecha, en una franja.
    Devuelve lo que ocupa (0 si no hay nada que poner)."""
    principal, resto = medidas[0], medidas[1:3]
    if not principal["texto"] and not resto:
        return 0
    alto = max(16.0, min(34.0, h * 0.24))
    ocupado = 0
    if principal["texto"]:
        px = px_que_quepa(l, principal["texto"], w * (0.4 if resto else 1), alto)
        ocupado = l.medir(principal["texto"], px, "fino")[0] + 12
        l.texto(principal["texto"], 0, 0, ocupado, alto, px, pal["texto"], "fino", 0.0, 0.5)
    if resto:
        _leyenda(l, pal, ocupado, 0, w - ocupado, alto, resto, 1.0)
    return alto + 6


def _celdas(x, medidas):
    x = x or {}
    celdas = x.get("celdas") or [m["frac"] for m in medidas]
    nombres = x.get("nombres") or [m["nombre"] for m in medidas]
    return celdas, nombres, x.get("historial") or [celdas]


def _calor(l, pal, w, h, medidas, x=None):
    """Una casilla por núcleo, del azul (parado) al rojo (a tope), en la rejilla que mejor
    llene el sitio. Sin núcleos (GPU, Memoria): las últimas lecturas, como un calendario."""
    celdas, nombres, historial = _celdas(x, medidas)
    y0 = _cabecera(l, pal, w, h, medidas)
    alto = h - y0
    if len(celdas) <= 3:
        # Sin núcleos (GPU, Memoria, Red...): una fila por medida con sus últimas lecturas.
        serie = (x or {}).get("serie") or [[m["frac"] for m in medidas]]
        filas = len(medidas[:3])
        cols = max(8, min(40, int(w / 9)))
        tramo = serie[-cols:]
        lado_w, lado_h = w / cols, alto / filas
        hueco = max(1.0, min(lado_w, lado_h) * 0.12)
        for k in range(filas):
            for j, lectura in enumerate(tramo):
                if k < len(lectura):
                    l.rect((cols - len(tramo) + j) * lado_w + hueco / 2, y0 + k * lado_h + hueco / 2, lado_w - hueco,
                           lado_h - hueco, min(3.0, lado_h * 0.15), calor(lectura[k]))
        return
    n = len(celdas)
    if n == 0 or alto < 10:
        return
    # Columnas que dejan las casillas más cuadradas.
    # (y mejor si llenan filas enteras: 16 núcleos en 8x2 o 4x4, no 6+6+4).
    mejor = min(range(1, n + 1), key=lambda c: abs(math.log((w / c) / (alto / math.ceil(n / c))))
                + (0.6 if n % c else 0))
    cols, filas = mejor, math.ceil(n / mejor)
    lado_w, lado_h = w / cols, alto / filas
    hueco = max(1.5, min(lado_w, lado_h) * 0.1)
    for i, f in enumerate(celdas):
        cx, cy = i % cols, i // cols
        xx, yy = cx * lado_w, y0 + cy * lado_h
        l.rect(xx + hueco / 2, yy + hueco / 2, lado_w - hueco, lado_h - hueco, min(6.0, lado_h * 0.18), calor(f))
        if nombres and min(lado_w, lado_h) > 26:
            px = min(lado_w, lado_h) * 0.26
            l.texto(f"{f * 100:.0f}", xx, yy, lado_w, lado_h, px, (1, 1, 1, 0.85), "negrita")


def _barras(l, pal, w, h, medidas, x=None):
    """Una barra por núcleo (o por medida) que se calienta de color al subir, con una raya
    que marca el máximo de los últimos segundos y baja despacio."""
    celdas, nombres, historial = _celdas(x, medidas)
    y0 = _cabecera(l, pal, w, h, medidas)
    rotulos = len(celdas) <= 4
    alto = h - y0 - (14 if rotulos else 0)
    n = len(celdas)
    if n == 0 or alto < 10:
        return
    paso = w / n
    ancho = max(2.0, paso * 0.68)
    reciente = historial[-12:]
    for i, f in enumerate(celdas):
        f = max(0.0, min(1.0, f))
        xx = i * paso + (paso - ancho) / 2
        l.rect(xx, y0, ancho, alto, min(3.0, ancho / 3), con_alfa(pal["tenue"], 0.07))
        if f > 0.005:
            # Por tramos: cada trozo con el color de su altura (como un vúmetro).
            trozos = max(1, int(f * 12))
            for k in range(trozos):
                f0, f1 = f * k / trozos, f * (k + 1) / trozos
                l.rect(xx, y0 + alto * (1 - f1), ancho, alto * (f1 - f0) + 0.5, 0, calor(f1))
        pico = max((fila[i] for fila in reciente if i < len(fila)), default=f)
        if pico > f + 0.02:
            yp = y0 + alto * (1 - min(1.0, pico))
            l.rect(xx, yp, ancho, 2, 0, con_alfa(calor(pico), 0.9))
        if rotulos:
            l.texto(nombres[i], i * paso, h - 14, paso, 14, 9, pal["gris"], "normal")


def _cascada(l, pal, w, h, medidas, x=None):
    """El historial cae como una cortina: cada fila es una lectura (la de arriba, la
    última) y cada columna un núcleo o una medida, coloreados por su carga."""
    celdas, _nombres, historial = _celdas(x, medidas)
    y0 = _cabecera(l, pal, w, h, medidas)
    alto = h - y0
    if not historial or alto < 10:
        return
    filas = max(1, min(len(historial), int(alto / 3)))
    alto_fila = alto / max(filas, 20)
    cols = max(len(f) for f in historial[-filas:])
    ancho_col = w / cols
    for j, fila in enumerate(reversed(historial[-filas:])):
        yy = y0 + j * alto_fila
        desvanece = 1 - j / max(filas, 20) * 0.6
        for i, f in enumerate(fila):
            l.rect(i * ancho_col + 0.5, yy, ancho_col - 1, alto_fila + 0.4, 0, con_alfa(calor(f), desvanece))


# --- espectrograma, araña y osciloscopio ----------------------------------------------------

# Como el "inferno" de los espectrogramas: negro, morado, rojo, naranja y amarillo claro.
INFERNO = ((0.0, (0.02, 0.01, 0.06)), (0.25, (0.33, 0.06, 0.43)), (0.5, (0.73, 0.2, 0.33)),
           (0.75, (0.98, 0.53, 0.1)), (1.0, (0.99, 0.95, 0.6)))


def inferno(f):
    f = max(0.0, min(1.0, f))
    for (f0, c0), (f1, c1) in zip(INFERNO, INFERNO[1:]):
        if f <= f1:
            return mezcla(c0, c1, (f - f0) / (f1 - f0))
    return INFERNO[-1][1]


def _espectrograma(l, pal, w, h, medidas, x=None):
    """El tiempo corre de derecha a izquierda y cada franja horizontal es un núcleo (o una
    medida): brilla de morado a amarillo según su carga, como un espectrograma de audio."""
    _celdas_, nombres, historial = _celdas(x, medidas)
    y0 = _cabecera(l, pal, w, h, medidas)
    alto = h - y0
    if not historial or alto < 10:
        return
    filas = max(len(f) for f in historial)
    rotulos = filas <= 4 and w > 120
    x_izq = 40 if rotulos else 0
    ancho = w - x_izq
    cols = min(len(historial), max(10, int(ancho / 3)))
    ancho_col = ancho / max(cols, 40)
    alto_fila = alto / filas
    l.rect(x_izq, y0, ancho, alto, 4, INFERNO[0][1])
    for j, lectura in enumerate(historial[-cols:][::-1]):
        xx = w - (j + 1) * ancho_col
        for i, f in enumerate(lectura):
            l.rect(xx, y0 + i * alto_fila, ancho_col + 0.5, alto_fila + 0.3, 0, inferno(f))
    if rotulos:
        for i, nombre in enumerate(nombres[:filas]):
            l.texto(nombre, 0, y0 + i * alto_fila, x_izq - 4, alto_fila, 9, pal["gris"], "normal", 1.0, 0.5)


def _arana(l, pal, w, h, medidas, x=None):
    """Radar de araña: un eje por núcleo (o por medida) y el polígono de la carga, con el
    de hace unos segundos en fantasma. Con menos de tres ejes, las últimas lecturas."""
    celdas, _nombres, historial = _celdas(x, medidas)
    extra = []  # polígonos de las demás medidas (cuando los ejes son lecturas)
    if len(celdas) < 3:
        # Dos medidas no dan para un polígono: los ejes son las últimas 12 lecturas, y cada
        # medida tiene el suyo, de su color.
        serie = (x or {}).get("serie") or [[m["frac"] for m in medidas]]
        tramo = serie[-12:]
        celdas = [v[0] for v in tramo]
        extra = [([v[k] for v in tramo if k < len(v)], _color(pal, m)) for k, m in enumerate(medidas[1:3], 1)]
        historial = []
    y0 = _cabecera(l, pal, w, h, medidas)
    r = min(w / 2, (h - y0) / 2) - 4
    n = len(celdas)
    if r < 14 or n < 3:
        return
    cx, cy = w / 2, y0 + (h - y0) / 2
    color = _color(pal, medidas[0])

    def punto(i, f):
        a = -math.pi / 2 + 2 * math.pi * i / n
        return cx + math.cos(a) * r * f, cy + math.sin(a) * r * f
    for nivel in (0.25, 0.5, 0.75, 1.0):  # la tela
        puntos = [punto(i, nivel) for i in range(n)]
        for p0, p1 in zip(puntos, puntos[1:] + puntos[:1]):
            l.linea(*p0, *p1, 1, con_alfa(pal["tenue"], 0.12 if nivel < 1 else 0.25))
    for i in range(n):
        l.linea(cx, cy, *punto(i, 1.0), 1, con_alfa(pal["tenue"], 0.1))
    if len(historial) > 6:
        antes = historial[-7]
        if len(antes) == n:
            l.poligono([punto(i, max(0.03, f)) for i, f in enumerate(antes)], con_alfa(pal["tenue"], 0.08))
    for valores, c in extra:
        if len(valores) == n:
            pts = [punto(i, max(0.03, min(1.0, f))) for i, f in enumerate(valores)]
            l.poligono(pts, con_alfa(c, 0.18))
            for p0, p1 in zip(pts, pts[1:] + pts[:1]):
                l.linea(*p0, *p1, 1.5, c, True)
    puntos = [punto(i, max(0.03, min(1.0, f))) for i, f in enumerate(celdas)]
    l.poligono(puntos, con_alfa(color, 0.3))
    for p0, p1 in zip(puntos, puntos[1:] + puntos[:1]):
        l.linea(*p0, *p1, 2, color, True)
    for p in puntos:
        l.circulo(*p, 2.5, color)


def _osciloscopio(l, pal, w, h, medidas, x=None):
    """Pantalla de fósforo verde con su cuadrícula: la medida principal es el trazo
    brillante (con estela) y las demás, trazos más tenues de su color."""
    serie = (x or {}).get("serie") or [[m["frac"] for m in medidas]]
    fosforo = (0.35, 1.0, 0.55)
    l.rect(0, 0, w, h, 10, (0.01, 0.06, 0.03, 0.75))
    m = 6
    ancho, alto = w - 2 * m, h - 2 * m
    for i in range(1, 10):  # cuadrícula de 10 x 8
        l.linea(m + ancho * i / 10, m, m + ancho * i / 10, m + alto, 1, con_alfa(fosforo, 0.12 if i == 5 else 0.06))
    for i in range(1, 8):
        l.linea(m, m + alto * i / 8, m + ancho, m + alto * i / 8, 1, con_alfa(fosforo, 0.12 if i == 4 else 0.06))
    puntos_max = max(10, min(len(serie), int(ancho / 4)))
    tramo = serie[-puntos_max:]
    paso = ancho / max(1, max(puntos_max, 60) - 1)
    x_fin = m + ancho

    def trazo(k, color, principal):
        pts = [(x_fin - (len(tramo) - 1 - j) * paso, m + alto * (1 - max(0.0, min(1.0, v[k]))))
               for j, v in enumerate(tramo) if k < len(v)]
        if len(pts) < 2:
            return
        for p0, p1 in zip(pts, pts[1:]):
            if principal:
                l.linea(*p0, *p1, 5, con_alfa(color, 0.15), True)  # el resplandor
            l.linea(*p0, *p1, 1.8 if principal else 1.2, con_alfa(color, 0.95 if principal else 0.55), True)
        if principal:
            l.circulo(*pts[-1], 3.5, con_alfa(color, 0.35))
            l.circulo(*pts[-1], 2, mezcla(color, (1, 1, 1), 0.5))
    for k in range(len(medidas) - 1, 0, -1):
        trazo(k, _color(pal, medidas[k]), False)
    trazo(0, fosforo, True)
    principal = medidas[0]
    if principal["texto"]:
        px = max(10.0, min(22.0, h * 0.16))
        l.texto(principal["texto"], m + 6, m + 2, ancho / 2, px * 1.4, px, fosforo, "normal", 0.0, 0.0)
    if len(medidas) > 1:
        _leyenda(l, pal, w * 0.4, m + 2, w * 0.6 - m - 4, 16, medidas[1:3], 1.0)


# --- líquido en el widget ------------------------------------------------------------------

def fondo_liquido(l, w, h, frac, color, t, burbujas=0.0, agitacion=0.0, segunda=None):
    """El líquido llenando toda la tarjeta (la tarjeta lo recorta a sus esquinas): dos capas
    de olas que van a distinto ritmo, más agitadas cuanto más alto, y burbujas que suben.
    `segunda` (frac, color): otra medida, como un líquido translúcido que ondula por detrás."""
    if segunda and segunda[0] > 0.003:
        nivel2 = h * (1 - max(0.0, min(1.0, segunda[0])))
        pasos = max(12, int(w / 8))
        pts = [(w * i / pasos, nivel2 + math.sin(i / pasos * 2 * math.pi * 1.1 - t * 1.1) * min(h * 0.03, 5.0))
               for i in range(pasos + 1)]
        l.poligono(pts + [(w, h), (0, h)], con_alfa(segunda[1], 0.22))
        for p0, p1 in zip(pts, pts[1:]):
            l.linea(*p0, *p1, 1.5, con_alfa(segunda[1], 0.6))
    f = max(0.0, min(1.0, frac))
    if f < 0.003:
        return
    nivel = h * (1 - f)
    amp = min(h * 0.035, 7.0) * (0.35 + 0.6 * f + 1.6 * agitacion) if f < 0.995 else 0
    for capa, (alfa, vel, desfase, oscuro) in enumerate(((0.28, 1.3, 1.7, 0.0), (0.5, -1.8, 0.0, 0.18))):
        puntos = []
        pasos = max(12, int(w / 8))
        for i in range(pasos + 1):
            xx = w * i / pasos
            ola = (math.sin(xx / max(w, 1) * 2 * math.pi * 1.3 + t * vel + desfase) * amp
                   + math.sin(xx / max(w, 1) * 2 * math.pi * 2.7 - t * vel * 0.7) * amp * 0.35)
            puntos.append((xx, nivel + ola - (amp * 0.6 if capa == 0 else 0)))
        puntos += [(w, h), (0, h)]
        l.poligono(puntos, con_alfa(mezcla(color, (0, 0, 0), oscuro), alfa))
    prof = h - nivel
    for i in range(int(5 + 10 * f)):
        sem = (i * 0.618) % 1
        avance = (burbujas * (0.6 + sem) + sem * 5.3) % 1
        by = h - 3 - avance * (prof - 6)
        if by > nivel + amp + 3:
            l.circulo(w * ((i * 0.381 + 0.07) % 1), by, 1 + 2.5 * sem, con_alfa((1, 1, 1), 0.22))


def _liquido(l, pal, w, h, medidas, x=None):
    """Encima del líquido (que pinta la tarjeta) solo van las cifras."""
    principal, resto = medidas[0], medidas[1:3]
    alto_ley = 18 if resto else 0
    if principal["texto"]:
        alto = min(h - alto_ley, max(24.0, h * 0.5))
        _cifra(l, pal, 0, (h - alto_ley - alto) / 2, w, alto, principal["texto"], pal["texto"], "normal")
    if resto:
        _leyenda(l, pal, 0, h - alto_ley, w, alto_ley, resto)


# --- sparkline, radar con barrido y rejilla hexagonal ------------------------------------------

def _sparkline(l, pal, w, h, medidas, x=None):
    """Como un teletipo de bolsa: una fila por medida con su nombre, su cifra y una línea
    fina de las últimas lecturas con el área degradada debajo. La principal, más grande."""
    serie = (x or {}).get("serie") or [[m["frac"] for m in medidas]]
    filas = medidas[:3]
    pesos = [2.0] + [1.0] * (len(filas) - 1)
    total = sum(pesos)
    y = 0.0
    for k, m in enumerate(filas):
        alto = h * pesos[k] / total
        color = _color(pal, m)
        ancho_txt = min(w * 0.38, 130.0)
        if k == 0:
            if m["texto"]:
                _cifra(l, pal, 0, y + alto * 0.12, ancho_txt, alto * 0.62, m["texto"], pal["texto"])
            l.texto(m["nombre"].upper(), 0, y + alto * 0.72, ancho_txt, alto * 0.22, max(8.0, min(11.0, alto * 0.16)),
                    pal["gris"], "negrita", 0.0, 0.5)
        else:
            px = max(8.0, min(12.0, alto * 0.38))
            l.texto(m["nombre"], 0, y, ancho_txt * 0.55, alto, px, pal["gris"], "normal", 0.0, 0.5)
            l.texto(m["texto"], ancho_txt * 0.5, y, ancho_txt * 0.5 - 6, alto, px, color, "normal", 1.0, 0.5)
        # La línea, de la más vieja (izquierda) a la última (derecha).
        x0, x1 = ancho_txt + 8, w - 6
        y0, y1 = y + alto * 0.15, y + alto * 0.85
        valores = [v[k] for v in serie[-60:] if k < len(v)]
        if len(valores) >= 2 and x1 - x0 > 20:
            paso = (x1 - x0) / (max(len(valores), 30) - 1)
            pts = [(x1 - (len(valores) - 1 - j) * paso, y1 - (y1 - y0) * max(0.0, min(1.0, v)))
                   for j, v in enumerate(valores)]
            for capa in range(6):  # área: franjas cada vez más transparentes hacia abajo
                fr0, fr1 = capa / 6, (capa + 1) / 6
                l.poligono([(px_, py + (y1 - py) * fr0) for px_, py in pts]
                           + [(px_, py + (y1 - py) * fr1) for px_, py in reversed(pts)],
                           con_alfa(color, 0.22 * (1 - fr0)))
            for p0, p1 in zip(pts, pts[1:]):
                l.linea(*p0, *p1, 2 if k == 0 else 1.5, color, True)
            l.circulo(*pts[-1], 3 if k == 0 else 2.2, mezcla(color, (1, 1, 1), 0.4))
        y += alto


def _barrido(l, pal, w, h, medidas, x=None):
    """Pantalla de radar: el haz gira y cada núcleo (o medida) es un eco a su ángulo, más lejos
    del centro cuanto más carga; brilla cuando lo barre el haz y se apaga despacio."""
    x = x or {}
    celdas, _nombres, _historial = _celdas(x, medidas)
    verde = (0.3, 1.0, 0.5)
    y0 = _cabecera(l, pal, w, h, medidas)
    r = min(w / 2, (h - y0) / 2) - 3
    if r < 16:
        return
    cx, cy = w / 2, y0 + (h - y0) / 2
    l.circulo(cx, cy, r, (0.01, 0.07, 0.03, 0.8))
    for k in (0.33, 0.66, 1.0):
        l.arco(cx, cy, r * k, 0, 2 * math.pi, 1, con_alfa(verde, 0.18))
    l.linea(cx - r, cy, cx + r, cy, 1, con_alfa(verde, 0.1))
    l.linea(cx, cy - r, cx, cy + r, 1, con_alfa(verde, 0.1))
    giro = (x.get("t", 0.0) * 0.45) % 1 * 2 * math.pi  # una vuelta cada ~2 s
    for k in range(18):  # la estela del haz
        a1 = giro - k * 0.05
        l.poligono([(cx, cy), (cx + math.cos(a1) * r, cy + math.sin(a1) * r),
                    (cx + math.cos(a1 - 0.05) * r, cy + math.sin(a1 - 0.05) * r)], con_alfa(verde, 0.16 * (1 - k / 18)))
    l.linea(cx, cy, cx + math.cos(giro) * r, cy + math.sin(giro) * r, 1.5, con_alfa(verde, 0.9))
    n = max(1, len(celdas))
    for i, f in enumerate(celdas):
        a = -math.pi / 2 + 2 * math.pi * i / n + 0.3
        detras = (giro - a) % (2 * math.pi)  # cuánto hace que pasó el haz
        brillo = max(0.15, 1 - detras / (2 * math.pi) * 1.4)
        rr = r * (0.12 + 0.85 * max(0.0, min(1.0, f)))
        c = mezcla(verde, pal["rojo"], max(0.0, f - 0.75) * 4)
        l.circulo(cx + math.cos(a) * rr, cy + math.sin(a) * rr, 5 * brillo + 1, con_alfa(c, 0.25 * brillo))
        l.circulo(cx + math.cos(a) * rr, cy + math.sin(a) * rr, 2.2, con_alfa(c, brillo))


def _hexagonos(l, pal, w, h, medidas, x=None):
    """Panal: un hexágono por núcleo que se enciende del azul al rojo según su carga."""
    celdas, _nombres, _historial = _celdas(x, medidas)
    y0 = _cabecera(l, pal, w, h, medidas)
    alto = h - y0
    n = len(celdas)
    if n == 0 or alto < 12:
        return
    raiz3 = math.sqrt(3)

    def tam(cols):
        filas = math.ceil(n / cols)
        por_ancho = w / (raiz3 * (cols + (0.5 if filas > 1 else 0)))
        por_alto = alto / (2 + 1.5 * (filas - 1))
        return min(por_ancho, por_alto)
    cols = max(range(1, n + 1), key=tam)
    s = tam(cols)
    filas = math.ceil(n / cols)
    ancho_total = raiz3 * s * (cols + (0.5 if filas > 1 else 0))
    alto_total = s * (2 + 1.5 * (filas - 1))
    ox, oy = (w - ancho_total) / 2 + raiz3 * s / 2, y0 + (alto - alto_total) / 2 + s
    for i, f in enumerate(celdas):
        fila, col = i // cols, i % cols
        cx = ox + col * raiz3 * s + (raiz3 * s / 2 if fila % 2 else 0)
        cy = oy + fila * 1.5 * s
        c = calor(f)
        def hexa(radio):
            return [(cx + math.cos(math.radians(60 * k - 90)) * radio, cy + math.sin(math.radians(60 * k - 90)) * radio)
                    for k in range(6)]
        l.poligono(hexa(s * 0.94), con_alfa(c, 0.18))       # halo
        l.poligono(hexa(s * 0.8), con_alfa(c, 0.35 + 0.6 * max(0.0, min(1.0, f))))
        if s > 16:
            l.texto(f"{f * 100:.0f}", cx - s, cy - s * 0.4, 2 * s, s * 0.8, s * 0.42, (1, 1, 1, 0.9), "negrita")


# --- retícula HUD, núcleo orbital y barras 3D isométricas ----------------------------------------

def _hud(l, pal, w, h, medidas, x=None):
    """Mira de ciencia ficción: anillos rotos que giran despacio, una escala con marcas, el
    arco de la carga entre corchetes y las demás medidas en arcos finos por dentro."""
    x = x or {}
    t = x.get("t", 0.0)
    principal, resto = medidas[0], medidas[1:3]
    color = mezcla(_color(pal, principal), (1, 1, 1), 0.2)
    r = min(w, h) / 2 - 3
    if r < 20:
        return
    cx, cy = w / 2, h / 2
    # Esquinas del recuadro.
    lado = min(w, h) - 2
    bx, by = cx - lado / 2, cy - lado / 2
    k = lado * 0.12
    for sx, sy in ((0, 0), (1, 0), (0, 1), (1, 1)):
        px_, py = bx + sx * lado, by + sy * lado
        dx, dy = (1 if sx == 0 else -1), (1 if sy == 0 else -1)
        l.linea(px_, py, px_ + dx * k, py, 1.5, con_alfa(color, 0.5))
        l.linea(px_, py, px_, py + dy * k, 1.5, con_alfa(color, 0.5))
    # Anillo exterior roto que gira, y otro al revés.
    for i in range(3):
        a = t * 0.35 + i * 2 * math.pi / 3
        l.arco(cx, cy, r * 0.97, a, a + 1.5, 1.5, con_alfa(color, 0.35))
    for i in range(4):
        a = -t * 0.5 + i * math.pi / 2
        l.arco(cx, cy, r * 0.9, a, a + 0.9, 3, con_alfa(color, 0.18))
    # Escala de marcas y el arco de la carga (de arriba en el sentido del reloj).
    re = r * 0.78
    for i in range(60):
        a = -math.pi / 2 + 2 * math.pi * i / 60
        largo = 0.07 if i % 5 == 0 else 0.035
        l.linea(cx + math.cos(a) * re, cy + math.sin(a) * re, cx + math.cos(a) * re * (1 - largo),
                cy + math.sin(a) * re * (1 - largo), 1, con_alfa(color, 0.4 if i % 5 == 0 else 0.2))
    f = max(0.0, min(1.0, principal["frac"]))
    a0 = -math.pi / 2
    rc = r * 0.68
    l.arco(cx, cy, rc, 0, 2 * math.pi, max(3.0, r * 0.06), con_alfa(color, 0.08))
    if f > 0.003:
        l.arco(cx, cy, rc, a0, a0 + 2 * math.pi * f, max(3.0, r * 0.06), con_alfa(color, 0.9))
        for a in (a0, a0 + 2 * math.pi * f):  # corchetes en los extremos
            l.linea(cx + math.cos(a) * rc * 0.88, cy + math.sin(a) * rc * 0.88,
                    cx + math.cos(a) * rc * 1.12, cy + math.sin(a) * rc * 1.12, 1.5, color)
    for j, m in enumerate(resto):
        rr = rc * (0.8 - j * 0.12)
        fm = max(0.0, min(1.0, m["frac"]))
        l.arco(cx, cy, rr, 0, 2 * math.pi, 1.5, con_alfa(_color(pal, m), 0.12))
        if fm > 0.003:
            l.arco(cx, cy, rr, a0, a0 + 2 * math.pi * fm, 1.5, _color(pal, m))
    # Centro: la cifra, su nombre y las demás en pequeño.
    if principal["texto"]:
        _cifra(l, pal, cx - rc * 0.55, cy - rc * 0.25, rc * 1.1, rc * 0.42, principal["texto"], color)
    if r > 45:
        px = max(7.0, r * 0.075)
        l.texto(principal["nombre"].upper(), cx - rc, cy - rc * 0.48, 2 * rc, px * 1.4, px, con_alfa(color, 0.7),
                "negrita")
        if resto:
            txt = "  ".join(f"{m['nombre']} {m['texto']}" for m in resto)
            l.texto(txt, cx - rc, cy + rc * 0.25, 2 * rc, px * 1.6, px, con_alfa(color, 0.7), "normal")


def _orbital(l, pal, w, h, medidas, x=None):
    """Un sistema solar inclinado: el núcleo brilla en el centro (más grande cuanto más carga)
    y cada núcleo de la CPU (o medida) es un planeta que orbita más deprisa cuanto más trabaja.
    Los que pasan por detrás se dibujan antes y más apagados."""
    x = x or {}
    celdas = (x.get("celdas") or [m["frac"] for m in medidas])
    fases = x.get("fases") or [i * 0.618 for i in range(len(celdas))]
    principal = medidas[0]
    color = _color(pal, principal)
    cx, cy = w / 2, h / 2
    rx = w / 2 - 8
    inclinacion = 0.36
    n = len(celdas)
    if rx < 20 or n == 0:
        return
    anillos = min(4, n)
    planetas = []
    for i, f in enumerate(celdas):
        orbita = rx * (0.4 + 0.6 * (i % anillos + 1) / anillos)
        a = 2 * math.pi * ((fases[i] if i < len(fases) else 0) + i / n)  # repartidos por la órbita
        planetas.append((math.sin(a), cx + math.cos(a) * orbita, cy + math.sin(a) * orbita * inclinacion, f))
    # Órbitas (elipses de puntitos).
    for k in range(anillos):
        orbita = rx * (0.4 + 0.6 * (k + 1) / anillos)
        for j in range(48):
            a = 2 * math.pi * j / 48
            l.circulo(cx + math.cos(a) * orbita, cy + math.sin(a) * orbita * inclinacion, 0.8,
                      con_alfa(pal["tenue"], 0.25))
    f0 = max(0.0, min(1.0, principal["frac"]))
    r_nucleo = min(h * 0.28, rx * 0.3) * (0.6 + 0.4 * f0)

    def planeta(p, detras):
        _z, px_, py, f = p
        rp = max(2.0, min(h, w) * 0.035) * (0.8 + 0.6 * f) * (0.8 if detras else 1.0)
        c = calor(f)
        l.circulo(px_, py, rp * 2, con_alfa(c, 0.12 if detras else 0.2))
        l.circulo(px_, py, rp, con_alfa(c, 0.5 if detras else 1.0))
    for p in sorted(planetas):
        if p[0] < 0:
            planeta(p, True)
    for k in range(5, 0, -1):  # el núcleo con su resplandor
        l.circulo(cx, cy, r_nucleo * (1 + k * 0.18), con_alfa(color, 0.05 * (6 - k) / 2))
    l.circulo(cx, cy, r_nucleo, mezcla(color, (1, 1, 1), 0.15))
    l.circulo(cx - r_nucleo * 0.3, cy - r_nucleo * 0.3, r_nucleo * 0.35, con_alfa((1, 1, 1), 0.25))
    for p in sorted(planetas):
        if p[0] >= 0:
            planeta(p, False)
    if principal["texto"]:
        _cifra(l, pal, cx - r_nucleo * 0.8, cy - r_nucleo * 0.4, r_nucleo * 1.6, r_nucleo * 0.8, principal["texto"],
               (1, 1, 1), "negrita")


def _iso(l, pal, w, h, medidas, x=None):
    """Una ciudad de barras en perspectiva isométrica: un prisma por núcleo (o medida), con
    su cara de arriba más clara, más alto y más caliente de color cuanto más carga."""
    celdas, _nombres, _historial = _celdas(x, medidas)
    y0 = _cabecera(l, pal, w, h, medidas)
    alto = h - y0
    n = len(celdas)
    if n == 0 or alto < 20:
        return
    cols = n if n <= 4 else min(range(2, n + 1), key=lambda c: abs(c - math.ceil(n / c) * 2) + (0.5 if n % c else 0))
    filas = math.ceil(n / cols)
    cos30, sin30 = math.cos(math.radians(30)), 0.5
    # Con escala 1: suelo de cols x filas y columnas de altura `zmax`.
    zmax = 2.4
    ancho_1 = (cols + filas) * cos30
    alto_1 = (cols + filas) * sin30 + zmax
    s = min(w / ancho_1, alto / alto_1) * 0.95
    ox = w / 2 + (filas - cols) * cos30 * s / 2
    oy = y0 + (alto - alto_1 * s) / 2 + zmax * s

    def iso(gx, gy, z):
        return ox + (gx - gy) * cos30 * s, oy + (gx + gy) * sin30 * s - z * s
    # El suelo.
    l.poligono([iso(0, 0, 0), iso(cols, 0, 0), iso(cols, filas, 0), iso(0, filas, 0)], con_alfa(pal["tenue"], 0.06))
    orden = sorted(range(n), key=lambda i: (i // cols) + (i % cols))  # de atrás hacia delante
    for i in orden:
        gx, gy = i % cols + 0.15, i // cols + 0.15
        lado = 0.7
        f = max(0.0, min(1.0, celdas[i]))
        z = max(0.05, f * zmax)
        c = calor(f)
        arriba = [iso(gx, gy, z), iso(gx + lado, gy, z), iso(gx + lado, gy + lado, z), iso(gx, gy + lado, z)]
        izquierda = [iso(gx, gy + lado, 0), iso(gx + lado, gy + lado, 0), iso(gx + lado, gy + lado, z), iso(gx, gy + lado, z)]
        derecha = [iso(gx + lado, gy, 0), iso(gx + lado, gy + lado, 0), iso(gx + lado, gy + lado, z), iso(gx + lado, gy, z)]
        l.poligono(izquierda, mezcla(c, (0, 0, 0), 0.35))
        l.poligono(derecha, mezcla(c, (0, 0, 0), 0.15))
        l.poligono(arriba, mezcla(c, (1, 1, 1), 0.2))


# --- paisaje del historial, chip en isométrico y cubo ----------------------------------------

def _suave(valores, u):
    """Curva Catmull-Rom por los valores (u de 0 a 1): picos redondeados, sin esquinas."""
    n = len(valores)
    if n == 1:
        return valores[0]
    pos = u * (n - 1)
    i = min(int(pos), n - 2)
    s = pos - i
    p0, p1, p2, p3 = (valores[max(0, i - 1)], valores[i], valores[i + 1], valores[min(n - 1, i + 2)])
    return 0.5 * (2 * p1 + (p2 - p0) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s * s
                  + (3 * p1 - p0 - 3 * p2 + p3) * s * s * s)


def _recorta_linea(p0, p1, x_min, x_max):
    """El tramo de la línea que cae entre x_min y x_max (None si nada)."""
    (x0, y0), (x1, y1) = p0, p1
    if x0 > x1:
        (x0, y0), (x1, y1) = (x1, y1), (x0, y0)
    if x1 < x_min or x0 > x_max:
        return None
    if x1 - x0 > 1e-9:
        if x0 < x_min:
            y0 += (y1 - y0) * (x_min - x0) / (x1 - x0)
            x0 = x_min
        if x1 > x_max:
            y1 = y0 + (y1 - y0) * (x_max - x0) / (x1 - x0)
            x1 = x_max
    return (x0, y0), (x1, y1)


def _recorta_poligono(puntos, x_min, x_max):
    """Sutherland-Hodgman contra las dos rectas verticales x_min y x_max."""
    for limite, dentro in ((x_min, lambda q: q[0] >= x_min), (x_max, lambda q: q[0] <= x_max)):
        salida = []
        for i, q in enumerate(puntos):
            prev = puntos[i - 1]
            if dentro(q) != dentro(prev):
                s = (limite - prev[0]) / (q[0] - prev[0])
                salida.append((limite, prev[1] + (q[1] - prev[1]) * s))
            if dentro(q):
                salida.append(q)
        puntos = salida
        if not puntos:
            break
    return puntos


def _paisaje(l, pal, w, h, medidas, x=None):
    """Un terreno 3D en malla (como los fondos synthwave): cada fila es una lectura, con un monte
    por núcleo (o por medida), y las filas se alejan hacia el horizonte deslizándose sin saltos
    entre lectura y lectura. Se pinta de atrás adelante: los montes tapan lo que hay detrás. Lo
    lejano se pierde en la niebla y los picos se calientan de color con la altura."""
    x = x or {}
    historial = x.get("historial") or [[m["frac"] for m in medidas]]
    color = _color(pal, medidas[0])
    fondo = (0.02, 0.02, 0.04)
    l.rect(0, 0, w, h, 8, (*fondo, 0.9))
    horizonte = h * 0.34
    cx = w / 2
    for k in range(8):  # resplandor del horizonte
        l.rect(2, horizonte - k * 2.5, w - 4, 2.5, 0, con_alfa(color, 0.06 * (1 - k / 8)))
    # Cada fila, a la distancia que le toca por el tiempo que hace que llegó: avanza a velocidad
    # constante, sin pararse aunque una lectura llegue un poco tarde.
    n = 14
    edades = x.get("edades") or list(range(len(historial) - 1, -1, -1))
    filas = list(reversed(historial[-(n + 3):]))  # la más nueva primero (+3: las que aún están entrando)
    edades = list(reversed(edades[-(n + 3):]))
    if len(edades) != len(filas):
        edades = list(range(len(filas)))
    # El perfil de cada fila: los valores suavizados (sin dientes de sierra) y muestreados.
    # Columnas: tupidas donde están los montes y sueltas en el suelo llano de los lados
    # (que sigue más allá de la pantalla).
    us = ([-0.35 + 0.45 * k / 3 for k in range(3)] + [0.1 + 0.8 * k / 23 for k in range(24)]
          + [0.9 + 0.45 * (k + 1) / 3 for k in range(3)])
    cols = len(us)

    def perfil(valores):
        if len(valores) > 3:
            valores = [(valores[max(0, i - 1)] + 2 * v + valores[min(len(valores) - 1, i + 1)]) / 4
                       for i, v in enumerate(valores)]
        salida = []
        for u in us:
            dentro = (u - 0.1) / 0.8
            if 0 <= dentro <= 1:
                salida.append(max(0.0, _suave(valores, dentro)) * math.sin(math.pi * dentro) ** 1.2)
            else:
                salida.append(0.0)
        return salida

    def prof(edad):
        # Paso creciente (como una perspectiva de verdad): la última fila llega al horizonte.
        return 28 ** (edad / n)

    def proyecta(u, edad, v):
        z = prof(edad)
        y_suelo = horizonte + (h - horizonte) * 0.97 / z
        return cx + (u - 0.5) * w * 1.25 / z, y_suelo - (h - horizonte) * 0.85 * v / z

    # Con tres lecturas de retraso: la fila nueva nace por delante de la cámara (debajo del panel),
    # plana, y va levantando sus montes mientras entra; así ni un pico alto asoma de golpe.
    retraso = 3.0
    malla = []
    for e, f in zip(edades, filas):
        edad = e - retraso
        sube = max(0.0, min(1.0, (e - 0.3) / (retraso - 0.3)))
        sube = sube * sube * (3 - 2 * sube)
        malla.append((edad, [v * sube for v in perfil(f)]))
    # La fila nueva entra desde delante (fuera de la pantalla) y las demás se alejan.
    for j in range(len(malla) - 1, 0, -1):  # franjas, de la más lejana a la más cercana
        edad_lejos, lejos = malla[j]
        edad_cerca, cerca = malla[j - 1]
        niebla = max(0.0, min(1.0, 1 - edad_lejos / n)) ** 1.2
        grosor = 0.5 + 1.2 / prof(edad_cerca)
        for k in range(cols - 1):
            a0, a1 = proyecta(us[k], edad_lejos, lejos[k]), proyecta(us[k + 1], edad_lejos, lejos[k + 1])
            b0, b1 = proyecta(us[k], edad_cerca, cerca[k]), proyecta(us[k + 1], edad_cerca, cerca[k + 1])
            if max(a0[0], a1[0], b0[0], b1[0]) <= 1.0 or min(a0[0], a1[0], b0[0], b1[0]) >= w - 1.0:
                continue  # entera fuera del panel
            trozo = _recorta_poligono([a0, a1, b1, b0], 1.0, w - 1.0)
            if len(trozo) >= 3:
                l.poligono(trozo, fondo)
            alto = max(cerca[k], cerca[k + 1], lejos[k])
            c = con_alfa(mezcla(color, calor(alto), min(1.0, alto * 1.5)), 0.1 + 0.9 * niebla)
            for q0, q1, g, cc in ((b0, b1, grosor, c),                                   # la cresta (fila)
                                  (a0, b0, grosor * 0.7, con_alfa(c, c[3] * 0.55))):   # hacia el fondo
                tramo = _recorta_linea(q0, q1, 1.0, w - 1.0)
                if tramo:
                    l.linea(*tramo[0], *tramo[1], g, cc, True)
    _cifras_arriba(l, pal, w, h, medidas)


def _chip(l, pal, w, h, medidas, x=None):
    """El procesador en isométrico: placa verde con patillas doradas, el encapsulado y, encima,
    una baldosa por núcleo que se levanta y se calienta de color con su carga."""
    celdas, _nombres, _historial = _celdas(x, medidas)
    y0 = _cabecera(l, pal, w, h, medidas)
    alto = h - y0
    n = len(celdas)
    if n == 0 or alto < 30:
        return
    cols = max(1, round(math.sqrt(n)))
    filas = math.ceil(n / cols)
    lado = max(cols, filas)
    cos30 = math.cos(math.radians(30))
    placa = lado + 2.0  # la placa: los núcleos más un borde para las patillas
    s = min(w / (2 * placa * cos30), alto / (placa + 1.6)) * 0.95
    ox = w / 2
    oy = y0 + (alto - (placa + 1.6) * s) / 2 + 1.0 * s

    def iso(gx, gy, z):
        return ox + (gx - gy) * cos30 * s, oy + (gx + gy) * 0.5 * s - z * s

    def caja_iso(x0, y0_, x1, y1, z0, z1, color):
        l.poligono([iso(x0, y1, z0), iso(x1, y1, z0), iso(x1, y1, z1), iso(x0, y1, z1)], mezcla(color, (0, 0, 0), 0.4))
        l.poligono([iso(x1, y0_, z0), iso(x1, y1, z0), iso(x1, y1, z1), iso(x1, y0_, z1)], mezcla(color, (0, 0, 0), 0.2))
        l.poligono([iso(x0, y0_, z1), iso(x1, y0_, z1), iso(x1, y1, z1), iso(x0, y1, z1)], color)
    caja_iso(0, 0, placa, placa, 0, 0.12, (0.1, 0.35, 0.2))                      # placa
    oro = (0.85, 0.68, 0.3)
    for k in range(int(placa * 3)):                                               # patillas
        u = 0.3 + k / 3
        if u > placa - 0.3:
            break
        l.linea(*iso(u, placa, 0.12), *iso(u, placa + 0.25, 0.05), max(1.0, s * 0.05), oro)
        l.linea(*iso(placa, u, 0.12), *iso(placa + 0.25, u, 0.05), max(1.0, s * 0.05), oro)
    caja_iso(0.7, 0.7, placa - 0.7, placa - 0.7, 0.12, 0.3, (0.16, 0.17, 0.2))   # encapsulado
    for i in sorted(range(n), key=lambda i: (i // cols) + (i % cols)):            # núcleos, de atrás adelante
        gx, gy = 1 + (i % cols) * lado / cols, 1 + (i // cols) * lado / filas
        f = max(0.0, min(1.0, celdas[i]))
        tam = lado / max(cols, filas) * 0.82
        caja_iso(gx + 0.05, gy + 0.05, gx + tam, gy + tam, 0.3, 0.32 + f * 0.6, calor(f))


def _cubo(l, pal, w, h, medidas, x=None):
    """Un cubo de cristal que gira más deprisa cuanto más carga hay, del color de su carga;
    dentro, otro más pequeño con la segunda medida. Las cifras, al lado."""
    x = x or {}
    fase = x.get("fase", 0.0)
    principal, resto = medidas[0], medidas[1:3]
    al_lado = w >= h + 60  # si no hay sitio para las cifras a la derecha, van debajo
    lado = min(h, w) if al_lado else min(w, h * 0.72)
    cx, cy = (lado / 2, h / 2) if al_lado else (w / 2, lado / 2)
    f = max(0.0, min(1.0, principal["frac"]))
    color = mezcla(_color(pal, principal), calor(f), 0.5)
    a, b = fase * 2 * math.pi, 0.55 + math.sin(fase * 2 * math.pi * 0.3) * 0.25

    def proyecta(px_, py, pz, tam):
        # Giro sobre el eje vertical (a) y luego inclinado hacia delante (b).
        x1 = px_ * math.cos(a) + pz * math.sin(a)
        z1 = -px_ * math.sin(a) + pz * math.cos(a)
        y2 = py * math.cos(b) - z1 * math.sin(b)
        z2 = py * math.sin(b) + z1 * math.cos(b)
        p = 4.5 / (4.5 + z2)  # perspectiva
        return cx + x1 * tam * p, cy + y2 * tam * p, z2

    vertices = [(i, j, k) for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)]
    caras = ((0, 1, 3, 2), (4, 5, 7, 6), (0, 1, 5, 4), (2, 3, 7, 6), (0, 2, 6, 4), (1, 3, 7, 5))

    def cubo(tam, color, alfa):
        pts = [proyecta(*v, tam) for v in vertices]
        for cara in sorted(caras, key=lambda c: -sum(pts[i][2] for i in c)):  # de atrás adelante
            l.poligono([pts[i][:2] for i in cara], con_alfa(color, alfa))
        for i, v in enumerate(vertices):
            for j in range(i + 1, 8):
                if sum(a_ != b_ for a_, b_ in zip(v, vertices[j])) == 1:
                    l.linea(*pts[i][:2], *pts[j][:2], 1.5, con_alfa(mezcla(color, (1, 1, 1), 0.4), 0.9), True)
    tam = lado * 0.2  # con el giro y la perspectiva, la diagonal del cubo cabe en `lado`
    if tam < 8:
        return
    cubo(tam, color, 0.12 + 0.2 * f)
    if resto:
        m = resto[0]
        cubo(tam * (0.25 + 0.5 * max(0.0, min(1.0, m["frac"]))), _color(pal, m), 0.35)
    if not al_lado:
        if principal["texto"]:
            _cifra(l, pal, 0, lado, w, h - lado - (16 if resto else 0), principal["texto"], pal["texto"])
        if resto:
            _leyenda(l, pal, 0, h - 16, w, 16, resto)
        return
    # Las cifras a la derecha.
    tx = lado + 4
    if w - tx > 50:
        if principal["texto"]:
            _cifra(l, pal, tx, h * 0.2, w - tx, h * 0.35, principal["texto"], pal["texto"])
        px = max(8.0, min(12.0, h * 0.1))
        y = h * 0.6
        for m in resto:
            l.circulo(tx + px * 0.3, y + px * 0.7, px * 0.28, _color(pal, m))
            l.texto(f"{m['nombre']} {m['texto']}", tx + px, y, w - tx - px, px * 1.4, px, pal["gris"], "normal",
                    0.0, 0.5)
            y += px * 1.6


# --- llamas, lámpara de lava, electrocardiograma, aurora y ondas ------------------------------

def _ruido(u, t, semilla):
    """Ondulación suave y sin patrón visible (suma de senos), entre -1 y 1."""
    return (math.sin(u * 7.3 + t * 3.1 + semilla) * 0.5 + math.sin(u * 13.7 - t * 4.3 + semilla * 2.1) * 0.3
            + math.sin(u * 3.1 + t * 1.7 + semilla * 0.7) * 0.2)


def _segunda(medidas, x):
    """(frac, medida, avance acumulado) de la segunda medida, o None si no hay."""
    if len(medidas) < 2:
        return None
    avances = (x or {}).get("avances") or []
    return (max(0.0, min(1.0, medidas[1]["frac"])), medidas[1], avances[1] if len(avances) > 1 else 0.0)


def _cifras_arriba(l, pal, w, h, medidas, color=None, tapa=False):
    """Cifra principal arriba a la izquierda y las demás a la derecha (para fondos animados).
    Con `tapa`, una franja oscura detrás para que se lean sobre dibujos muy cargados."""
    principal, resto = medidas[0], medidas[1:3]
    alto = max(14.0, min(30.0, h * 0.22))
    if tapa and (principal["texto"] or resto):
        l.rect(0, 0, w, alto + 8, 8, (0.0, 0.0, 0.0, 0.7))
    ocupado = 0
    if principal["texto"]:
        px = px_que_quepa(l, principal["texto"], w * 0.45, alto)
        ocupado = l.medir(principal["texto"], px, "fino")[0] + 14
        l.texto(principal["texto"], 6, 4, ocupado, alto, px, color or pal["texto"], "fino", 0.0, 0.5)
    if resto:
        _leyenda(l, pal, ocupado, 4, w - ocupado - 6, alto, resto, 1.0)


def _llamas(l, pal, w, h, medidas, x=None):
    """Fuego desde abajo: lenguas de llama que titilan, más altas cuanto más carga, de rojo por
    fuera a amarillo por dentro; chispas que suben."""
    x = x or {}
    t = x.get("t", 0.0)
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    alto_max = h * (0.25 + 0.65 * f)
    capas = (((0.85, 0.15, 0.08), 1.0, 0.75), ((1.0, 0.45, 0.1), 0.78, 0.85), ((1.0, 0.8, 0.25), 0.52, 0.9),
             ((1.0, 0.97, 0.75), 0.28, 0.85))
    pasos = max(20, int(w / 5))
    s2 = _segunda(medidas, x)
    if s2:  # la segunda medida: otra llama de su color, por detrás
        alto2 = h * (0.2 + 0.7 * s2[0])
        pts = [(0, h)] + [(w * k / pasos, h - alto2 * (0.55 + 0.45 * _ruido(k / pasos * 1.3, t * 1.1, 9.0))
                           * math.sin(math.pi * k / pasos) ** 0.5) for k in range(pasos + 1)] + [(w, h)]
        l.poligono(pts, con_alfa(_color(pal, s2[1]), 0.45))
    for c, escala, alfa in capas:
        pts = [(0, h)]
        for k in range(pasos + 1):
            u = k / pasos
            # Varias lenguas: picos donde el seno compuesto es alto; los bordes, más bajos.
            lenguas = 0.55 + 0.45 * _ruido(u * 1.6, t * 1.3, escala * 5)
            borde = math.sin(math.pi * u) ** 0.5
            alto = alto_max * escala * lenguas * borde
            pts.append((w * u, h - alto))
        pts.append((w, h))
        l.poligono(pts, con_alfa(c, alfa))
    for i in range(int(4 + 10 * f)):  # chispas
        sem = (i * 0.618) % 1
        avance = (x.get("burbujas", 0.0) * 2.2 * (0.7 + sem) + sem * 4.1) % 1
        cx = w * ((i * 0.381 + 0.11) % 1) + math.sin(t * 2 + i) * 6
        cy = h - avance * h * 0.95
        l.circulo(cx, cy, 1.4, con_alfa((1.0, 0.75, 0.3), (1 - avance) * 0.9))
    _cifras_arriba(l, pal, w, h, medidas)


def _lava(l, pal, w, h, medidas, x=None):
    """Lámpara de lava: el cristal estrecho arriba y ancho abajo, con su tapa y su base; las
    gotas suben y bajan despacio (más deprisa cuanto más carga) y se juntan al tocarse."""
    x = x or {}
    principal, resto = medidas[0], medidas[1:3]
    color = _color(pal, principal)
    ancho = min(w, h * 0.5)
    cx = ancho / 2
    arriba, abajo = h * 0.12, h * 0.86
    r_arriba, r_abajo = ancho * 0.28, ancho * 0.46

    def radio_en(y):
        return r_arriba + (r_abajo - r_arriba) * (y - arriba) / (abajo - arriba)
    l.poligono([(cx - r_arriba * 0.7, 2), (cx + r_arriba * 0.7, 2), (cx + r_arriba, arriba),
                (cx - r_arriba, arriba)], (0.55, 0.57, 0.62))                                   # tapa
    l.poligono([(cx - r_arriba, arriba), (cx + r_arriba, arriba), (cx + r_abajo, abajo),
                (cx - r_abajo, abajo)], con_alfa(mezcla(color, (0, 0, 0), 0.75), 0.9))          # cristal
    l.poligono([(cx - r_abajo, abajo), (cx + r_abajo, abajo), (cx + r_abajo * 0.75, h - 1),
                (cx - r_abajo * 0.75, h - 1)], (0.55, 0.57, 0.62))                              # base
    f = max(0.0, min(1.0, principal["frac"]))
    mov = x.get("burbujas", 0.0) * 0.8
    caliente = mezcla(color, (1.0, 0.55, 0.3), 0.35)
    l.circulo(cx, abajo, r_abajo * 0.75, caliente)  # el charco de abajo
    s2 = _segunda(medidas, x)
    for i in range(5 + int(3 * f)):
        sem = (i * 0.618) % 1
        segunda = s2 and i % 2 == 1  # las impares, de la segunda medida
        mov_i = s2[2] * 1.6 if segunda else mov
        # Cada gota sube y baja con su propio ritmo (coseno: frena arriba y abajo).
        ciclo = (mov_i * (0.6 + sem * 0.8) + sem) % 1
        altura = (1 - math.cos(ciclo * 2 * math.pi)) / 2
        y = abajo - 6 - altura * (abajo - arriba - 12)
        r = radio_en(y) * (0.25 + 0.3 * sem)
        bx = cx + math.sin(mov_i * 2 + i * 1.7) * (radio_en(y) - r) * 0.6
        l.circulo(bx, y, r, mezcla(_color(pal, s2[1]), (1.0, 0.6, 0.4), 0.3) if segunda else caliente)
    l.linea(cx - r_arriba * 0.6, arriba + 6, cx - r_abajo * 0.6, abajo - 6, 2, con_alfa((1, 1, 1), 0.15), True)
    tx = ancho + 10
    if w - tx > 50:
        if principal["texto"]:
            _cifra(l, pal, tx, h * 0.2, w - tx, h * 0.32, principal["texto"], pal["texto"])
        px = max(8.0, min(12.0, h * 0.1))
        y = h * 0.58
        for m in resto:
            l.circulo(tx + px * 0.3, y + px * 0.7, px * 0.28, _color(pal, m))
            l.texto(f"{m['nombre']} {m['texto']}", tx + px, y, w - tx - px, px * 1.4, px, pal["gris"], "normal",
                    0.0, 0.5)
            y += px * 1.6


def _pqrst(fase):
    """Un latido (fase 0-1): onda P, el pico QRS y la onda T, como en un electro de verdad."""
    def campana(c, ancho, alto):
        return alto * math.exp(-((fase - c) / ancho) ** 2)
    return (campana(0.12, 0.035, 0.12) - campana(0.245, 0.012, 0.12) + campana(0.27, 0.014, 1.0)
            - campana(0.295, 0.014, 0.28) + campana(0.5, 0.06, 0.22))


def _electro(l, pal, w, h, medidas, x=None):
    """Monitor de constantes: cuadrícula, el trazo del latido corriendo hacia la izquierda y
    las pulsaciones por minuto, que suben con la carga."""
    x = x or {}
    latidos = x.get("latidos", 0.0)
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    ritmo = 0.9 + 1.6 * f  # latidos por segundo (igual que en la vista)
    verde = (0.35, 1.0, 0.55)
    l.rect(0, 0, w, h, 10, (0.01, 0.05, 0.03, 0.75))
    for i in range(1, int(w / 16) + 1):
        l.linea(i * 16, 0, i * 16, h, 1, con_alfa(verde, 0.05))
    for i in range(1, int(h / 16) + 1):
        l.linea(0, i * 16, w, i * 16, 1, con_alfa(verde, 0.05))
    segundos = 3.0  # lo que cabe en pantalla
    base = h * 0.66
    amp = h * 0.42
    pts = []
    pasos = max(60, int(w / 2))
    for k in range(pasos + 1):
        u = k / pasos
        atras = (1 - u) * segundos
        fase = (latidos - atras * ritmo) % 1
        pts.append((u * w, base - amp * _pqrst(fase)))
    for k, (p0, p1) in enumerate(zip(pts, pts[1:])):
        alfa = 0.25 + 0.75 * k / pasos  # se apaga hacia la izquierda, como el fósforo
        l.linea(*p0, *p1, 4, con_alfa(verde, 0.12 * alfa), True)
        l.linea(*p0, *p1, 1.6, con_alfa(verde, alfa), True)
    l.circulo(*pts[-1], 3, mezcla(verde, (1, 1, 1), 0.5))
    s2 = _segunda(medidas, x)
    if s2:
        latidos2 = x.get("t", 0.0) * 0.77 + s2[2] * 3.2  # de 54 a 150 por minuto, como el principal
        ritmo2 = 0.9 + 1.6 * s2[0]
        base2, amp2 = h * 0.9, h * 0.16
        c2 = _color(pal, s2[1])
        pts2 = [(u * w, base2 - amp2 * _pqrst((latidos2 - (1 - u) * segundos * ritmo2) % 1))
                for u in (k / pasos for k in range(pasos + 1))]
        for k, (p0, p1) in enumerate(zip(pts2, pts2[1:])):
            l.linea(*p0, *p1, 1.2, con_alfa(c2, 0.2 + 0.6 * k / pasos), True)
    _cifras_arriba(l, pal, w, h, medidas, verde)
    px = max(8.0, min(12.0, h * 0.09))
    l.texto(f"♥ {ritmo * 60:.0f}", w - 70, h - px * 1.8, 64, px * 1.5, px, con_alfa(verde, 0.8), "negrita", 1.0, 0.5)


def _aurora(l, pal, w, h, medidas, x=None):
    """Aurora boreal: cortinas de luz que ondulan sobre un cielo con estrellas; más altas,
    más brillantes y más agitadas cuanto más carga."""
    x = x or {}
    t = x.get("t", 0.0)
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    l.rect(0, 0, w, h, 8, (0.01, 0.02, 0.06, 0.7))
    for i in range(24):  # estrellas
        sx, sy = w * ((i * 0.618) % 1), h * ((i * 0.381 + 0.05) % 0.6)
        l.circulo(sx, sy, 0.8, con_alfa((1, 1, 1), 0.3 + 0.3 * math.sin(t * 1.5 + i)))
    colores = ((0.25, 1.0, 0.55), (0.3, 0.85, 0.95), (0.7, 0.4, 1.0))
    # Lo que han avanzado las cortinas: un ritmo fijo más `fase`, que se acumula más deprisa con más
    # carga (multiplicar el tiempo por una velocidad que cambia las haría saltar).
    mov = t * 0.25 + x.get("fase", 0.0)
    paso = 3.0
    for b, c in enumerate(colores):
        fb = max(0.0, min(1.0, medidas[b]["frac"])) if b < len(medidas) else f  # cada cortina, una medida
        if b < len(medidas) and b > 0:
            c = mezcla(c, _color(pal, medidas[b]), 0.5)
        base = h * (0.55 + 0.12 * b)
        alto = h * (0.15 + 0.4 * fb) * (1 - b * 0.2)
        brillo = 0.18 + 0.4 * fb
        for k in range(int(w / paso) + 1):
            u = k * paso / w
            onda = _ruido(u * (1.2 + b * 0.4), mov, b * 2.3)
            top = base - alto * (0.6 + 0.4 * onda) + math.sin(u * 5 + t * 0.6 + b) * h * 0.05
            intensidad = brillo * (0.55 + 0.45 * _ruido(u * 3, t * 0.4, b + 7))
            # La cortina: fuerte abajo y desvaneciéndose hacia arriba (tres tramos).
            largo = base + h * 0.08 - top
            for tramo, a in ((0.0, 0.25), (0.33, 0.55), (0.66, 1.0)):
                l.rect(k * paso, top + largo * tramo, paso + 0.5, largo / 3 + 0.5, 0,
                       con_alfa(c, max(0.0, intensidad * a)))
    _cifras_arriba(l, pal, w, h, medidas)


def _ondas(l, pal, w, h, medidas, x=None):
    """Gotas que caen en el centro y forman ondas que se abren y se apagan; caen más seguido
    cuanto más carga. La cifra, en la gota."""
    x = x or {}
    principal, resto = medidas[0], medidas[1:3]
    color = _color(pal, principal)
    alto_ley = 16 if resto else 0
    cx, cy = w / 2, (h - alto_ley) / 2
    rx, ry = w / 2 - 2, (h - alto_ley) / 2 - 2
    avance = x.get("burbujas", 0.0) * 1.5
    n = 6
    for k in range(n):
        edad = (avance + k / n) % 1
        alfa = (1 - edad) ** 1.5
        # Elipses (vistas un poco desde arriba): se dibujan como polígonos de líneas.
        pts = [(cx + math.cos(a) * rx * edad, cy + math.sin(a) * ry * edad)
               for a in (2 * math.pi * j / 64 for j in range(65))]
        for p0, p1 in zip(pts, pts[1:]):
            l.linea(*p0, *p1, 1 + 2.5 * (1 - edad), con_alfa(color, 0.7 * alfa))
    s2 = _segunda(medidas, x)
    if s2:  # la segunda medida: otras ondas, de su color y a su ritmo
        c2 = _color(pal, s2[1])
        for k in range(4):
            edad = (s2[2] * 2.2 + k / 4) % 1
            pts = [(cx + math.cos(a) * rx * edad, cy + math.sin(a) * ry * edad)
                   for a in (2 * math.pi * j / 48 for j in range(49))]
            for p0, p1 in zip(pts, pts[1:]):
                l.linea(*p0, *p1, 1 + 1.5 * (1 - edad), con_alfa(c2, 0.55 * (1 - edad) ** 1.5 * (0.3 + 0.7 * s2[0])))
    r = min(rx, ry) * 0.42
    l.circulo(cx, cy, r, con_alfa(color, 0.25))
    l.circulo(cx, cy, r * 0.82, con_alfa(mezcla(color, (0, 0, 0), 0.3), 0.6))
    if principal["texto"]:
        _cifra(l, pal, cx - r * 0.75, cy - r * 0.4, r * 1.5, r * 0.8, principal["texto"], pal["texto"])
    if resto:
        _leyenda(l, pal, 0, h - alto_ley, w, alto_ley, resto)


# --- hiperespacio, donut ASCII y vúmetro ---------------------------------------------------------

def _hiperespacio(l, pal, w, h, medidas, x=None):
    """Salto al hiperespacio: las estrellas vienen hacia ti desde el centro, más deprisa y con
    estelas más largas cuanto más carga; con mucha, se tiñen del color caliente."""
    x = x or {}
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    viaje = x.get("fase", 0.0) * 1.6  # distancia recorrida (acumulada: cambiar de velocidad no salta)
    l.rect(0, 0, w, h, 8, (0.0, 0.0, 0.03, 0.85))
    cx, cy = w / 2, h / 2
    escala = max(w, h) * 0.5
    estela = 0.02 + 0.22 * f
    def azar(i, sal):  # pseudoaleatorio fijo por estrella (sin patrones visibles)
        return (math.sin(i * 12.9898 + sal * 78.233) * 43758.5453) % 1
    s2 = _segunda(medidas, x)
    for i in range(140):
        segunda = s2 and i % 3 == 0  # un tercio de las estrellas, de la segunda medida
        a = azar(i, 1) * 2 * math.pi
        r = 0.08 + azar(i, 2) * 0.92
        z = 1 - (azar(i, 3) + (s2[2] * 1.6 if segunda else viaje)) % 1  # 1 lejos, 0 encima
        if z < 0.02:
            continue
        z0 = min(1.0, z + estela)
        x1, y1 = cx + math.cos(a) * r / z * escala * 0.25, cy + math.sin(a) * r / z * escala * 0.25
        x0, y0 = cx + math.cos(a) * r / z0 * escala * 0.25, cy + math.sin(a) * r / z0 * escala * 0.25
        if not (-20 < x1 < w + 20 and -20 < y1 < h + 20):
            continue
        brillo = min(1.0, (1 - z) * 1.6)
        color = (_color(pal, s2[1]) if segunda
                 else mezcla((0.75, 0.85, 1.0), calor(f), max(0.0, f - 0.5) * 1.6))
        l.linea(x0, y0, x1, y1, 0.6 + 1.8 * (1 - z), con_alfa(color, brillo), True)
    l.circulo(cx, cy, 6 + 10 * f, con_alfa((0.7, 0.8, 1.0), 0.06 + 0.1 * f))  # resplandor del centro
    _cifras_arriba(l, pal, w, h, medidas)


LUZ_ASCII = ".,-~:;=!*#$@"


def _donut(l, pal, w, h, medidas, x=None):
    """El donut ASCII de toda la vida (un toro iluminado, hecho de caracteres) girando más deprisa
    cuanto más carga, y del color de su carga."""
    x = x or {}
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    giro = x.get("fase", 0.0) * 2 * math.pi
    a_, b_ = giro * 1.0, giro * 0.5
    arriba = max(14.0, min(30.0, h * 0.22)) + 4  # debajo de la cifra
    filas = max(8, min(20, int((h - arriba) / 10)))
    alto_c = (h - arriba) / filas
    ancho_c = l.medir("@", alto_c, "mono")[0] or alto_c * 0.6
    cols = max(10, int(w / ancho_c))
    salida = [[" "] * cols for _ in range(filas)]
    zbuf = [[0.0] * cols for _ in range(filas)]
    ca, sa, cb, sb = math.cos(a_), math.sin(a_), math.cos(b_), math.sin(b_)
    s2 = _segunda(medidas, x)
    r1, r2, k2 = (0.55 + 0.75 * s2[0]) if s2 else 1.0, 2.0, 5.0  # el grosor del tubo: la segunda medida
    k1 = min(cols * ancho_c, h - arriba) * k2 * 2.6 / (8 * (r1 + r2)) / alto_c  # en filas
    for i in range(0, 110):
        theta = 2 * math.pi * i / 110
        ct, st = math.cos(theta), math.sin(theta)
        for j in range(0, 44):
            phi = 2 * math.pi * j / 44
            cp, sp = math.cos(phi), math.sin(phi)
            cx_ = r2 + r1 * ct
            cy_ = r1 * st
            px_ = cx_ * (cb * cp + sa * sb * sp) - cy_ * ca * sb
            py_ = cx_ * (sb * cp - sa * cb * sp) + cy_ * ca * cb
            pz = k2 + ca * cx_ * sp + cy_ * sa
            ooz = 1 / pz
            col = int(cols / 2 + k1 * ooz * px_ * alto_c / ancho_c)
            fil = int(filas / 2 - k1 * ooz * py_)
            luz = cp * ct * sb - ca * ct * sp - sa * st + cb * (ca * st - ct * sa * sp)
            if 0 <= col < cols and 0 <= fil < filas and luz > 0 and ooz > zbuf[fil][col]:
                zbuf[fil][col] = ooz
                salida[fil][col] = LUZ_ASCII[min(len(LUZ_ASCII) - 1, int(luz * 8))]
    color = mezcla(_color(pal, medidas[0]), calor(f), 0.4)
    x0 = (w - cols * ancho_c) / 2
    for k, fila in enumerate(salida):
        texto = "".join(fila).rstrip()
        if texto.strip():
            l.texto(texto, x0, arriba + k * alto_c, cols * ancho_c, alto_c, alto_c, color, "mono", 0.0, 0.5)
    _cifras_arriba(l, pal, w, h, medidas)


AMBAR = (1.0, 0.72, 0.32)


def _vumetro(l, pal, w, h, medidas, x=None):
    """Vúmetros de estudio: una o dos cajas iluminadas en ámbar, escala de -20 a +3 con la zona
    roja y una aguja negra (con la inercia de las de verdad)."""
    cajas = medidas[:2]
    hueco = 8
    # Dos cajas: una al lado de la otra si hay ancho; si no, una encima de otra.
    apiladas = len(cajas) > 1 and (w - hueco) / 2 < h * 0.95
    if apiladas:
        ancho, alto_caja = w, (h - hueco) / 2
    else:
        ancho, alto_caja = (w - hueco * (len(cajas) - 1)) / len(cajas), h
    for k, m in enumerate(cajas):
        x0, y0 = (0, k * (alto_caja + hueco)) if apiladas else (k * (ancho + hueco), 0)
        _caja_vu(l, x0, y0, ancho, alto_caja, m)


def _caja_vu(l, x0, y0, ancho, h, m):
    """Una caja de vúmetro: iluminada en ámbar, escala de -20 a +3 y la aguja."""
    l.rect(x0, y0, ancho, h, 8, (0.12, 0.1, 0.08))                     # marco
    l.rect(x0 + 4, y0 + 4, ancho - 8, h - 8, 5, mezcla(AMBAR, (0, 0, 0), 0.08))  # esfera iluminada
    for s in range(5):  # luz más intensa en el centro (viene de detrás)
        l.rect(x0 + 4 + (ancho - 8) * s / 10, y0 + 4 + (h - 8) * s / 10, (ancho - 8) * (1 - s / 5),
               (h - 8) * (1 - s / 5), 5, con_alfa((1.0, 0.92, 0.7), 0.06))
    cx, cy = x0 + ancho / 2, y0 + h * 1.02
    r = min(ancho * 0.48, h * 0.78)
    a0, a1 = math.radians(-140), math.radians(-40)
    tinta = (0.15, 0.1, 0.05)
    l.arco(cx, cy, r * 0.8, a0, a1, 1.2, tinta)
    l.arco(cx, cy, r * 0.8, a0 + (a1 - a0) * 0.72, a1, max(2.0, r * 0.05), (0.75, 0.1, 0.05))  # zona roja
    marcas = ((0, "20"), (0.2, "10"), (0.38, "5"), (0.55, "3"), (0.72, "0"), (0.86, "+2"), (1.0, "+3"))
    px = max(7.0, min(11.0, r * 0.1))
    for pos, rotulo in marcas:
        a = a0 + (a1 - a0) * pos
        l.linea(cx + math.cos(a) * r * 0.8, cy + math.sin(a) * r * 0.8,
                cx + math.cos(a) * r * 0.88, cy + math.sin(a) * r * 0.88, 1.2,
                (0.75, 0.1, 0.05) if pos >= 0.72 else tinta)
        if r > 50:
            l.texto(rotulo, cx + math.cos(a) * r * 0.97 - 12, cy + math.sin(a) * r * 0.97 - 7, 24, 14, px,
                    (0.75, 0.1, 0.05) if pos >= 0.72 else tinta, "normal")
    l.texto("VU", cx - 20, cy - r * 0.45, 40, px * 2, px * 1.6, tinta, "negrita")
    nombre = f"{m['nombre']}  {m['texto']}" if m["texto"] else m["nombre"]
    l.texto(nombre, x0 + 6, y0 + h - px * 2.2, ancho - 12, px * 1.6, px, con_alfa(tinta, 0.8), "normal")
    a = a0 + (a1 - a0) * max(0.0, min(1.05, m["frac"]))
    l.linea(cx, cy, cx + math.cos(a) * r * 0.95, cy + math.sin(a) * r * 0.95, 1.6, (0.05, 0.04, 0.03), True)
    l.circulo(cx, y0 + h - 4, max(4.0, r * 0.06), (0.12, 0.1, 0.08))


# --- túnel, galaxia y esfera de partículas ----------------------------------------------------------

def _azar(i, sal):
    """Pseudoaleatorio fijo (0-1) para la partícula i: siempre el mismo, sin patrones visibles."""
    return (math.sin(i * 12.9898 + sal * 78.233) * 43758.5453) % 1


def _tunel(l, pal, w, h, medidas, x=None):
    """Un túnel sin fin: anillos octogonales que vienen desde el fondo, con el centro que
    serpentea; más deprisa y más calientes de color cuanto más carga."""
    x = x or {}
    t = x.get("t", 0.0)
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    viaje = x.get("fase", 0.0) * 2.2
    l.rect(0, 0, w, h, 8, (0.01, 0.0, 0.03, 0.85))
    base = mezcla(_color(pal, medidas[0]), calor(f), 0.5)
    lados = 8
    n = 16
    radio = max(w, h) * 0.75
    anillos = []
    for k in range(n):
        z = 1 - ((k / n + viaje) % 1)  # 1 al fondo, 0 encima
        z = max(z, 0.02)
        # El centro se mueve con el tiempo, más cuanto más al fondo (el túnel hace curvas).
        cx = w / 2 + math.sin(t * 0.7 + z * 2.5) * w * 0.12 * z
        cy = h / 2 + math.cos(t * 0.5 + z * 2.0) * h * 0.1 * z
        r = radio * 0.08 / z
        giro = z * 1.2 + t * 0.15
        anillos.append((z, cx, cy, r, giro))
    anillos.sort(reverse=True)  # del fondo hacia delante
    s2 = _segunda(medidas, x)
    for k_anillo, (z, cx, cy, r, giro) in enumerate(anillos):
        if r > max(w, h) * 2:
            continue
        niebla = max(0.0, min(1.0, (1 - z) * 1.3))
        if s2 and k_anillo % 2:  # uno de cada dos anillos, de la segunda medida
            c2 = _color(pal, s2[1])
            pts = [(cx + math.cos(giro + 2 * math.pi * k / lados) * r * 0.97,
                    cy + math.sin(giro + 2 * math.pi * k / lados) * r * 0.97) for k in range(lados + 1)]
            for p0, p1 in zip(pts, pts[1:]):
                l.linea(*p0, *p1, 0.6 + 2.5 * (1 - z), con_alfa(c2, niebla * (0.25 + 0.75 * s2[0])), True)
            continue
        pts = [(cx + math.cos(giro + 2 * math.pi * k / lados) * r, cy + math.sin(giro + 2 * math.pi * k / lados) * r)
               for k in range(lados + 1)]
        for p0, p1 in zip(pts, pts[1:]):
            l.linea(*p0, *p1, 0.6 + 2.5 * (1 - z), con_alfa(base, niebla), True)
    # Las aristas del túnel: del anillo más lejano al más cercano.
    lejos, cerca = anillos[0], anillos[-1]
    for k in range(lados):
        a0 = lejos[4] + 2 * math.pi * k / lados
        a1 = cerca[4] + 2 * math.pi * k / lados
        l.linea(lejos[1] + math.cos(a0) * lejos[3], lejos[2] + math.sin(a0) * lejos[3],
                cerca[1] + math.cos(a1) * cerca[3], cerca[2] + math.sin(a1) * cerca[3], 1, con_alfa(base, 0.18))
    _cifras_arriba(l, pal, w, h, medidas)


def _galaxia(l, pal, w, h, medidas, x=None):
    """Galaxia espiral vista un poco de lado: estrellas en dos brazos que giran (las de dentro,
    más deprisa); con más carga los brazos brillan más y el núcleo se enciende."""
    x = x or {}
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    giro = x.get("fase", 0.0) * 2 * math.pi * 0.6
    l.rect(0, 0, w, h, 8, (0.0, 0.0, 0.02, 0.85))
    cx, cy = w / 2, h / 2
    rx = w * 0.46
    inclinacion = min(0.6, h / w * 1.1)
    color = _color(pal, medidas[0])
    for k in range(10, 0, -1):  # el resplandor del núcleo (muchas capas finas: sin escalones)
        l.circulo(cx, cy, rx * 0.016 * k * (0.7 + 0.6 * f), con_alfa(mezcla(color, (1, 0.95, 0.8), 0.6), 0.03 + 0.04 * f))
    for i in range(420):
        brazo = i % 2
        r = _azar(i, 1) ** 0.7  # más estrellas hacia dentro
        abertura = 3.2  # vueltas de la espiral
        a = brazo * math.pi + r * abertura + (_azar(i, 2) - 0.5) * (0.5 + 0.6 * r) + giro / (0.35 + r)
        sx = cx + math.cos(a) * r * rx
        sy = cy + math.sin(a) * r * rx * inclinacion
        fb, cb = f, color
        if brazo == 1 and len(medidas) > 1:  # el segundo brazo: la segunda medida
            fb, cb = max(0.0, min(1.0, medidas[1]["frac"])), _color(pal, medidas[1])
        brillo = (0.25 + 0.75 * fb) * (1 - r * 0.6) * (0.5 + 0.5 * _azar(i, 3))
        c = mezcla(cb, (1, 1, 1), 0.5 * (1 - r))
        l.circulo(sx, sy, 0.6 + 1.1 * _azar(i, 4) * (1 - r * 0.5), con_alfa(c, min(1.0, brillo + 0.15)))
    _cifras_arriba(l, pal, w, h, medidas)


def _esfera(l, pal, w, h, medidas, x=None):
    """Un globo de partículas (repartidas con la espiral de Fibonacci) que gira y late con cada
    lectura; más grande y más rápido cuanto más carga. Las de detrás, más pequeñas y apagadas."""
    x = x or {}
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    giro = x.get("fase", 0.0) * 2 * math.pi
    latido = math.exp(-x.get("desde", 1.0) * 5) * 0.08 if x.get("latido", True) else 0.0  # al llegar cada lectura
    arriba = max(14.0, min(30.0, h * 0.22)) + 4
    cx, cy = w / 2, arriba + (h - arriba) / 2
    r = min(w, h - arriba) * (0.32 + 0.12 * f) * (1 + latido)
    color = mezcla(_color(pal, medidas[0]), calor(f), 0.35)
    inc = 0.45
    ci, si, cg, sg = math.cos(inc), math.sin(inc), math.cos(giro), math.sin(giro)
    puntos = []
    n = 260
    oro = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        y = 1 - 2 * (i + 0.5) / n
        rad = math.sqrt(1 - y * y)
        px_, pz = math.cos(oro * i) * rad, math.sin(oro * i) * rad
        px_, pz = px_ * cg + pz * sg, -px_ * sg + pz * cg      # giro sobre el eje vertical
        py, pz = y * ci - pz * si, y * si + pz * ci             # inclinada hacia delante
        puntos.append((pz, px_, py))
    capas = [(pz, px_, py, r, color) for pz, px_, py in puntos]
    s2 = _segunda(medidas, x)
    if s2:  # dentro, otra esfera: la segunda medida (su tamaño y su color)
        r2 = r * (0.2 + 0.5 * s2[0])
        for pz, px_, py in puntos[::3]:
            capas.append((pz * r2 / r, -px_, py, r2, _color(pal, s2[1])))
    for pz, px_, py, rr, c in sorted(capas, key=lambda q: q[0]):  # de atrás adelante
        cerca = (pz + 1) / 2
        l.circulo(cx + px_ * rr, cy + py * rr, 0.6 + 1.8 * cerca * rr / r, con_alfa(c, 0.2 + 0.8 * cerca))
    _cifras_arriba(l, pal, w, h, medidas)


# --- espacio: planeta con anillos y agujero negro ---------------------------------------------------

def _elipse(l, cx, cy, rx, ry, a0, a1, grosor, color, pasos=48):
    """Arco de elipse (de a0 a a1) a base de líneas."""
    pts = [(cx + math.cos(a0 + (a1 - a0) * k / pasos) * rx, cy + math.sin(a0 + (a1 - a0) * k / pasos) * ry)
           for k in range(pasos + 1)]
    for p0, p1 in zip(pts, pts[1:]):
        l.linea(*p0, *p1, grosor, color, True)


def _planeta(l, pal, w, h, medidas, x=None):
    """Un planeta con bandas que giran y anillos: uno por medida, lleno hasta su valor. La mitad
    de atrás de los anillos pasa por detrás del planeta."""
    x = x or {}
    fase = x.get("fase", 0.0)
    principal = medidas[0]
    color = _color(pal, principal)
    arriba = max(14.0, min(30.0, h * 0.22)) + 2
    cx, cy = w / 2, arriba + (h - arriba) / 2
    r = min(w * 0.22, (h - arriba) * 0.36)
    if r < 8:
        return
    anillos = medidas[:3]

    def anillo(i, m, delante):
        rx, ry = r * (1.45 + i * 0.28), r * (1.45 + i * 0.28) * 0.28
        a0, a1 = (0, math.pi) if delante else (math.pi, 2 * math.pi)
        _elipse(l, cx, cy, rx, ry, a0, a1, max(2.0, r * 0.12), con_alfa(_color(pal, m), 0.15))
        f = max(0.0, min(1.0, m["frac"]))
        # Lo lleno empieza a la izquierda y da la vuelta por detrás: se corta en su mitad.
        fin = math.pi + 2 * math.pi * f
        if not delante and f > 0:
            _elipse(l, cx, cy, rx, ry, math.pi, min(fin, 2 * math.pi), max(2.0, r * 0.12), _color(pal, m), 24)
        if delante and fin > 2 * math.pi:
            _elipse(l, cx, cy, rx, ry, 0, fin - 2 * math.pi, max(2.0, r * 0.12), _color(pal, m), 24)
    for i, m in enumerate(anillos):
        anillo(i, m, False)
    # El planeta: sombreado de luz arriba a la izquierda, con bandas que se desplazan.
    for k in range(8, 0, -1):
        l.circulo(cx - r * 0.25 * (1 - k / 8), cy - r * 0.25 * (1 - k / 8), r * k / 8,
                  mezcla(mezcla(color, (0, 0, 0), 0.55), mezcla(color, (1, 1, 1), 0.25), 1 - k / 8))
    for b in range(5):
        y = cy - r + (b + 0.5) * 2 * r / 5
        semi = math.sqrt(max(0.0, r * r - (y - cy) ** 2))
        desplaza = math.sin(fase * 2 * math.pi + b * 1.3) * semi * 0.25
        l.linea(cx - semi * 0.9 + desplaza, y, cx + semi * 0.6 + desplaza, y, max(1.0, r * 0.06),
                con_alfa((1, 1, 1), 0.08))
    for i, m in enumerate(anillos):
        anillo(i, m, True)
    _cifras_arriba(l, pal, w, h, medidas)


def _agujero(l, pal, w, h, medidas, x=None):
    """Agujero negro: disco de acreción inclinado que gira (más brillante con la carga), el anillo
    de fotones y la parte de atrás del disco curvada por encima (la lente gravitatoria)."""
    x = x or {}
    fase = x.get("fase", 0.0)
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    arriba = max(14.0, min(30.0, h * 0.22)) + 2
    cx, cy = w / 2, arriba + (h - arriba) / 2
    r = min(w * 0.13, (h - arriba) * 0.24)
    if r < 6:
        return
    l.rect(0, 0, w, h, 8, (0.0, 0.0, 0.0, 0.85))
    caliente = mezcla((1.0, 0.55, 0.15), (1.0, 0.95, 0.8), f)
    brillo = 0.35 + 0.65 * f
    # Detrás: el disco de atrás, curvado por encima del agujero.
    for k in range(6):
        rr = r * (1.25 + k * 0.22)
        _elipse(l, cx, cy, rr, rr * 0.95, math.pi, 2 * math.pi, max(1.0, r * 0.08),
                con_alfa(caliente, brillo * (0.5 - k * 0.07)), 36)
    # El disco (las dos mitades) con grumos que giran.
    for k in range(8):
        rr = r * (1.3 + k * 0.28)
        _elipse(l, cx, cy, rr, rr * 0.22, 0, 2 * math.pi, max(1.0, r * 0.1),
                con_alfa(mezcla(caliente, (0.8, 0.2, 0.05), k / 8), brillo * (0.55 - k * 0.05)), 48)
    for i in range(40):
        rr = r * (1.3 + _azar(i, 1) * 2.0)
        a = fase * 2 * math.pi * (2.2 / (rr / r)) + _azar(i, 2) * 2 * math.pi
        l.circulo(cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.22, 1.2, con_alfa((1, 0.9, 0.7), brillo * 0.8))
    s2 = _segunda(medidas, x)
    if s2 and s2[0] > 0.02:  # chorros polares: la segunda medida
        c2 = mezcla(_color(pal, s2[1]), (0.8, 0.9, 1.0), 0.4)
        largo = (h - arriba) * 0.5 * s2[0]
        for sentido in (-1, 1):
            for k in range(5):
                l.linea(cx, cy + sentido * r * 0.9, cx, cy + sentido * (r + largo * (1 - k * 0.15)),
                        max(1.0, r * 0.25 * (1 - k / 5)), con_alfa(c2, 0.12 + 0.1 * k), True)
    l.circulo(cx, cy, r * 1.08, con_alfa(caliente, 0.6 * brillo))  # anillo de fotones
    l.circulo(cx, cy, r, (0, 0, 0))
    # Delante: la parte del disco que pasa por delante del agujero.
    for k in range(4):
        rr = r * (1.3 + k * 0.28)
        _elipse(l, cx, cy, rr, rr * 0.22, 0, math.pi, max(1.0, r * 0.1),
                con_alfa(mezcla(caliente, (0.8, 0.2, 0.05), k / 8), brillo * (0.7 - k * 0.1)), 24)
    _cifras_arriba(l, pal, w, h, medidas)


# --- retro: tablero de aeropuerto, terminal, LEDs y luces de F1 ---------------------------------------

def _paletas(l, pal, w, h, medidas, x=None):
    """Tablero de aeropuerto: cada carácter en su paleta partida por la mitad; cuando la cifra va a
    cambiar, la mitad de arriba de la última cifra cae doblándose (según lo que falta para el
    siguiente número)."""
    principal, resto = medidas[0], medidas[1:3]
    texto = principal["texto"] or "—"
    alto_ley = 18 if resto else 0
    n = max(4, len(texto))
    hueco = 3
    ancho_c = min((w - 8 - hueco * (n - 1)) / n, (h - alto_ley - 8) * 0.68)
    alto_c = ancho_c / 0.68
    x0 = (w - n * ancho_c - (n - 1) * hueco) / 2
    y0 = (h - alto_ley - alto_c) / 2
    texto = texto.rjust(n)
    valor = principal.get("valor") or 0.0
    progreso = (valor % 1) if principal["texto"] and principal["texto"][0].isdigit() else 0.0
    ultimo = max((i for i, c in enumerate(texto) if c.isdigit()), default=-1)
    px = alto_c * 0.72
    for i, c in enumerate(texto):
        xx = x0 + i * (ancho_c + hueco)
        l.rect(xx, y0, ancho_c, alto_c, 3, (0.1, 0.1, 0.11))
        l.rect(xx, y0, ancho_c, alto_c / 2, 3, (0.14, 0.14, 0.15))
        l.texto(c, xx, y0, ancho_c, alto_c, px, (0.95, 0.93, 0.85), "negrita")
        if i == ultimo and progreso > 0.05:
            # La paleta de arriba cayendo: se aplasta hacia la bisagra.
            alto_p = alto_c / 2 * abs(math.cos(progreso * math.pi))
            arriba = progreso < 0.5
            yy = y0 + alto_c / 2 - alto_p if arriba else y0 + alto_c / 2
            l.rect(xx, yy, ancho_c, alto_p, 2, (0.17, 0.17, 0.18) if arriba else (0.08, 0.08, 0.09))
        l.rect(xx, y0 + alto_c / 2 - 0.7, ancho_c, 1.4, 0, (0, 0, 0))  # la raja
        for lado in (xx + 1, xx + ancho_c - 3):  # bisagras
            l.rect(lado, y0 + alto_c / 2 - 2.5, 2, 5, 1, (0.4, 0.4, 0.42))
    # Las demás medidas: su nombre y su cifra en paletas pequeñas.
    y = h - alto_ley + 1
    ancho_m = w / max(1, len(resto))
    for k, m in enumerate(resto):
        txt = (m["texto"] or "—")
        n2 = len(txt)
        ac = min(11.0, (ancho_m - 40) / max(1, n2) - 1)
        xx = k * ancho_m + 4
        l.texto(m["nombre"].upper(), xx, y, 36, alto_ley - 2, 8, _color(pal, m), "negrita", 0.0, 0.5)
        for i, c in enumerate(txt):
            px_ = xx + 38 + i * (ac + 1)
            l.rect(px_, y, ac, alto_ley - 2, 2, (0.1, 0.1, 0.11))
            l.texto(c, px_, y, ac, alto_ley - 2, (alto_ley - 2) * 0.7, (0.95, 0.93, 0.85), "negrita")
            l.rect(px_, y + (alto_ley - 2) / 2 - 0.5, ac, 1, 0, (0, 0, 0))


AMBAR_FOSFORO = (1.0, 0.68, 0.18)
BLOQUES = "▁▂▃▄▅▆▇█"


def _terminal(l, pal, w, h, medidas, x=None):
    """Una terminal de fósforo ámbar: una línea por medida con su barra de bloques, el historial
    de la principal en mini barras y el cursor parpadeando; con líneas de barrido."""
    x = x or {}
    t = x.get("t", 0.0)
    serie = x.get("serie") or []
    l.rect(0, 0, w, h, 8, (0.06, 0.03, 0.0, 0.88))
    lineas = len(medidas[:3]) + 3
    alto_l = min(18.0, (h - 8) / lineas)
    px = alto_l * 0.8
    ancho_c = l.medir("█", px, "mono")[0] or px * 0.6
    cols = max(10, int((w - 12) / ancho_c) - 1)
    y = 4
    l.texto("> monitor", 6, y, w - 12, alto_l, px, con_alfa(AMBAR_FOSFORO, 0.6), "mono", 0.0, 0.5)
    y += alto_l
    for m in medidas[:3]:
        etiqueta = m["nombre"][:6].upper().ljust(6)
        cifra = (m["texto"] or "").rjust(10)
        barra_n = max(4, cols - len(etiqueta) - len(cifra) - 4)
        lleno = int(round(max(0.0, min(1.0, m["frac"])) * barra_n))
        texto = f"{etiqueta} [{'█' * lleno}{'░' * (barra_n - lleno)}]{cifra}"
        l.texto(texto, 6, y, w - 12, alto_l, px, AMBAR_FOSFORO, "mono", 0.0, 0.5)
        y += alto_l
    valores = [v[0] for v in serie[-cols:]] if serie else []
    hist = "".join(BLOQUES[min(7, int(max(0.0, min(1.0, v)) * 8))] for v in valores)
    l.texto(hist, 6, y, w - 12, alto_l, px, con_alfa(AMBAR_FOSFORO, 0.85), "mono", 0.0, 0.5)
    y += alto_l
    if (t * 1.6) % 1 < 0.55:  # el cursor
        l.rect(6, y + alto_l * 0.15, ancho_c, alto_l * 0.75, 0, AMBAR_FOSFORO)
    for k in range(0, int(h), 3):  # líneas de barrido
        l.rect(0, k, w, 1, 0, (0, 0, 0, 0.18))


# Letras de 5x7 para la matriz de LEDs (cada fila, 5 bits de izquierda a derecha).
LETRAS_LED = {
    "0": (14, 17, 19, 21, 25, 17, 14), "1": (4, 12, 4, 4, 4, 4, 14), "2": (14, 17, 1, 2, 4, 8, 31),
    "3": (31, 2, 4, 2, 1, 17, 14), "4": (2, 6, 10, 18, 31, 2, 2), "5": (31, 16, 30, 1, 1, 17, 14),
    "6": (6, 8, 16, 30, 17, 17, 14), "7": (31, 1, 2, 4, 8, 8, 8), "8": (14, 17, 17, 14, 17, 17, 14),
    "9": (14, 17, 17, 15, 1, 2, 12), "%": (24, 25, 2, 4, 8, 19, 3), ".": (0, 0, 0, 0, 0, 12, 12),
    "°": (12, 18, 18, 12, 0, 0, 0), "C": (14, 17, 16, 16, 16, 17, 14), "B": (30, 17, 17, 30, 17, 17, 30),
    "K": (17, 18, 20, 24, 20, 18, 17), "M": (17, 27, 21, 21, 17, 17, 17), "G": (14, 17, 16, 23, 17, 17, 15),
    "i": (4, 0, 12, 4, 4, 4, 14), "/": (0, 1, 2, 4, 8, 16, 0), "s": (0, 0, 14, 16, 14, 1, 30),
    "-": (0, 0, 0, 14, 0, 0, 0), "—": (0, 0, 0, 31, 0, 0, 0), " ": (0,) * 7,
}


def _leds(l, pal, w, h, medidas, x=None):
    """Pantalla de matriz de LEDs: la cifra con letras de 5x7 puntos y, debajo, el historial de
    la medida principal en columnas de puntos. Los LEDs apagados se ven tenues."""
    x = x or {}
    serie = x.get("serie") or []
    principal = medidas[0]
    color = mezcla(_color(pal, principal), (1, 1, 1), 0.15)
    apagado = con_alfa(color, 0.07)
    texto = principal["texto"] or ""
    filas = 16  # 7 de letras + 1 de hueco + 8 de gráfica
    paso = min((h - 6) / filas, (w - 6) / max(20, len(texto) * 6))
    cols = int((w - 6) / paso)
    radio = paso * 0.36
    x0 = (w - cols * paso) / 2 + paso / 2
    y0 = (h - filas * paso) / 2 + paso / 2
    encendidos = set()
    ancho_txt = len(texto) * 6 - 1
    inicio = max(0, (cols - ancho_txt) // 2)
    for i, c in enumerate(texto):
        mapa = LETRAS_LED.get(c, LETRAS_LED.get(c.upper(), LETRAS_LED[" "]))
        for fila, bits in enumerate(mapa):
            for b in range(5):
                if bits & (16 >> b):
                    encendidos.add((inicio + i * 6 + b, fila))
    valores = [v[0] for v in serie[-cols:]]
    for k, v in enumerate(valores):
        col = cols - len(valores) + k
        for fila in range(int(round(max(0.0, min(1.0, v)) * 8))):
            encendidos.add((col, 15 - fila))
    segunda = {}  # la segunda medida: un punto de su color por columna, a su altura
    if len(medidas) > 1:
        valores2 = [v[1] for v in serie[-cols:] if len(v) > 1]
        for k, v in enumerate(valores2):
            segunda[(cols - len(valores2) + k, 15 - min(7, int(max(0.0, min(1.0, v)) * 8)))] = True
    for fila in range(filas):
        if fila == 7:
            continue
        for col in range(cols):
            if (col, fila) in segunda:
                l.circulo(x0 + col * paso, y0 + fila * paso, radio, mezcla(_color(pal, medidas[1]), (1, 1, 1), 0.2))
                continue
            encendido = (col, fila) in encendidos
            l.circulo(x0 + col * paso, y0 + fila * paso, radio, color if encendido else apagado)


def _f1(l, pal, w, h, medidas, x=None):
    """Luces de cambio de marcha de un volante de F1: 15 LEDs (verde, rojo, azul) que se encienden
    con la carga; pasado el 95 % parpadean todos. La cifra grande debajo."""
    x = x or {}
    t = x.get("t", 0.0)
    principal, resto = medidas[0], medidas[1:3]
    f = max(0.0, min(1.0, principal["frac"]))
    n = 15
    colores = [(0.2, 0.95, 0.35)] * 5 + [(1.0, 0.18, 0.15)] * 5 + [(0.25, 0.5, 1.0)] * 5
    paso = (w - 16) / n
    r = min(paso * 0.38, h * 0.12)
    y = r + 6
    l.rect(4, 2, w - 8, 2 * r + 8, r + 4, (0.03, 0.03, 0.04, 0.85))
    parpadeo = f > 0.95 and (t * 6) % 1 < 0.5
    for i in range(n):
        cx = 8 + paso * (i + 0.5)
        encendido = (i + 0.5) / n <= f and not parpadeo
        c = colores[i]
        if encendido:
            l.circulo(cx, y, r * 1.6, con_alfa(c, 0.18))
        l.circulo(cx, y, r, c if encendido else con_alfa(c, 0.12))
    abajo = y + r + 8
    if resto:  # la segunda medida: una tira fina de LEDs de su color
        f2 = max(0.0, min(1.0, resto[0]["frac"]))
        c2 = _color(pal, resto[0])
        for i in range(n):
            cx = 8 + paso * (i + 0.5)
            l.circulo(cx, abajo + 2, r * 0.4, c2 if (i + 0.5) / n <= f2 else con_alfa(c2, 0.12))
        abajo += r * 0.8 + 6
    alto_ley = 16 if resto else 0
    if principal["texto"]:
        _cifra(l, pal, 0, abajo, w, h - abajo - alto_ley, principal["texto"], pal["texto"], "negrita")
    if resto:
        _leyenda(l, pal, 0, h - alto_ley, w, alto_ley, resto)


# --- naturaleza y física ------------------------------------------------------------------------

def _arena(l, pal, w, h, medidas, x=None):
    """Reloj de arena: abajo se acumula la medida principal (arriba queda el resto), y el chorro
    cae más deprisa cuanto más carga."""
    x = x or {}
    principal, resto = medidas[0], medidas[1:3]
    f = max(0.0, min(1.0, principal["frac"]))
    ancho = min(w, h * 0.55)
    cx = ancho / 2
    arriba, abajo, medio = 8, h - 8, h / 2
    semi = ancho * 0.42
    cuello = max(2.0, ancho * 0.04)
    arena = mezcla(_color(pal, principal), (0.95, 0.8, 0.5), 0.5)
    vidrio = con_alfa(pal["texto"], 0.25)

    def semi_en(y):  # media anchura del cristal a la altura y (dos conos)
        d = abs(y - medio) / (medio - arriba)
        return cuello + (semi - cuello) * d ** 0.8
    # Arena de abajo: un montón hasta la altura que marca f.
    alto_abajo = (abajo - medio) * f
    if alto_abajo > 1:
        pts = []
        for k in range(21):
            y = abajo - alto_abajo * k / 20
            pts.append((cx - semi_en(y), y))
        cima = abajo - alto_abajo
        pts.append((cx, cima - min(alto_abajo * 0.3, 10)))
        for k in range(20, -1, -1):
            y = abajo - alto_abajo * k / 20
            pts.append((cx + semi_en(y), y))
        l.poligono(pts, arena)
    # Arena de arriba: lo que falta, pegado al cuello.
    alto_arriba = (medio - arriba) * (1 - f)
    if alto_arriba > 1:
        pts = []
        y_sup = medio - alto_arriba
        for k in range(21):
            y = y_sup + (medio - y_sup) * k / 20
            pts.append((cx - semi_en(y), y))
        for k in range(20, -1, -1):
            y = y_sup + (medio - y_sup) * k / 20
            pts.append((cx + semi_en(y), y))
        l.poligono(pts, con_alfa(arena, 0.85))
    # El chorro: granos que caen (más deprisa con la carga).
    if 0.01 < f < 0.99:
        cae = x.get("burbujas", 0.0) * 3
        for i in range(10):
            avance = (cae + i / 10) % 1
            y = medio + avance * (abajo - alto_abajo - medio)
            l.circulo(cx + math.sin(i * 7.1) * 0.8, y, 1.1, arena)
    # El cristal y los marcos de madera.
    for lado in (-1, 1):
        pts = [(cx + lado * semi_en(arriba + (abajo - arriba) * k / 30), arriba + (abajo - arriba) * k / 30)
               for k in range(31)]
        for p0, p1 in zip(pts, pts[1:]):
            l.linea(*p0, *p1, 1.5, vidrio)
    madera = (0.45, 0.28, 0.14)
    if resto:  # la segunda medida: el palo derecho del marco se llena de su color
        f2 = max(0.0, min(1.0, resto[0]["frac"]))
        xp = cx + semi + 2
        l.rect(xp, arriba, 4, abajo - arriba, 2, con_alfa(madera, 0.6))
        l.rect(xp, abajo - (abajo - arriba) * f2, 4, (abajo - arriba) * f2, 2, _color(pal, resto[0]))
    l.rect(cx - semi - 4, arriba - 6, 2 * semi + 8, 6, 2, madera)
    l.rect(cx - semi - 4, abajo, 2 * semi + 8, 6, 2, madera)
    tx = ancho + 10
    if w - tx > 50:
        if principal["texto"]:
            _cifra(l, pal, tx, h * 0.2, w - tx, h * 0.32, principal["texto"], pal["texto"])
        px = max(8.0, min(12.0, h * 0.1))
        y = h * 0.58
        for m in resto:
            l.circulo(tx + px * 0.3, y + px * 0.7, px * 0.28, _color(pal, m))
            l.texto(f"{m['nombre']} {m['texto']}", tx + px, y, w - tx - px, px * 1.4, px, pal["gris"], "normal",
                    0.0, 0.5)
            y += px * 1.6


def _tormenta(l, pal, w, h, medidas, x=None):
    """Tormenta: la lluvia es más densa y cae más inclinada cuanto más carga; pasado el 80 % caen
    rayos (con su fogonazo)."""
    x = x or {}
    t = x.get("t", 0.0)
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    l.rect(0, 0, w, h, 8, (0.03, 0.04, 0.07, 0.85))
    # El rayo: cada medio segundo se decide (por azar fijo) si cae uno.
    ventana = int(t * 2)
    rayo = f > 0.8 and _azar(ventana, 9) < (f - 0.8) * 4
    dentro = (t * 2) % 1
    if rayo and dentro < 0.25:
        l.rect(0, 0, w, h, 8, con_alfa((0.8, 0.85, 1.0), 0.25 * (1 - dentro * 4)))
        xx, yy = w * (0.2 + 0.6 * _azar(ventana, 3)), 0.0
        while yy < h * 0.9:
            nx = xx + (_azar(int(yy) + ventana, 5) - 0.5) * w * 0.12
            ny = yy + h * 0.1
            l.linea(xx, yy, nx, ny, 2.2, con_alfa((0.9, 0.92, 1.0), 1 - dentro * 3), True)
            xx, yy = nx, ny
    s2 = _segunda(medidas, x)
    viento = 0.1 + 0.5 * (s2[0] if s2 else f)  # el viento: la segunda medida (si la hay)
    gotas = int(20 + 90 * f)
    cae = x.get("burbujas", 0.0) * 5
    for i in range(gotas):
        avance = (cae * (0.8 + _azar(i, 1) * 0.4) + _azar(i, 2)) % 1
        y = avance * (h + 20) - 10
        x0 = (_azar(i, 3) * (w + h * viento)) - y * viento
        largo = 6 + 8 * f
        l.linea(x0, y, x0 - largo * viento, y - largo, 1, con_alfa((0.65, 0.75, 1.0), 0.55))
    _cifras_arriba(l, pal, w, h, medidas)


def _plasma(l, pal, w, h, medidas, x=None):
    """Bola de plasma: rayos que serpentean desde el centro hasta el cristal; más rayos, más
    largos y más brillantes cuanto más carga."""
    x = x or {}
    t = x.get("t", 0.0)
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    arriba = max(14.0, min(30.0, h * 0.22)) + 2
    cx, cy = w / 2, arriba + (h - arriba) / 2
    r = min(w / 2, (h - arriba) / 2) - 3
    if r < 10:
        return
    color = mezcla(_color(pal, medidas[0]), (0.85, 0.4, 1.0), 0.4)
    l.circulo(cx, cy, r, (0.02, 0.0, 0.05, 0.8))
    for k in range(6):
        l.circulo(cx, cy, r * 0.12 * (6 - k) / 3, con_alfa(color, 0.07))
    for i in range(int(3 + 7 * f)):
        a = _azar(i, 1) * 2 * math.pi + math.sin(t * (0.3 + _azar(i, 2) * 0.5) + i) * 0.8
        largo = r * (0.55 + 0.45 * f)
        px_, py = cx, cy
        pasos = 10
        for k in range(1, pasos + 1):
            d = largo * k / pasos
            ondula = math.sin(t * 9 + k * 1.7 + i * 3) * r * 0.05 * k / pasos
            nx = cx + math.cos(a) * d - math.sin(a) * ondula
            ny = cy + math.sin(a) * d + math.cos(a) * ondula
            l.linea(px_, py, nx, ny, 3.5 * (1 - k / pasos) + 0.6, con_alfa(color, 0.25), True)
            l.linea(px_, py, nx, ny, 1.4 * (1 - k / pasos) + 0.4, con_alfa((1, 0.9, 1), 0.85), True)
            px_, py = nx, ny
        l.circulo(px_, py, 2.5, con_alfa(color, 0.6))
    s2 = _segunda(medidas, x)
    if s2:  # el núcleo: la segunda medida
        for k in range(5, 0, -1):
            l.circulo(cx, cy, r * (0.08 + 0.2 * s2[0]) * k / 3, con_alfa(_color(pal, s2[1]), 0.08))
    l.circulo(cx, cy, r * 0.12, mezcla(color, (1, 1, 1), 0.5))
    l.arco(cx, cy, r, 0, 2 * math.pi, 1.5, con_alfa((1, 1, 1), 0.25))
    l.arco(cx, cy, r * 0.85, math.radians(200), math.radians(245), 2, con_alfa((1, 1, 1), 0.2), True)
    _cifras_arriba(l, pal, w, h, medidas)


def _vida(l, pal, w, h, medidas, x=None):
    """El juego de la vida de Conway: a cada paso nacen y mueren casillas por sus vecinas; la carga
    siembra vida nueva (más cuanto más alta) para que nunca se apague."""
    x = x or {}
    estado = x.get("estado", {})
    t = x.get("t", 0.0)
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    arriba = max(14.0, min(30.0, h * 0.22)) + 4
    lado = 6.0
    cols, filas = max(4, int(w / lado)), max(4, int((h - arriba) / lado))
    rejilla = estado.get("rejilla")
    if not rejilla or len(rejilla) != filas or len(rejilla[0]) != cols:
        rejilla = [[1 if _azar(i * 131 + j, 7) < 0.25 else 0 for j in range(cols)] for i in range(filas)]
        estado["rejilla"], estado["paso"] = rejilla, t
    s2 = _segunda(medidas, x)
    intervalo = 0.35 - 0.27 * s2[0] if s2 else 0.18  # el ritmo: la segunda medida (si la hay)
    if t - estado.get("paso", 0.0) > intervalo:
        estado["paso"] = t
        nueva = [[0] * cols for _ in range(filas)]
        for i in range(filas):
            for j in range(cols):
                vecinas = sum(rejilla[(i + di) % filas][(j + dj) % cols]
                              for di in (-1, 0, 1) for dj in (-1, 0, 1) if di or dj)
                nueva[i][j] = 1 if vecinas == 3 or (rejilla[i][j] and vecinas == 2) else 0
        for k in range(int(f * cols * filas * 0.02)):  # la carga siembra
            semilla = int(t * 100) + k
            nueva[int(_azar(semilla, 1) * filas)][int(_azar(semilla, 2) * cols)] = 1
        rejilla = estado["rejilla"] = nueva
    color = mezcla(_color(pal, medidas[0]), calor(f), 0.4)
    x0 = (w - cols * lado) / 2
    for i, fila in enumerate(rejilla):
        for j, viva in enumerate(fila):
            if viva:
                l.rect(x0 + j * lado + 0.5, arriba + i * lado + 0.5, lado - 1, lado - 1, 1, color)
    _cifras_arriba(l, pal, w, h, medidas)


def _arbol(l, pal, w, h, medidas, x=None):
    """Un árbol fractal que se mece: más carga, más viento (y hojas de colores más calientes)."""
    x = x or {}
    t = x.get("t", 0.0)
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    arriba = max(14.0, min(30.0, h * 0.22)) + 2
    viento = 0.05 + 0.25 * f
    tronco = (0.42, 0.3, 0.2)
    hoja = mezcla((0.35, 0.85, 0.4), calor(f), f * 0.8)
    s2 = _segunda(medidas, x)
    tam_hoja = 1.2 + 2.6 * s2[0] if s2 else 2.2  # las hojas, más grandes con la segunda medida
    if s2:
        hoja = mezcla(hoja, _color(pal, s2[1]), 0.35)

    def rama(x0, y0, largo, angulo, nivel):
        mece = math.sin(t * (1.2 + nivel * 0.3) + nivel) * viento * (1 + nivel * 0.4)
        a = angulo + mece * 0.3
        x1, y1 = x0 + math.cos(a) * largo, y0 + math.sin(a) * largo
        l.linea(x0, y0, x1, y1, max(0.8, 6 - nivel * 0.9), mezcla(tronco, hoja, nivel / 8), True)
        if nivel >= 7:
            l.circulo(x1, y1, tam_hoja, con_alfa(hoja, 0.85))
            return
        abre = 0.42 + 0.08 * math.sin(t * 0.7)
        rama(x1, y1, largo * 0.74, a - abre, nivel + 1)
        rama(x1, y1, largo * 0.74, a + abre, nivel + 1)
    rama(w / 2, h - 2, (h - arriba) * 0.27, -math.pi / 2, 0)
    _cifras_arriba(l, pal, w, h, medidas)


def _newton(l, pal, w, h, medidas, x=None):
    """Péndulo de Newton: cinco bolas colgando; la de un extremo cae, golpea y sale la del otro.
    Más carga, más amplitud y más ritmo."""
    x = x or {}
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    s2 = _segunda(medidas, x)
    fase = (s2[2] if s2 else x.get("fase", 0.0)) * 2.5  # el ritmo: la segunda medida (si la hay)
    arriba = max(14.0, min(30.0, h * 0.22)) + 4
    largo = (h - arriba) * 0.62
    r = min(w / 14, (h - arriba) * 0.13)
    cx = w / 2
    techo = arriba + 4
    l.rect(cx - 6 * r, techo - 3, 12 * r, 4, 2, con_alfa(pal["texto"], 0.4))
    amp = 0.2 + 0.5 * f
    s = math.sin(fase * 2 * math.pi)
    color = _color(pal, medidas[0])
    for i in range(5):
        x_colgado = cx + (i - 2) * 2 * r
        a = 0.0
        if i == 0 and s < 0:
            a = s * amp
        if i == 4 and s > 0:
            a = s * amp
        bx = x_colgado + math.sin(a) * largo
        by = techo + math.cos(a) * largo
        l.linea(x_colgado - r * 0.6, techo, bx, by, 1, con_alfa(pal["texto"], 0.4))
        l.linea(x_colgado + r * 0.6, techo, bx, by, 1, con_alfa(pal["texto"], 0.4))
        l.circulo(bx, by, r, mezcla(color, (0.75, 0.78, 0.82), 0.6))
        l.circulo(bx - r * 0.3, by - r * 0.3, r * 0.35, con_alfa((1, 1, 1), 0.5))
    _cifras_arriba(l, pal, w, h, medidas)


def _lissajous(l, pal, w, h, medidas, x=None):
    """Curva de Lissajous en un osciloscopio (modo XY): las frecuencias salen de las dos primeras
    medidas, y la figura gira despacio; más carga, más nudos."""
    x = x or {}
    t = x.get("t", 0.0)
    fosforo = (0.35, 1.0, 0.55)
    l.rect(0, 0, w, h, 10, (0.01, 0.06, 0.03, 0.75))
    f0 = max(0.0, min(1.0, medidas[0]["frac"]))
    f1 = max(0.0, min(1.0, medidas[1]["frac"])) if len(medidas) > 1 else 0.5
    a, b = 1 + 3 * f0, 1 + 3 * f1
    delta = x.get("fase", 0.0) * 2 * math.pi * 0.3 + t * 0.1
    cx, cy = w / 2, h / 2
    rx, ry = w / 2 - 10, h / 2 - 10
    pts = [(cx + math.sin(a * u + delta) * rx, cy + math.sin(b * u) * ry)
           for u in (2 * math.pi * k / 300 for k in range(301))]
    for p0, p1 in zip(pts, pts[1:]):
        l.linea(*p0, *p1, 4, con_alfa(fosforo, 0.08), True)
        l.linea(*p0, *p1, 1.3, con_alfa(fosforo, 0.85), True)
    _cifras_arriba(l, pal, w, h, medidas, fosforo)


def _reactor(l, pal, w, h, medidas, x=None):
    """Reactor de arco: núcleo que brilla con la carga, una corona de bobinas que se encienden por
    turnos y dos anillos que giran; zumba (parpadeo leve) cuando va alto."""
    x = x or {}
    t = x.get("t", 0.0)
    fase = x.get("fase", 0.0)
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    arriba = max(14.0, min(30.0, h * 0.22)) + 2
    cx, cy = w / 2, arriba + (h - arriba) / 2
    r = min(w / 2, (h - arriba) / 2) - 3
    if r < 12:
        return
    azul = mezcla((0.45, 0.85, 1.0), _color(pal, medidas[0]), 0.3)
    zumbido = 1 - (0.15 * f if (t * 23) % 1 < 0.5 else 0)
    l.circulo(cx, cy, r, (0.06, 0.07, 0.09))
    l.arco(cx, cy, r * 0.97, 0, 2 * math.pi, 2, (0.3, 0.32, 0.36))
    for k in range(10):  # bobinas
        a = 2 * math.pi * k / 10 - math.pi / 2
        encendida = (k + 0.5) / 10 <= f
        c = con_alfa(azul, (0.85 if encendida else 0.12) * zumbido)
        l.arco(cx, cy, r * 0.75, a + 0.08, a + 2 * math.pi / 10 - 0.08, r * 0.22, c)
    s2 = _segunda(medidas, x)
    giro, c_anillo = (s2[2], mezcla(azul, _color(pal, s2[1]), 0.6)) if s2 else (fase, azul)
    for k, (radio, vel) in enumerate(((0.52, 1.0), (0.88, -0.6))):
        a = giro * 2 * math.pi * vel
        for s in range(3):
            l.arco(cx, cy, r * radio, a + s * 2.09, a + s * 2.09 + 1.2, 1.5 + (2.0 * s2[0] if s2 else 0),
                   con_alfa(c_anillo, 0.5 * zumbido))
    for k in range(8, 0, -1):
        l.circulo(cx, cy, r * 0.42 * k / 8, con_alfa(mezcla(azul, (1, 1, 1), 1 - k / 8), (0.1 + 0.5 * f) * zumbido))
    l.circulo(cx, cy, r * 0.12, con_alfa((1, 1, 1), 0.6 + 0.4 * f))
    _cifras_arriba(l, pal, w, h, medidas)


CARACTERES_CODIGO = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ0123456789"


def _codigo(l, pal, w, h, medidas, x=None):
    """Lluvia de código: columnas de caracteres que caen con la cabeza brillante y la cola
    apagándose; más columnas y más deprisa cuanto más carga."""
    x = x or {}
    t = x.get("t", 0.0)
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    verde = mezcla((0.3, 1.0, 0.45), _color(pal, medidas[0]), 0.15)
    l.rect(0, 0, w, h, 8, (0.0, 0.02, 0.0, 0.85))
    px = 11.0
    ancho_c = l.medir("ｱ", px, "mono")[0] or px * 0.6
    alto_c = px * 1.15
    cols, filas = max(4, int(w / ancho_c)), max(4, int(h / alto_c) + 1)
    s2 = _segunda(medidas, x)
    cae = (s2[2] * 6 + t * 0.6) if s2 else x.get("burbujas", 0.0) * 9  # la velocidad: la segunda medida
    # Cada nivel de brillo, una línea de texto por fila (con espacios donde no toca): pocas llamadas.
    niveles = {k: [[" "] * cols for _ in range(filas)] for k in range(4)}
    activas = int(cols * (0.35 + 0.65 * f))
    for c in range(cols):
        if _azar(c, 1) > activas / cols:
            continue
        largo = int(5 + _azar(c, 2) * 10)
        cabeza = (cae * (0.6 + _azar(c, 3) * 0.8) + _azar(c, 4) * (filas + largo)) % (filas + largo)
        for k in range(largo):
            fila = int(cabeza) - k
            if 0 <= fila < filas:
                nivel = 0 if k == 0 else 1 if k < 3 else 2 if k < largo * 0.6 else 3
                car = CARACTERES_CODIGO[int(_azar(c * 97 + fila, 5 + int(t * 3) % 7) * len(CARACTERES_CODIGO))]
                niveles[nivel][fila][c] = car
    colores = ((0.85, 1.0, 0.9), verde, con_alfa(verde, 0.6), con_alfa(verde, 0.25))
    for nivel, rejilla in niveles.items():
        for fila, caracteres in enumerate(rejilla):
            texto = "".join(caracteres).rstrip()
            if texto.strip():
                l.texto(texto, 0, fila * alto_c, cols * ancho_c, alto_c, px, colores[nivel], "mono", 0.0, 0.5)
    _cifras_arriba(l, pal, w, h, medidas, tapa=True)


# --- globo con viento (modelo «A Windy Day», ver globo_viento.py) -------------------------------------

def _globo(l, pal, w, h, medidas, x=None):
    """La Tierra en puntos (los continentes) girando, con el viento soplando por encima: sus
    partículas pasan los fotogramas más deprisa cuanto más carga (del color de la principal), y
    los puntos que flotan van de la segunda medida. Lo de la cara de atrás, tenue."""
    import globo_viento
    x = x or {}
    continentes, _colores, fotogramas = globo_viento.cargar()
    f = max(0.0, min(1.0, medidas[0]["frac"]))
    avances = x.get("avances") or [x.get("fase", 0.0)]
    s2 = _segunda(medidas, x)
    arriba = max(14.0, min(30.0, h * 0.22)) + 2
    cx, cy = w / 2, arriba + (h - arriba) / 2
    r = min(w / 2, (h - arriba) / 2) - 3
    if r < 12:
        return
    giro = x.get("t", 0.0) * 0.12 + (s2[2] if s2 else 0.0) * 1.5  # gira; más deprisa con la segunda medida
    cg, sg = math.cos(giro), math.sin(giro)
    inclinacion = 0.4
    ci, si = math.cos(inclinacion), math.sin(inclinacion)

    def proyecta(p):
        px_, pz, py = p  # en el modelo el eje de la Tierra es z: aquí, hacia arriba
        pz = -pz
        px_, pz = px_ * cg + pz * sg, -px_ * sg + pz * cg
        py, pz = py * ci - pz * si, py * si + pz * ci
        return cx + px_ * r, cy - py * r, pz

    l.circulo(cx, cy, r, (0.03, 0.05, 0.09, 0.85))
    l.arco(cx, cy, r, 0, 2 * math.pi, 1.2, con_alfa((0.6, 0.75, 1.0), 0.35))
    for p in continentes:
        sx, sy, z = proyecta(p)
        if z > -0.1:  # la cara de atrás de los continentes, no (se taparía todo)
            l.circulo(sx, sy, 1.15, con_alfa((0.82, 0.85, 0.9), 0.3 + 0.6 * max(0.0, z)))
    # El viento: fotograma a fotograma (no hay continuidad entre ellos en el modelo).
    fot = int(avances[0] * 60) % len(fotogramas)
    color = mezcla(_color(pal, medidas[0]), (1, 1, 1), 0.2)
    for p in fotogramas[fot][0]:
        sx, sy, z = proyecta(p)
        l.circulo(sx, sy, 0.9 + 0.5 * f, con_alfa(color, 0.1 + 0.55 * max(0.0, z + 0.3) * (0.5 + 0.5 * f)))
    # Los puntos que flotan, interpolados entre fotogramas (sí se mueven de uno a otro).
    pos = (avances[1] if len(avances) > 1 else avances[0]) * 20
    a, b = fotogramas[int(pos) % len(fotogramas)][1], fotogramas[(int(pos) + 1) % len(fotogramas)][1]
    k = pos % 1
    c2 = _color(pal, s2[1]) if s2 else mezcla(color, (1, 0.8, 0.4), 0.5)
    for pa, pb in zip(a, b):
        sx, sy, z = proyecta(tuple(u + (v - u) * k for u, v in zip(pa, pb)))
        l.circulo(sx, sy, 1.6, con_alfa(c2, 0.25 + 0.75 * max(0.0, z)))
    _cifras_arriba(l, pal, w, h, medidas)
