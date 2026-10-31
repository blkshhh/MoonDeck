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
        fila.set_margin_start(24)
        fila.set_margin_end(24)
        self.credito = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        self.b_anterior = boton_icono("media-skip-backward-symbolic")
        self.b_pausa = boton_icono("media-playback-pause-symbolic")
        self.b_siguiente = boton_icono("media-skip-forward-symbolic")
        self.estado = Gtk.Label(xalign=1, ellipsize=Pango.EllipsizeMode.END)
        grupo = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        grupo.add_widget(self.credito)
        grupo.add_widget(self.estado)
        fila.pack_start(self.credito, True, True, 0)
        for b, fn in ((self.b_anterior, app.fondos.anterior), (self.b_pausa, app.pausar_fondo),
                      (self.b_siguiente, app.fondos.siguiente)):
            b.connect("clicked", lambda _b, f=fn: f())
            fila.pack_start(b, False, False, 0)
        fila.pack_start(self.estado, True, True, 0)
        self.add(fila)
        css = Gtk.CssProvider()
        css.load_from_data(CSS_FRANJA)
        for w in (self.credito, self.estado, self.b_anterior, self.b_pausa, self.b_siguiente):
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
        v.lienzo.queue_draw()
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
            v.imagen = cubrir(cargador.get_pixbuf(), *v.tam)
        except GLib.Error as e:
            log("Fondo que no se pudo leer:", e)
        self._fondo_tam = v.tam
        v.lienzo.queue_draw()

    def pintar_franja(self):
        v, f = self.panel, self.fondos
        if not v or not v.franja:
            return
        fr = v.franja
        foto = f.foto
        if foto:
            autor = GLib.markup_escape_text(foto["autor"])
            enlace = f'<a href="{GLib.markup_escape_text(foto["perfil"])}">{autor}</a>'
            web = f'<a href="{GLib.markup_escape_text(fondos.WEB)}">Unsplash</a>'
            fr.credito.set_markup(_("Foto de {autor} en {web}").format(autor=enlace, web=web))
        else:
            fr.credito.set_text("")
        poner_icono(fr.b_pausa, "media-playback-start-symbolic" if f.cfg["pausado"]
                    else "media-playback-pause-symbolic")
        fr.b_anterior.set_sensitive(f.cfg["indice"] > 0)
        falta = f.restante()
        if not f.cfg["clave"].strip():
            texto = _("Pon tu clave en Configuración > Panel.")
        elif f.error:
            texto = f.error
        elif f.cfg["pausado"]:
            texto = _("En pausa")
        elif falta is not None:
            texto = _("Cambia en {n} min").format(n=falta // 60 + 1)
        else:
            texto = ""
        poner_texto(fr.estado, texto)

    def vigilar_fondos(self):
        f, v = self.fondos, self.panel
        f.comprobar()
        if v:
            f.tam = v.tam
            if f.version != self._fondo_visto or v.tam != self._fondo_tam:
                self._fondo_visto = f.version
                self.pintar_imagen()
            self.pintar_franja()
        return True


def iniciar(self):
    self.fondos = fondos.Fondos(self.config.setdefault("fondos", {}), self.guardar_config)
    self._fondo_visto = 0
    self._fondo_tam = None


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
    lista = self.grupo(cont, "Fondos de Unsplash", "Una foto detrás de las tarjetas, bajo el velo del panel.")
    activo = Gtk.Switch(active=c["activo"])
    activo.connect("notify::active", lambda w, _p: self.app.activar_fondos(w.get_active()))
    self.fila(lista, "Activar fondos", activo)
    clave = Gtk.Entry(text=c["clave"], visibility=False, width_chars=24)
    clave.connect("focus-out-event", lambda w, _e: f.configurar(clave=w.get_text().strip()) or False)
    self.fila(lista, "Clave de acceso", clave, "Gratis en unsplash.com/developers")
    tags = Gtk.Entry(text=c["etiquetas"], width_chars=24)
    tags.connect("focus-out-event", lambda w, _e: f.configurar(etiquetas=w.get_text()) or False)
    self.fila(lista, "Etiquetas", tags, "Separadas por comas. Cada tanda usa una de ellas.")
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
