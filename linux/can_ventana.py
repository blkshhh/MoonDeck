#!/usr/bin/env python3
"""Ventana de la mascota: una capa pequeña que anda por el escritorio, por debajo de las ventanas.

De momento se puede lanzar sola:  python3 can_ventana.py [diseño] [segundos]
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "comun"))

import cairo
import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, Gtk, GtkLayerShell

import can_esqueleto as ce
from can_gl import Dibujo

LADO, PIE_Y, ESC = 340, 300, .8
TINTA, OJO, LENGUA = (.17, .12, .1), (.13, .09, .07), (.89, .5, .49)


def rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


class VentanaCan(Gtk.Window):
    def __init__(self, diseno, ancho, alto, segundos=0, monitor=None, al_hacer=None, al_acariciar=None):
        super().__init__()
        self.al_hacer, self.al_acariciar = al_hacer, al_acariciar
        self.set_visual(self.get_screen().get_rgba_visual())
        self.set_app_paintable(True)
        self.set_default_size(LADO, LADO)
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, "moondeck-mascota")
        if monitor:
            GtkLayerShell.set_monitor(self, monitor)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.BOTTOM)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_exclusive_zone(self, -1)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        self.can = ce.Can(ancho, alto, diseno)
        self.dibujo = Dibujo()
        self.poner_diseno(diseno)
        self.area = Gtk.GLArea()
        self.area.set_required_version(3, 3)
        self.area.set_has_alpha(True)
        self.area.set_has_depth_buffer(False)
        self.area.set_size_request(LADO, LADO)
        self.area.connect("realize", self.preparar)
        self.area.connect("render", self.pintar)
        self.area.add_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.BUTTON_PRESS_MASK
                             | Gdk.EventMask.BUTTON_MOTION_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.area.connect("button-press-event", lambda *_: self.can.saltar())
        self.area.connect("motion-notify-event", self.raton)
        self.area.connect("leave-notify-event", lambda *_: setattr(self.can, "raton", None))
        self.add(self.area)
        self.inicio = self.antes = time.monotonic()
        self.fin = self.inicio + segundos if segundos else None
        self.tiempos = []
        self.area.add_tick_callback(self.tic)

    def poner_diseno(self, diseno):
        self.can.diseno = diseno
        self.colores = [*(rgb(c) for c in ce.DISENOS[diseno]["colores"]), OJO, TINTA, LENGUA]

    def preparar(self, area):
        area.make_current()
        if area.get_error():
            raise RuntimeError(area.get_error().message)
        self.dibujo.preparar()
        region = cairo.Region(cairo.RectangleInt(60, 90, 220, 220))
        self.get_window().input_shape_combine_region(region, 0, 0)

    def raton(self, _w, e):
        self.can.raton = (self.can.x + (e.x - LADO / 2) / ESC, self.can.y + (e.y - PIE_Y) / ESC)
        if e.state & Gdk.ModifierType.BUTTON1_MASK and self.al_acariciar:
            self.al_acariciar()

    def tic(self, _w, _reloj):
        ahora = time.monotonic()
        dt = min(ahora - self.antes, .05)
        self.tiempos.append(ahora - self.antes)
        self.antes = ahora
        self.can.avanzar(dt)
        while self.can.eventos:
            tipo, x, y = self.can.eventos.pop()
            if self.al_hacer:
                self.al_hacer(tipo, x, y)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, round(self.can.x - LADO / 2))
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, round(self.can.y - PIE_Y))
        self.area.queue_render()
        if self.fin and ahora > self.fin:
            orden = sorted(self.tiempos[30:])
            print(f"imágenes {len(orden)}, media {sum(orden) / len(orden) * 1000:.1f} ms, "
                  f"p99 {orden[int(len(orden) * .99)] * 1000:.1f} ms, posición {self.can.x:.0f},{self.can.y:.0f}")
            Gtk.main_quit()
        return True

    def pintar(self, area, _ctx):
        t = time.monotonic() - self.inicio
        capsulas, tintes = self.can.capsulas(t, 1 / 60)
        y = PIE_Y - self.can.altura_salto() * ESC
        factor = area.get_scale_factor()
        error = self.dibujo.dibujar(area.get_allocated_width() * factor, area.get_allocated_height() * factor,
                                    (LADO / 2 * factor, y * factor), ESC * factor, ce.CAMARA, capsulas, tintes, self.colores)
        if error:
            print("Error de OpenGL", hex(error), flush=True)
        return True


def main():
    diseno = sys.argv[1] if len(sys.argv) > 1 else "bizcocho"
    segundos = float(sys.argv[2]) if len(sys.argv) > 2 else 0
    g = Gdk.Display.get_default().get_monitor(0).get_geometry()
    v = VentanaCan(diseno, g.width, g.height, segundos)
    v.connect("destroy", Gtk.main_quit)
    v.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
