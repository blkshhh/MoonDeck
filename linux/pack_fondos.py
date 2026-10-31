"""Fondos de Unsplash en el modo panel (Linux), con controles en una franja debajo de la cuadrícula."""

from __main__ import *  # noqa: F403 - las piezas de monitor.py (etiqueta, Tarjeta, Dibujo...)
import __main__ as M  # lo que cambia mientras corre (colores del tema, ANCHO...)
import fondos
from idioma import _

WIDGETS = ()
ALTO_FRANJA = 44
RESERVA = 20  # lo que la franja le quita a la cuadrícula (el resto es su margen de siempre)
CSS_FRANJA = b"label, button, image { color: #fff; } label link { color: #fff; }"


def cubrir(pixbuf, ancho, alto):
    """La imagen escalada para cubrir ancho x alto, recortando lo que sobre."""
    w, h = pixbuf.get_width(), pixbuf.get_height()
    escala = max(ancho / w, alto / h)
    nueva = pixbuf.scale_simple(max(ancho, round(w * escala)), max(alto, round(h * escala)),
                                GdkPixbuf.InterpType.BILINEAR)
    x, y = (nueva.get_width() - ancho) // 2, (nueva.get_height() - alto) // 2
    return nueva.new_subpixbuf(x, y, ancho, alto)


class Franja(Gtk.EventBox):
    def __init__(self, app):
        super().__init__(halign=Gtk.Align.FILL, valign=Gtk.Align.END)
        self.app = app
        self.set_visible_window(False)
        self.set_size_request(-1, ALTO_FRANJA)
        fila = caja(False, 6)
        fila.set_halign(Gtk.Align.CENTER)
        fila.set_valign(Gtk.Align.CENTER)
        self.b_anterior = boton_icono("media-skip-backward-symbolic")
        self.b_pausa = boton_icono("media-playback-pause-symbolic")
        self.b_siguiente = boton_icono("media-skip-forward-symbolic")
        for b, fn in ((self.b_anterior, app.fondos.anterior), (self.b_pausa, app.pausar_fondo),
                      (self.b_siguiente, app.fondos.siguiente)):
            b.connect("clicked", lambda _b, f=fn: f())
            fila.pack_start(b, False, False, 0)
        self.add(fila)
        css = Gtk.CssProvider()
        css.load_from_data(CSS_FRANJA)
        for w in (self.b_anterior, self.b_pausa, self.b_siguiente):
            w.get_style_context().add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        fila.connect("draw", self._pintar)
        self.show_all()

    @staticmethod
    def _pintar(w, cr):
        cr.set_source_rgba(0, 0, 0, 0.45)
        cr.rectangle(0, 0, w.get_allocated_width(), w.get_allocated_height())
        cr.fill()
        return False


class Metodos:
    """Se añaden a Monitor."""

    def pausar_fondo(self):
        self.fondos.alternar_pausa()
        self.pintar_franja()

    def activar_fondos(self, activo):
        self.fondos.configurar(activo=activo)
        if activo:
            self.fondos.arrancar()
        self.colocar_franja()

    def colocar_franja(self):
        v = self.panel
        if not v:
            return
        activo = self.fondos.cfg["activo"]
        reserva = RESERVA if activo else 0
        if not activo:
            v.imagen = None
        if v.franja:
            v.franja.set_visible(activo)
        if v.reserva_abajo != reserva:
            v.reserva_abajo = reserva
            v.recalcular(asignar=False)
        v.repintar_fondo()
        self.pintar_imagen()
        self.pintar_franja()

    def pintar_imagen(self):
        v, f = self.panel, self.fondos
        if not v or not f.imagen or not f.cfg["activo"]:
            return
        cargador = GdkPixbuf.PixbufLoader()
        try:
            cargador.write(f.imagen)
            cargador.close()
            v.imagen = cubrir(cargador.get_pixbuf(), *v.tam_fondo())
        except GLib.Error as e:
            log("Fondo que no se pudo leer:", e)
        self._fondo_tam = v.tam_fondo()
        v.repintar_fondo()

    def pintar_franja(self):
        v, f = self.panel, self.fondos
        if not v or not v.franja:
            return
        fr = v.franja
        poner_icono(fr.b_pausa, "media-playback-start-symbolic" if f.cfg["pausado"]
                    else "media-playback-pause-symbolic")
        fr.b_anterior.set_sensitive(f.cfg["indice"] > 0)

    def vigilar_fondos(self):
        f, v = self.fondos, self.panel
        f.comprobar()
        if v:
            f.tam = v.tam_fondo()
            if f.version != self._fondo_visto or v.tam_fondo() != self._fondo_tam:
                self._fondo_visto = f.version
                self.pintar_imagen()
            self.pintar_franja()
        return True


def iniciar(self):
    self.fondos = fondos.Fondos(self.config.setdefault("fondos", {}), self.guardar_config)
    self._fondo_visto = 0
    self._fondo_tam = None


def fondo_propio(self):
    return self.fondos.cfg["activo"]


def panel(self, ventana):
    ventana.franja = Franja(self)
    ventana.superposicion.add_overlay(ventana.franja)
    ventana.superposicion.set_overlay_pass_through(ventana.franja, False)
    ventana.franja.set_no_show_all(True)
    self.panel = self.panel or ventana
    self.colocar_franja()


def arrancar(self):
    self.fondos.arrancar()
    GLib.timeout_add(1000, self.vigilar_fondos)


def ajustes_panel(self, cont):
    """Configuración > Panel (self es la ventana)."""
    f = self.app.fondos
    c = f.cfg
    lista = self.grupo(cont, "Fondos de Unsplash", "Una foto detrás de las tarjetas, en lugar del color del panel.")
    activo = Gtk.Switch(active=c["activo"])
    activo.connect("notify::active", lambda w, _p: (self.app.activar_fondos(w.get_active()),
                                                            GLib.idle_add(self.construir)))
    self.fila(lista, "Activar fondos", activo)
    clave = Gtk.Entry(text=c["clave"], visibility=False, width_chars=24)
    clave.connect("changed", lambda w: f.escribir(clave=w.get_text().strip()))
    self.fila(lista, "Clave de acceso", clave, "Gratis en unsplash.com/developers")
    tags = Gtk.Entry(text=c["etiquetas"], width_chars=24)
    tags.connect("changed", lambda w: f.apuntar(etiquetas=w.get_text()))
    aplicar = Gtk.Button(label=_("Aplicar"))
    aplicar.connect("clicked", lambda _b: f.aplicar())
    control = caja(False, 6)
    control.pack_start(tags, False, False, 0)
    control.pack_start(aplicar, False, False, 0)
    self.fila(lista, "Etiquetas", control, "Separadas por comas. Cada tanda usa una de ellas.")
    modo = Gtk.ComboBoxText()
    for ident, nombre in fondos.MODOS:
        modo.append(ident, _(nombre))
    modo.set_active_id(c["modo"])
    modo.connect("changed", lambda w: f.configurar(modo=w.get_active_id()))
    self.fila(lista, "Cambiar de fondo", modo)
    minutos = Gtk.SpinButton.new_with_range(1, 1440, 1)
    minutos.set_value(c["minutos"])
    minutos.connect("value-changed", lambda w: f.configurar(minutos=w.get_value_as_int()))
    self.fila(lista, "Minutos", minutos, "Para \"Cada X minutos\"")
