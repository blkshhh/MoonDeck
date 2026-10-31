"""Perros (Linux): un perro en 3D que anda por el escritorio y este widget para cuidarlo."""

from __main__ import *  # noqa: F403 - las piezas de monitor.py (etiqueta, Tarjeta, caja...)
import __main__ as M  # lo que cambia mientras corre (colores del tema, ANCHO...)
import can_esqueleto
import can_partida
from can_ventana import VentanaCan
from gi.repository import GtkLayerShell
from idioma import _

WIDGETS = ('perros',)
CADA_MS = 5000
ANCHO_MANCHA, ALTO_MANCHA = 150, 110


class VentanaMancha(Gtk.Window):
    """Pis o caca sobre el escritorio: tapa lo que haya debajo hasta que se frota."""

    def __init__(self, mancha, monitor, al_limpiar):
        super().__init__()
        self.mancha, self.al_limpiar, self.vida = mancha, al_limpiar, 1.0
        self.ultimo = None
        self.set_visual(self.get_screen().get_rgba_visual())
        self.set_app_paintable(True)
        self.set_default_size(ANCHO_MANCHA, ALTO_MANCHA)
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, "moondeck-mancha")
        if monitor:
            GtkLayerShell.set_monitor(self, monitor)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.BOTTOM)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_exclusive_zone(self, -1)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, max(0, mancha["x"] - ANCHO_MANCHA // 2))
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, max(0, mancha["y"] - ALTO_MANCHA // 2))
        # Una capa sin contenido se queda sin tamaño: el área es la que le da los píxeles.
        area = Gtk.DrawingArea()
        area.set_size_request(ANCHO_MANCHA, ALTO_MANCHA)
        area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_MOTION_MASK)
        area.connect("draw", self.dibujar)
        area.connect("motion-notify-event", self.frotar)
        area.connect("button-press-event", lambda _w, e: setattr(self, "ultimo", (e.x, e.y)))
        self.add(area)
        self.area = area
        self.show_all()

    def frotar(self, _w, e):
        if self.ultimo:
            self.vida -= min(math.hypot(e.x - self.ultimo[0], e.y - self.ultimo[1]), 30) * .012
        self.ultimo = (e.x, e.y)
        self.area.queue_draw()
        if self.vida <= 0:
            self.al_limpiar(self)

    def dibujar(self, _w, cr):
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        a = max(self.vida, 0)
        cx, cy = ANCHO_MANCHA / 2, ALTO_MANCHA / 2

        def ovalo(x, y, rx, ry):
            cr.save()
            cr.translate(x, y)
            cr.scale(rx, ry)
            cr.new_path()
            cr.arc(0, 0, 1, 0, 2 * math.pi)
            cr.restore()

        if self.mancha["tipo"] == "pis":
            ovalo(cx, cy, 66, 24)
            cr.set_source_rgba(1, .86, .4, .85 * a)
            cr.fill()
            return False
        for dy, rx, ry in ((22, 38, 17), (2, 28, 15), (-16, 17, 12)):
            ovalo(cx, cy + dy, rx, ry)
            cr.set_source_rgba(.37, .23, .13, a)
            cr.fill_preserve()
            cr.set_source_rgba(.23, .13, .08, a)
            cr.set_line_width(3)
            cr.stroke()
        return False


def dibujar_icono(cr, nombre, tinta):
    """Los iconos de los botones, en un cuadro de 28 x 28."""
    cr.set_line_width(2)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)

    def forma(color):
        cr.set_source_rgb(*color)
        cr.fill_preserve()
        cr.set_source_rgb(*tinta)
        cr.stroke()

    def bola(x, y, r, color):
        cr.new_sub_path()
        cr.arc(x, y, r, 0, 2 * math.pi)
        forma(color)

    def gota(x, y, q, color):
        cr.new_path()
        cr.move_to(x, y - q)
        cr.curve_to(x + q, y, x + q * .7, y + q * .85, x, y + q * .85)
        cr.curve_to(x - q * .7, y + q * .85, x - q, y, x, y - q)
        forma(color)

    azul, amarillo, rojo = (.33, .64, .9), (.98, .8, .25), (.89, .4, .36)
    if nombre == "comida":  # cuenco con pienso
        for x, y in ((9, 11), (14, 8), (19, 11), (12, 13), (17, 13)):
            bola(x, y, 3, (.68, .42, .22))
        cr.new_path()
        cr.move_to(3, 14)
        cr.line_to(25, 14)
        cr.line_to(21, 24)
        cr.line_to(7, 24)
        cr.close_path()
        forma(rojo)
    elif nombre == "agua":
        gota(14, 13, 11, azul)
    elif nombre == "banar":  # bañera con burbujas
        for x, y, r in ((9, 9, 3.4), (15, 6, 4.2), (21, 9, 3)):
            bola(x, y, r, (1, 1, 1))
        cr.new_path()
        cr.rectangle(3, 13, 22, 9)
        forma(azul)
        cr.move_to(8, 22)
        cr.line_to(7, 25)
        cr.move_to(20, 22)
        cr.line_to(21, 25)
        cr.stroke()
    elif nombre == "esponja":
        cr.new_path()
        cr.rectangle(4, 8, 20, 14)
        forma(amarillo)
        for x, y in ((9, 12), (15, 17), (20, 12)):
            cr.new_path()
            cr.arc(x, y, 1.5, 0, 2 * math.pi)
            cr.set_source_rgb(.72, .52, .1)
            cr.fill()
    elif nombre == "ducha":  # alcachofa y gotas
        cr.set_source_rgb(*tinta)
        cr.new_path()
        cr.move_to(21, 4)
        cr.curve_to(14, 2, 12, 5, 12, 9)
        cr.stroke()
        cr.new_path()
        cr.move_to(5, 15)
        cr.curve_to(6, 7, 18, 7, 19, 15)
        cr.close_path()
        forma((.76, .8, .84))
        for x, y in ((7, 20), (12, 23), (17, 20)):
            gota(x, y, 2.6, azul)
    elif nombre == "toalla":
        cr.new_path()
        cr.rectangle(5, 4, 18, 20)
        forma(rojo)
        cr.move_to(5, 16)
        cr.line_to(23, 16)
        cr.move_to(5, 19)
        cr.line_to(23, 19)
        cr.stroke()
    elif nombre == "terminar":  # hecho
        cr.new_path()
        cr.set_line_width(3.6)
        cr.move_to(5, 15)
        cr.line_to(12, 22)
        cr.line_to(24, 7)
        cr.set_source_rgb(.25, .65, .38)
        cr.stroke()
    elif nombre == "silbato":
        cr.new_path()
        cr.arc(11, 16, 8, 0, 2 * math.pi)
        forma(amarillo)
        cr.new_path()
        cr.rectangle(13, 7, 12, 6)
        forma(amarillo)
        bola(11, 16, 2.4, tinta)
        cr.set_source_rgb(*tinta)
        for y0, y1, x1 in ((5, 2, 5), (9, 8, 2)):
            cr.move_to(8, y0)
            cr.line_to(x1, y1)
        cr.stroke()
    elif nombre == "caseta":  # guardarlo: la caseta
        cr.new_path()
        cr.move_to(3, 13)
        cr.line_to(14, 4)
        cr.line_to(25, 13)
        cr.close_path()
        forma(rojo)
        cr.new_path()
        cr.rectangle(6, 13, 16, 11)
        forma(amarillo)
        cr.new_path()
        cr.arc(14, 24, 5, math.pi, 2 * math.pi)
        cr.close_path()
        forma(tinta)
    else:  # sacarlo: una huella
        bola(14, 18, 6.5, (.68, .42, .22))
        for x, y in ((6, 12), (11, 7), (17, 7), (22, 12)):
            bola(x, y, 2.8, (.68, .42, .22))


class BotonIcono(Gtk.ToggleButton):
    """Un botón con dibujo. El nombre del texto queda como aviso al dejar el ratón encima."""

    def __init__(self, icono, texto, al_pulsar, marcable=False):
        super().__init__()
        self.icono, self.marcable, self.cambiando = icono, marcable, False
        self.set_tooltip_text(_(texto))
        area = Gtk.DrawingArea()
        area.set_size_request(28, 28)
        area.connect("draw", self.dibujar)
        self.area = area
        self.add(area)
        self.al_pulsar = al_pulsar
        self.connect("toggled", self.pulsado)
        self.show_all()

    def pulsado(self, _b):
        if self.cambiando:
            return
        if not self.marcable:
            self.marcar(False)
        self.al_pulsar()

    def marcar(self, si):
        self.cambiando = True
        self.set_active(si)
        self.cambiando = False

    def cambiar(self, icono, texto):
        self.icono = icono
        self.set_tooltip_text(_(texto))
        self.area.queue_draw()

    def dibujar(self, _w, cr):
        dibujar_icono(cr, self.icono, paleta()["texto"][:3])
        return False


class Bocadillo(Gtk.Window):
    """Lo que piensa el perro, en una nube que le sigue: un dibujo, sin textos ni barras."""

    ANCHO, ALTO = 112, 104

    def __init__(self, monitor):
        super().__init__()
        self.idea = None
        self.set_visual(self.get_screen().get_rgba_visual())
        self.set_app_paintable(True)
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, "moondeck-bocadillo")
        if monitor:
            GtkLayerShell.set_monitor(self, monitor)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.BOTTOM)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_exclusive_zone(self, -1)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        area = Gtk.DrawingArea()
        area.set_size_request(self.ANCHO, self.ALTO)
        area.connect("draw", self.dibujar)
        self.add(area)
        self.area = area
        self.connect("realize", lambda w: w.get_window().input_shape_combine_region(cairo.Region(), 0, 0))

    def mover(self, x, y):
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, max(0, round(x)))
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, max(0, round(y)))

    def dibujar(self, _w, cr):
        tinta, papel = (.17, .12, .1), (1, .99, .95)

        def bola(x, y, r):
            cr.new_path()
            cr.arc(x, y, r, 0, 2 * math.pi)

        nube = ((36, 42, 26), (70, 40, 28), (54, 28, 25), (54, 54, 25), (84, 52, 18), (26, 56, 16))
        cr.set_source_rgb(*tinta)
        for x, y, r in nube:
            bola(x, y, r + 2.6)
            cr.fill()
        for x, y, r in ((22, 84, 6.5), (11, 97, 4)):
            bola(x, y, r + 2)
            cr.fill()
        cr.set_source_rgb(*papel)
        for x, y, r in (*nube, (22, 84, 6.5), (11, 97, 4)):
            bola(x, y, r)
            cr.fill()
        cx, cy = 54, 42
        if self.idea == "hambre":  # un hueso
            cr.set_source_rgb(.93, .85, .7)
            cr.rectangle(cx - 17, cy - 5, 34, 10)
            cr.fill()
            for dx in (-18, 18):
                for dy in (-7, 7):
                    bola(cx + dx, cy + dy, 8)
                    cr.fill()
        elif self.idea == "sed":  # una gota
            cr.new_path()
            cr.move_to(cx, cy - 23)
            cr.curve_to(cx + 22, cy + 2, cx + 15, cy + 19, cx, cy + 19)
            cr.curve_to(cx - 15, cy + 19, cx - 22, cy + 2, cx, cy - 23)
            cr.set_source_rgb(.3, .62, .9)
            cr.fill()
        elif self.idea == "sucio":  # una bañera con burbujas
            cr.set_source_rgb(.55, .75, .9)
            cr.rectangle(cx - 25, cy - 1, 50, 18)
            cr.fill()
            cr.set_source_rgb(*tinta)
            cr.set_line_width(2.6)
            cr.rectangle(cx - 25, cy - 1, 50, 18)
            cr.stroke()
            for x, y, r in ((-12, -9, 7), (3, -13, 9), (17, -8, 6)):
                bola(cx + x, cy + y, r)
                cr.set_source_rgb(1, 1, 1)
                cr.fill_preserve()
                cr.set_source_rgb(.55, .75, .9)
                cr.stroke()
        else:  # cariño: un corazón
            cr.new_path()
            cr.move_to(cx, cy + 19)
            cr.curve_to(cx - 32, cy - 6, cx - 11, cy - 26, cx, cy - 9)
            cr.curve_to(cx + 11, cy - 26, cx + 32, cy - 6, cx, cy + 19)
            cr.set_source_rgb(.88, .32, .34)
            cr.fill()
        return False


class Metodos:
    """Se añaden a Monitor."""

    def monitor_perro(self):
        d = Gdk.Display.get_default()
        return d.get_primary_monitor() or d.get_monitor(0)

    def sacar_perro(self):
        p = self.partida_perro
        if self.ventana_perro:
            return
        m = self.monitor_perro()
        g = m.get_geometry()
        self.ventana_perro = VentanaCan(p.d["diseno"], g.width, g.height, monitor=m,
                                        al_hacer=self.perro_hizo, al_acariciar=p.acariciar,
                                        al_frotar=self.frotar_perro, al_tic=self.seguir_perro)
        if self.can_perro:  # sigue donde estaba, haciendo lo que hacía
            self.ventana_perro.can = self.can_perro
        self.can_perro = self.ventana_perro.can
        self.pasar_estado()
        self.ventana_perro.show_all()
        if self.herramienta_perro:
            self.ventana_perro.empezar_bano(self.herramienta_perro)

    def guardar_perro(self):
        self.quitar_bocadillo()
        if self.ventana_perro:
            self.ventana_perro.destroy()
            self.ventana_perro = None

    def pasar_estado(self):
        """El perro enseña la partida con el cuerpo: barro, espuma, agua y postura."""
        p, c = self.partida_perro, self.can_perro
        if c:
            c.barro, c.espuma = p.d["barro"], p.espuma
            c.mojado, c.apetito = p.d["mojado"], p.aliento()

    def frotar_perro(self, herramienta, zonas, cuanto):
        self.partida_perro.frotar(herramienta, zonas, cuanto)
        self.pasar_estado()

    def banar_perro(self, _b=None):
        if not self.ventana_perro:
            return
        self.poner_herramienta("esponja")
        self.fila_bano.show()
        self.fila_cuidados.hide()

    def poner_herramienta(self, herramienta):
        self.herramienta_perro = herramienta
        for clave, boton in self.botones_bano.items():
            boton.marcar(clave == herramienta)
        self.quitar_bocadillo()
        if self.ventana_perro:
            self.ventana_perro.empezar_bano(herramienta)

    def terminar_bano(self, _b=None):
        self.herramienta_perro = None
        self.partida_perro.acabar_bano()
        self.pasar_estado()
        if self.ventana_perro:
            self.ventana_perro.acabar_bano()
        self.fila_bano.hide()
        self.fila_cuidados.show()
        self.ajustar_alturas()

    def quitar_bocadillo(self):
        if self.bocadillo_perro:
            self.bocadillo_perro.destroy()
            self.bocadillo_perro = None

    def seguir_perro(self, v):
        b = self.bocadillo_perro
        if b:
            b.mover(v.can.x + 26, v.can.y - 215 - v.can.altura_salto() * .8)

    def pensar_perro(self):
        """Cada rato dice lo que necesita, un momento, sin quedarse fijo en pantalla."""
        self.quitar_bocadillo()
        idea = self.partida_perro.pensamiento()
        if idea and self.ventana_perro and not self.herramienta_perro:
            self.bocadillo_perro = Bocadillo(self.monitor_perro())
            self.bocadillo_perro.idea = idea
            self.seguir_perro(self.ventana_perro)
            self.bocadillo_perro.show_all()
            GLib.timeout_add(5000, lambda: self.quitar_bocadillo() or False)
        return True

    def subir_perro(self):
        """En una capa manda lo último abierto: se reabren para quedar sobre las tarjetas."""
        self.espera_subir = None
        for v in self.ventanas_mancha:
            v.destroy()
        self.ventanas_mancha = []
        for m in self.partida_perro.d["manchas"]:
            self.poner_mancha(m)
        if self.ventana_perro:
            self.guardar_perro()
            self.sacar_perro()
        return False

    def alternar_perro(self, _b=None):
        p = self.partida_perro
        p.d["fuera"] = not p.d["fuera"]
        (self.sacar_perro if p.d["fuera"] else self.guardar_perro)()
        self.guardar_config()
        self.pintar_perro()
        return False

    def llamar_perro(self, _b=None):
        if self.ventana_perro:
            c = self.ventana_perro.can
            c.ir(c.ancho / 2, c.alto * .7)

    def perro_hizo(self, tipo, x, y):
        self.partida_perro.mancha(tipo, x, y)
        self.poner_mancha(self.partida_perro.d["manchas"][-1])

    def poner_mancha(self, mancha):
        self.ventanas_mancha.append(VentanaMancha(mancha, self.monitor_perro(), self.mancha_limpia))

    def mancha_limpia(self, ventana):
        self.partida_perro.quitar_mancha(ventana.mancha)
        self.ventanas_mancha.remove(ventana)
        ventana.destroy()

    def cuidar_perro(self, accion):
        accion()
        if self.ventana_perro:
            self.ventana_perro.can.saltar()
        self.pasar_estado()

    def pintar_perro(self):
        if self.partida_perro.d["fuera"]:
            self.boton_perro.cambiar("caseta", "Guardar")
        else:
            self.boton_perro.cambiar("huella", "Sacar")

    def vivir_perro(self):
        toca = self.partida_perro.avanzar()
        v = self.ventana_perro
        if toca and v and v.can.accion not in ("pis", "caca", "banio"):
            v.can.pedir(toca)
        self.pasar_estado()
        self.pintar_perro()
        return True


def iniciar(self):
    self.partida_perro = can_partida.Partida(self.config.setdefault("perros", {}), self.guardar_config)
    self.ventana_perro = self.can_perro = self.espera_subir = None
    self.bocadillo_perro = self.herramienta_perro = None
    self.ventanas_mancha = []


def construir(self, s):
    c = self.tarjeta("perros", "Perro")
    p = self.partida_perro
    fila = self.fila_cuidados = caja(False, 6)
    for icono, texto, fn in (("comida", "Comida", lambda: self.cuidar_perro(p.comer)),
                             ("agua", "Agua", lambda: self.cuidar_perro(p.beber)), ("banar", "Bañar", self.banar_perro),
                             ("silbato", "Llamar", self.llamar_perro)):
        fila.pack_start(BotonIcono(icono, texto, fn), True, True, 0)
    self.boton_perro = BotonIcono("caseta", "Guardar", self.alternar_perro)
    fila.pack_start(self.boton_perro, True, True, 0)
    c.add_w(fila)
    fila = self.fila_bano = caja(False, 6)
    fila.set_no_show_all(True)
    self.botones_bano = {}
    for clave, texto in (("esponja", "Esponja"), ("ducha", "Ducha"), ("toalla", "Toalla")):
        b = BotonIcono(clave, texto, lambda h=clave: self.poner_herramienta(h), marcable=True)
        self.botones_bano[clave] = b
        fila.pack_start(b, True, True, 0)
    fila.pack_start(BotonIcono("terminar", "Terminar", self.terminar_bano), True, True, 0)
    c.add_w(fila)


def arrancar(self):
    for m in self.partida_perro.d["manchas"]:
        self.poner_mancha(m)
    if self.partida_perro.d["fuera"]:
        self.sacar_perro()
    self.pintar_perro()
    GLib.timeout_add(CADA_MS, self.vivir_perro)
    GLib.timeout_add(25000, self.pensar_perro)


def ventanas_abiertas(self):
    # Con margen: las tarjetas sueltas se colocan un momento después de abrirse.
    if self.espera_subir:
        GLib.source_remove(self.espera_subir)
    self.espera_subir = GLib.timeout_add(1200, self.subir_perro)


def ajustes(self, cont):
    """Configuración > Widgets (self es la ventana)."""
    app = self.app
    lista = self.grupo(cont, "Perros de escritorio")
    raza = Gtk.ComboBoxText()
    for clave, d in can_esqueleto.DISENOS.items():
        raza.append(clave, _(d["nombre"]))
    raza.set_active_id(app.partida_perro.d["diseno"])

    def cambiar(w):
        app.partida_perro.d["diseno"] = w.get_active_id()
        app.guardar_config()
        if app.ventana_perro:
            app.ventana_perro.poner_diseno(w.get_active_id())

    raza.connect("changed", cambiar)
    self.fila(lista, "Raza", raza)


def salir(self):
    self.partida_perro.avanzar()
    self.guardar_perro()
