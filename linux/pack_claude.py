"""Widget Claude (Linux): lo gastado del plan en 5 horas y en la semana, con dos anillos."""

from __main__ import *  # noqa: F403 - las piezas de monitor.py (etiqueta, Tarjeta, Dibujo...)
import __main__ as M  # lo que cambia mientras corre (colores del tema, ANCHO...)
import uso_claude
from idioma import _

WIDGETS = ('claude',)
CADA_MS = 30000


class AnillosUso(Dibujo):
    def __init__(self):
        super().__init__()
        self.poner_alto(80, 120)
        self.set_vexpand(True)
        self.cinco = self.semana = None
        self.connect("draw", self.dibujar)

    def poner(self, cinco, semana):
        if (cinco, semana) != (self.cinco, self.semana):
            self.cinco, self.semana = cinco, semana
            self.queue_draw()

    def dibujar(self, _w, cr):
        esferas.anillos_uso(LienzoCairo(self, cr), paleta(), self.get_allocated_width(),
                            self.get_allocated_height(),
                            ((self.cinco, _("5 horas")), (self.semana, _("Semana"))))


class Metodos:
    """Se añaden a Monitor."""

    def actualizar_claude(self):
        u = uso_claude.leer()
        if not u:
            self.claude_anillos.poner(None, None)
            poner_texto(self.claude_pie, _("Usa Claude Code con el mod para ver datos."))
            return True
        self.claude_anillos.poner(u["cinco"], u["semana"])
        if u["vuelve"]:
            poner_texto(self.claude_pie, _("Vuelve en {tiempo}").format(tiempo=uso_claude.duracion(u["vuelve"])))
        elif u["leido"]:
            poner_texto(self.claude_pie, _("Última lectura: {hora}").format(
                hora=u["leido"].astimezone().strftime("%H:%M")))
        return True


def construir(self, s):
    c = self.tarjeta("claude", "Claude")
    self.claude_anillos = c.add_w(AnillosUso(), expand=True)
    self.claude_pie = c.add_w(etiqueta("", "dim"), prescindible=1)
    self.claude_pie.set_xalign(0.5)


def arrancar(self):
    self.actualizar_claude()
    GLib.timeout_add(CADA_MS, self.actualizar_claude)
