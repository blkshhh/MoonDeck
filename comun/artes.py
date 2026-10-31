"""Tipos de arte: cada uno dibuja las tarjetas, barras y gráficas a su manera y tiene sus estilos.

Se dibuja con el lienzo común (LienzoCairo / LienzoQt), así que cada arte se escribe una sola vez.
Un estilo es un tema normal (tema.py) con "arte" en su parte global. Cristal no dibuja nada aquí
(`dibuja = False`): usa el dibujo de siempre de cada sistema, con el desenfoque y el neón.
Relojes, juegos, mascota y letra no dependen del arte: solo toman los colores del estilo.
"""

import tema as temas


def _alfa(color, alfa):
    return (*color[:3], alfa)


def _estilo(arte, acento, texto, sec, fondo, borde, velo, grosor=1):
    """Un estilo de colores planos: sin cristal, degradado ni neón (eso es de Cristal)."""
    tarjeta = dict(fondo=fondo, opacidad=1.0, degradado=False, borde=borde, borde_opacidad=1.0,
                   borde_grosor=grosor, radio=0, cristal=False, neon=False, parpadeo=False)
    return {"global": dict(temas.POR_DEFECTO["global"], arte=arte, acento=acento, texto=texto, texto_sec=sec),
            "widgets": dict(temas.POR_DEFECTO["widgets"], **tarjeta),
            "panel": dict(temas.POR_DEFECTO["panel"], **tarjeta, panel_fondo=velo, panel_opacidad=0.92)}


def _columnas(datos, tope, n):
    """La serie reducida a n puntos: [altura 0-1]."""
    datos = list(datos)
    return [min(datos[round(i * (len(datos) - 1) / max(1, n - 1))] / tope, 1.0) for i in range(n)]


def tramos(largo, frac, celda, hueco):
    """Una barra por bloques: [(posición, largo, lleno)]."""
    n = max(1, (largo + hueco) // (celda + hueco))
    llenos = round(min(max(frac, 0.0), 1.0) * n)
    paso = (largo + hueco) / n
    return [(round(i * paso), round((i + 1) * paso - hueco) - round(i * paso), i < llenos) for i in range(n)]


def marco(l, x, y, w, h, color, g=1):
    """Un rectángulo hueco, de grosor g."""
    l.rect(x, y, w, g, 0, color)
    l.rect(x, y + h - g, w, g, 0, color)
    l.rect(x, y + g, g, h - 2 * g, 0, color)
    l.rect(x + w - g, y + g, g, h - 2 * g, 0, color)


class Arte:
    """Lo que tiene que saber dibujar un tipo de arte. Este es Cristal: no dibuja nada."""

    clave, nombre = "cristal", "Cristal"
    estilos = temas.PREDEFINIDOS
    dibuja = False
    radio_boton = None  # esquinas de los botones (None = las de siempre)

    def forma(self, w, h):
        """El contorno de la tarjeta (puntos del polígono), o None si es un rectángulo."""
        return None

    def tarjeta(self, l, p, w, h, opacidad, pal):
        """Fondo y borde. p: el perfil del tema (widgets o panel)."""

    def barra(self, l, w, h, frac, color, pal):
        """Barra de progreso, con frac de 0 a 1."""

    def nucleo(self, l, x, w, h, frac, color, pal):
        """Una columna de BarrasNucleos, en x."""

    def grafica(self, l, series, tope, w, h, pal):
        """series: [(color, datos)]; tope: el valor de arriba del todo."""

    def muestra(self, l, t, w, h):
        """La miniatura de un estilo en Configuración: tarjeta, dos textos y una barra."""
        g = t["global"]
        pal = {"texto": temas.hex_rgb(g["texto"]), "gris": temas.hex_rgb(g["texto_sec"]),
               "tenue": temas.hex_rgb(g["texto"]), "azul": temas.hex_rgb(g["acento"])}
        self.tarjeta(l, t["widgets"], w, h, 1.0, pal)
        l.rect(12, 11, 40, 7, 0, pal["texto"])
        l.rect(12, 23, 60, 4, 0, pal["gris"])


class PixelArt(Arte):
    """Bloques: esquinas en escalones y barras y gráficas a saltos."""

    clave, nombre = "pixel", "Pixel art"
    dibuja = True
    radio_boton = 0
    PIXEL = 3  # lo que mide un "píxel" de las esquinas y el borde
    estilos = {
        "Game Boy": _estilo("pixel", "#9bbc0f", "#c4d86a", "#8bac0f", "#0f380f", "#8bac0f", "#0a2a0a", PIXEL),
        "8 bits": _estilo("pixel", "#ffcd75", "#f4f4f4", "#94b0c2", "#1a1c2c", "#f4f4f4", "#0d0e17", PIXEL),
        "Arcade": _estilo("pixel", "#ff2e88", "#f5f0ff", "#9d8bd1", "#140c2a", "#29e7ff", "#07040f", PIXEL),
        "Mazmorra": _estilo("pixel", "#e09f3e", "#f1e3c6", "#a8917a", "#2b2119", "#7a5c3e", "#120d09", PIXEL),
    }

    def forma(self, w, h):
        d, e = self.PIXEL, 2 * self.PIXEL
        return [(e, 0), (w - e, 0), (w - e, d), (w - d, d), (w - d, e), (w, e), (w, h - e), (w - d, h - e),
                (w - d, h - d), (w - e, h - d), (w - e, h), (e, h), (e, h - d), (d, h - d), (d, h - e), (0, h - e),
                (0, e), (d, e), (d, d), (e, d)]

    def tarjeta(self, l, p, w, h, opacidad, pal):
        l.poligono(self.forma(w, h), _alfa(temas.hex_rgb(p["fondo"]), p["opacidad"] * opacidad))
        if p["borde_grosor"] <= 0:
            return
        b = self.PIXEL
        borde = _alfa(temas.hex_rgb(p["borde"]), p["borde_opacidad"] * opacidad)
        for x, y, ancho, alto in ((2 * b, 0, w - 4 * b, b), (2 * b, h - b, w - 4 * b, b), (0, 2 * b, b, h - 4 * b),
                                  (w - b, 2 * b, b, h - 4 * b), (b, b, b, b), (w - 2 * b, b, b, b), (b, h - 2 * b, b, b),
                                  (w - 2 * b, h - 2 * b, b, b)):
            l.rect(x, y, ancho, alto, 0, borde)

    def barra(self, l, w, h, frac, color, pal):
        for x, largo, lleno in tramos(w, frac, 6, 2):
            l.rect(x, 0, largo, h, 0, color if lleno else _alfa(pal["tenue"], 0.11))

    def nucleo(self, l, x, w, h, frac, color, pal):
        for y, largo, lleno in tramos(h, frac, 4, 2):
            l.rect(x, h - y - largo, w, largo, 0, color if lleno else _alfa(pal["tenue"], 0.085))

    def grafica(self, l, series, tope, w, h, pal):
        l.rect(0, 0, w, h, 0, (0, 0, 0, 0.2))
        b = 4
        for color, datos in series:
            for i, v in enumerate(_columnas(datos, tope, max(1, w // b))):
                y = h - b - round(v * (h - b) / b) * b
                l.rect(i * b, y, b, h - y, 0, _alfa(color, 0.16))
                l.rect(i * b, y, b, b, 0, color)

    def muestra(self, l, t, w, h):
        super().muestra(l, t, w, h)
        for x, largo, _lleno in tramos(w - 24, 1.0, 6, 2):
            l.rect(12 + x, 33, largo, 5, 0, temas.hex_rgb(t["global"]["acento"]))


class Terminal(Arte):
    """Un monitor de fósforo: líneas de barrido, marco doble y gráficas de puntos que brillan."""

    clave, nombre = "terminal", "Terminal"
    dibuja = True
    radio_boton = 0
    estilos = {
        "Fósforo": _estilo("terminal", "#33ff66", "#7dffa0", "#2fae55", "#050d07", "#33ff66", "#000000"),
        "Ámbar": _estilo("terminal", "#ffb000", "#ffc94d", "#b37a00", "#0e0900", "#ffb000", "#000000"),
        "Hielo": _estilo("terminal", "#66d9ff", "#b4ecff", "#4a93ad", "#03090d", "#66d9ff", "#000000"),
    }

    def tarjeta(self, l, p, w, h, opacidad, pal):
        l.rect(0, 0, w, h, 0, _alfa(temas.hex_rgb(p["fondo"]), p["opacidad"] * opacidad))
        for y in range(0, h, 4):
            l.rect(0, y, w, 1, 0, _alfa(temas.hex_rgb(p["borde"]), 0.035 * opacidad))
        if p["borde_grosor"] <= 0:
            return
        borde = temas.hex_rgb(p["borde"])
        marco(l, 0, 0, w, h, _alfa(borde, 0.9 * p["borde_opacidad"] * opacidad))
        marco(l, 3, 3, w - 6, h - 6, _alfa(borde, 0.3 * p["borde_opacidad"] * opacidad))
        for x, y in ((0, 0), (w - 9, 0), (0, h - 2), (w - 9, h - 2)):  # las esquinas, más fuertes
            l.rect(x, y, 9, 2, 0, _alfa(borde, opacidad))

    def barra(self, l, w, h, frac, color, pal):
        l.rect(0, 0, 2, h, 0, color)  # [ ... ]
        l.rect(w - 2, 0, 2, h, 0, color)
        for x, largo, lleno in tramos(w - 8, frac, 2, 2):
            l.rect(4 + x, 0, largo, h, 0, color if lleno else _alfa(pal["tenue"], 0.1))

    def nucleo(self, l, x, w, h, frac, color, pal):
        for y, largo, lleno in tramos(h, frac, 2, 2):
            l.rect(x, h - y - largo, w, largo, 0, color if lleno else _alfa(pal["tenue"], 0.07))

    def grafica(self, l, series, tope, w, h, pal):
        for y in range(0, h, 8):
            for x in range(0, w, 8):
                l.rect(x, y, 1, 1, 0, _alfa(pal["tenue"], 0.18))
        paso = 3
        for color, datos in series:
            for i, v in enumerate(_columnas(datos, tope, max(1, w // paso))):
                y = round((1 - v) * (h - 3))
                l.rect(i * paso - 1, y - 1, 4, 4, 0, _alfa(color, 0.2))  # el brillo
                l.rect(i * paso, y, 2, 2, 0, color)

    def muestra(self, l, t, w, h):
        super().muestra(l, t, w, h)
        for x, largo, _lleno in tramos(w - 24, 1.0, 2, 2):
            l.rect(12 + x, 33, largo, 5, 0, temas.hex_rgb(t["global"]["acento"]))


class Comic(Arte):
    """Viñetas: tinta gruesa, sombra dura, formas algo torcidas y trama de puntos."""

    clave, nombre = "comic", "Cómic"
    dibuja = True
    radio_boton = 2
    SOMBRA = 6
    TINTA = 3
    estilos = {
        "Pop": _estilo("comic", "#e4322b", "#1b1b1f", "#55525a", "#fff4d6", "#1b1b1f", "#3b6fb5"),
        "Noir": _estilo("comic", "#f5c400", "#f4f1e8", "#a9a59a", "#16161a", "#f4f1e8", "#000000"),
        "Tebeo": _estilo("comic", "#2f6f9f", "#2b2118", "#6d5a45", "#ecd9b0", "#2b2118", "#8a5a3c"),
    }

    @staticmethod
    def _papel(tinta):
        """Lo de dentro de barras y gráficas: más claro que el papel, o más oscuro en los estilos oscuros."""
        return (1, 1, 1, 0.6) if sum(tinta[:3]) < 1.5 else (0, 0, 0, 0.6)

    def forma(self, w, h):
        w, h = w - self.SOMBRA, h - self.SOMBRA
        return [(2, 0), (w, 3), (w - 2, h - 1), (0, h - 3)]

    def tarjeta(self, l, p, w, h, opacidad, pal):
        fuera = self.forma(w, h)
        tinta = _alfa(temas.hex_rgb(p["borde"]), p["borde_opacidad"] * opacidad)
        l.poligono([(x + self.SOMBRA, y + self.SOMBRA) for x, y in fuera], tinta)
        l.poligono(fuera, tinta)
        t = self.TINTA if p["borde_grosor"] > 0 else 0
        dentro = [(x + (t if i in (0, 3) else -t), y + (t if i in (0, 1) else -t)) for i, (x, y) in enumerate(fuera)]
        l.poligono(dentro, _alfa(temas.hex_rgb(p["fondo"]), p["opacidad"] * opacidad))
        # La trama de puntos de la esquina: cada vez más pequeños
        paso = 9
        ancho = w - self.SOMBRA - 2 * t - 4
        for fila in range(6):
            for col in range(6 - fila):
                r = (6 - fila - col) * 0.62
                l.circulo(ancho - col * paso, 2 * t + 4 + fila * paso, r, _alfa(pal["azul"], 0.45 * opacidad))

    def barra(self, l, w, h, frac, color, pal):
        tinta = pal["texto"]
        l.rect(0, 0, w, h, 0, self._papel(tinta))
        lleno = round((w - 2) * min(max(frac, 0.0), 1.0))
        if lleno > 0:
            l.rect(1, 1, lleno, h - 2, 0, color)
        for x in range(1, lleno - h, 9):  # las rayas de la tinta
            l.poligono([(x + h, 1), (x + h + 3, 1), (x + 3, h - 1), (x, h - 1)], _alfa(tinta, 0.3))
        marco(l, 0, 0, w, h, tinta)

    def nucleo(self, l, x, w, h, frac, color, pal):
        l.rect(x, 0, w, h, 0, self._papel(pal["texto"]))
        alto = round((h - 2) * frac)
        if alto > 0:
            l.rect(x + 1, h - 1 - alto, w - 2, alto, 0, color)
        marco(l, x, 0, w, h, pal["texto"])

    def grafica(self, l, series, tope, w, h, pal):
        tinta = pal["texto"]
        l.rect(0, 0, w, h, 0, self._papel(tinta))
        paso = 6
        for color, datos in series:
            alturas = _columnas(datos, tope, max(2, w // paso))
            puntos = [(2 + i * (w - 4) / (len(alturas) - 1), h - 3 - v * (h - 6)) for i, v in enumerate(alturas)]
            l.poligono([*puntos, (w - 2, h - 2), (2, h - 2)], _alfa(color, 0.3))
            for a, b in zip(puntos, puntos[1:]):
                l.linea(*a, *b, 3.2, tinta, True)
            for a, b in zip(puntos, puntos[1:]):
                l.linea(*a, *b, 1.6, color, True)
        marco(l, 0, 0, w, h, tinta, 2)

    def muestra(self, l, t, w, h):
        super().muestra(l, t, w, h)
        l.rect(12, 33, w - 40, 5, 0, temas.hex_rgb(t["global"]["acento"]))


ARTES = (Arte(), PixelArt(), Terminal(), Comic())


def de(clave):
    """El tipo de arte por su clave (uno desconocido, Cristal: un tema de una versión más nueva)."""
    return next((a for a in ARTES if a.clave == clave), ARTES[0])
