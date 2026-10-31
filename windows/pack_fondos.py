"""Fondos de Unsplash en el modo panel (Windows), con controles en una franja debajo de la cuadrícula."""

import html

from __main__ import *  # noqa: F403 - las piezas de monitor.py (etiqueta, Tarjeta, Dibujo...)
import __main__ as M  # lo que cambia mientras corre (colores del tema, ANCHO...)
import fondos
from idioma import _

WIDGETS = ()
ALTO_FRANJA = 44
RESERVA = 20  # lo que la franja le quita a la cuadrícula (el resto es su margen de siempre)


def cubrir(pixmap, ancho, alto):
    """La imagen escalada para cubrir ancho x alto, recortando lo que sobre."""
    nueva = pixmap.scaled(ancho, alto, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    return nueva.copy((nueva.width() - ancho) // 2, (nueva.height() - alto) // 2, ancho, alto)


class Franja(QWidget):
    ALTO = ALTO_FRANJA

    def __init__(self, app, padre):
        super().__init__(padre)
        self.app = app
        fila = QHBoxLayout(self)
        fila.setContentsMargins(24, 0, 24, 0)
        fila.setSpacing(6)
        self.credito = QLabel()
        self.credito.setOpenExternalLinks(True)
        self.credito.setStyleSheet("color: #fff; background: transparent;")
        self.b_anterior = boton_icono("anterior")
        self.b_pausa = boton_icono("pausa", 14)
        self.b_siguiente = boton_icono("siguiente")
        self.estado = QLabel(alignment=Qt.AlignRight | Qt.AlignVCenter)
        self.estado.setStyleSheet("color: #fff; background: transparent;")
        fila.addWidget(self.credito, 1)
        for b, fn in ((self.b_anterior, app.fondos.anterior), (self.b_pausa, app.pausar_fondo),
                      (self.b_siguiente, app.fondos.siguiente)):
            b.clicked.connect(lambda _c=False, f=fn: f())
            fila.addWidget(b)
        fila.addWidget(self.estado, 1)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 115))


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
            v.franja.setVisible(activo)
            v.franja.raise_()
        if v.reserva_abajo != reserva:
            v.reserva_abajo = reserva
            v.recalcular()
        v.update()
        self.pintar_imagen()
        self.pintar_franja()

    def pintar_imagen(self):
        v, f = self.panel, self.fondos
        if not v or not f.imagen or not f.cfg["activo"]:
            return
        pixmap = QPixmap()
        if pixmap.loadFromData(f.imagen):
            v.imagen = cubrir(pixmap, v.width(), v.height())
        self._fondo_tam = (v.width(), v.height())
        v.update()

    def pintar_franja(self):
        v, f = self.panel, self.fondos
        if not v or not v.franja:
            return
        fr = v.franja
        foto = f.foto
        if foto:
            enlace = f'<a style="color:#fff" href="{html.escape(foto["perfil"])}">{html.escape(foto["autor"])}</a>'
            web = f'<a style="color:#fff" href="{html.escape(fondos.WEB)}">Unsplash</a>'
            fr.credito.setText(_("Foto de {autor} en {web}").format(autor=enlace, web=web))
        else:
            fr.credito.setText("")
        poner_icono(fr.b_pausa, "play" if f.cfg["pausado"] else "pausa", 14)
        fr.b_anterior.setEnabled(f.cfg["indice"] > 0)
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
        fr.estado.setText(texto)

    def vigilar_fondos(self):
        f, v = self.fondos, self.panel
        f.comprobar()
        if v:
            tam = (v.width(), v.height())
            f.tam = tam
            if f.version != self._fondo_visto or tam != self._fondo_tam:
                self._fondo_visto = f.version
                self.pintar_imagen()
            self.pintar_franja()


def iniciar(self):
    self.fondos = fondos.Fondos(self.config.setdefault("fondos", {}), self.guardar_config)
    self._fondo_visto = 0
    self._fondo_tam = None


def panel(self, ventana):
    ventana.franja = Franja(self, ventana)
    self.panel = self.panel or ventana
    self.colocar_franja()


def arrancar(self):
    self.fondos.arrancar()
    self.t_fondos = QTimer()
    self.t_fondos.timeout.connect(self.vigilar_fondos)
    self.t_fondos.start(1000)


def ajustes_panel(self, caja):
    """Configuración > Panel (self es la ventana)."""
    f = self.app.fondos
    c = f.cfg
    lista = self.grupo(caja, "Fondos de Unsplash", "Una foto detrás de las tarjetas, bajo el velo del panel.")
    activo = QCheckBox()
    activo.setChecked(c["activo"])
    activo.toggled.connect(self.app.activar_fondos)
    self.fila(lista, "Activar fondos", activo)
    clave = QLineEdit(c["clave"])
    clave.setEchoMode(QLineEdit.Password)
    clave.editingFinished.connect(lambda: f.configurar(clave=clave.text().strip()))
    self.fila(lista, "Clave de acceso", clave, "Gratis en unsplash.com/developers")
    tags = QLineEdit(c["etiquetas"])
    tags.editingFinished.connect(lambda: f.configurar(etiquetas=tags.text()))
    self.fila(lista, "Etiquetas", tags, "Separadas por comas. Cada tanda usa una de ellas.")
    modo = QComboBox()
    for ident, nombre in fondos.MODOS:
        modo.addItem(_(nombre), ident)
    modo.setCurrentIndex(max(0, modo.findData(c["modo"])))
    modo.currentIndexChanged.connect(lambda _i: f.configurar(modo=modo.currentData()))
    self.fila(lista, "Cambiar de fondo", modo)
    minutos = QSpinBox()
    minutos.setRange(1, 1440)
    minutos.setValue(c["minutos"])
    minutos.valueChanged.connect(lambda v: f.configurar(minutos=v))
    self.fila(lista, "Minutos", minutos, "Para \"Cada X minutos\"")
