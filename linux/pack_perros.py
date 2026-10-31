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
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_MOTION_MASK)
        self.connect("draw", self.dibujar)
        self.connect("motion-notify-event", self.frotar)
        self.connect("button-press-event", lambda _w, e: setattr(self, "ultimo", (e.x, e.y)))
        self.show_all()

    def frotar(self, _w, e):
        if self.ultimo:
            self.vida -= min(math.hypot(e.x - self.ultimo[0], e.y - self.ultimo[1]), 30) * .012
        self.ultimo = (e.x, e.y)
        self.queue_draw()
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
                                        al_hacer=self.perro_hizo, al_acariciar=p.acariciar)
        self.ventana_perro.show_all()

    def guardar_perro(self):
        if self.ventana_perro:
            self.ventana_perro.destroy()
            self.ventana_perro = None

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
        self.pintar_perro()

    def pintar_perro(self):
        d = self.partida_perro.d
        for clave, barra in self.barras_perro.items():
            barra.set(d[clave] * 100)
        self.boton_perro.set_label(_("Guardar") if d["fuera"] else _("Sacar"))

    def vivir_perro(self):
        toca = self.partida_perro.avanzar()
        v = self.ventana_perro
        if toca and v and v.can.accion not in ("pis", "caca"):
            v.can.pedir(toca)
        self.pintar_perro()
        return True


def iniciar(self):
    self.partida_perro = can_partida.Partida(self.config.setdefault("perros", {}), self.guardar_config)
    self.ventana_perro = None
    self.ventanas_mancha = []


def construir(self, s):
    c = self.tarjeta("perros", "Perro")
    self.barras_perro = {}
    for clave, texto in (("hambre", "Hambre"), ("sed", "Sed"), ("limpieza", "Limpieza"), ("animo", "Ánimo")):
        c.add_w(etiqueta(texto, "dim"))
        self.barras_perro[clave] = c.add_w(Barra(8, "acento"))
    p = self.partida_perro
    fila = caja(False, 6)
    for texto, fn in (("Comida", lambda _b: self.cuidar_perro(p.comer)), ("Agua", lambda _b: self.cuidar_perro(p.beber)),
                      ("Lavar", lambda _b: self.cuidar_perro(p.lavar))):
        b = Gtk.Button(label=_(texto))
        b.connect("clicked", fn)
        fila.pack_start(b, True, True, 0)
    c.add_w(fila)
    fila = caja(False, 6)
    b = Gtk.Button(label=_("Llamar"))
    b.connect("clicked", self.llamar_perro)
    fila.pack_start(b, True, True, 0)
    self.boton_perro = Gtk.Button(label=_("Guardar"))
    self.boton_perro.connect("clicked", self.alternar_perro)
    fila.pack_start(self.boton_perro, True, True, 0)
    c.add_w(fila)


def arrancar(self):
    for m in self.partida_perro.d["manchas"]:
        self.poner_mancha(m)
    if self.partida_perro.d["fuera"]:
        self.sacar_perro()
    self.pintar_perro()
    GLib.timeout_add(CADA_MS, self.vivir_perro)


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
