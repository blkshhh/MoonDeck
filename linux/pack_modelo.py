"""Pack Modelo 3D (Linux): de decoración, un modelo .glb tal cual (sus puntos, sus colores y su
animación) girando despacio. Se arrastra con el ratón para verlo desde otro lado.

Se pinta con OpenGL (Gtk.GLArea), llamando a la librería del sistema con ctypes: no hace falta
instalar nada. Los modelos van en ~/.config/MoonDeck/modelos (o el que se elija con el clic derecho).
"""

import ctypes
import glob
import math

from __main__ import *  # noqa: F403 - las piezas de monitor.py (Tarjeta, etiqueta, log...)
import __main__ as M  # noqa: F401
import modelo_glb
from idioma import _

WIDGETS = ('modelo3d',)
MODELOS = os.path.join(CARPETA, "modelos")

GL_FLOAT, GL_ARRAY_BUFFER, GL_ELEMENT_ARRAY_BUFFER, GL_STATIC_DRAW = 0x1406, 0x8892, 0x8893, 0x88E4
GL_VERTEX_SHADER, GL_FRAGMENT_SHADER, GL_COMPILE_STATUS, GL_LINK_STATUS = 0x8B31, 0x8B30, 0x8B81, 0x8B82
GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST, GL_PROGRAM_POINT_SIZE = 0x4000, 0x0100, 0x0B71, 0x8642

VERTICES = """#version 330 core
layout(location = 0) in vec3 posicion;
layout(location = 1) in vec4 color;
uniform mat4 mvp;
uniform float punto;
out vec4 c;
void main() {
    gl_Position = mvp * vec4(posicion, 1.0);
    gl_PointSize = punto;
    c = color;
}
"""
# Los colores de glTF son lineales: a sRGB para la pantalla (sin luces: el modelo es «unlit»).
FRAGMENTOS = """#version 330 core
in vec4 c;
out vec4 salida;
void main() {
    vec3 s = mix(c.rgb * 12.92, 1.055 * pow(c.rgb, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c.rgb));
    salida = vec4(s * c.a, c.a);
}
"""


class GL:
    """Las funciones de OpenGL que hacen falta, sacadas de libOpenGL (la de glvnd, vale para EGL y GLX)."""

    FIRMAS = {
        "glViewport": (None, [ctypes.c_int] * 4),
        "glClearColor": (None, [ctypes.c_float] * 4),
        "glClear": (None, [ctypes.c_uint]),
        "glEnable": (None, [ctypes.c_uint]),
        "glCreateShader": (ctypes.c_uint, [ctypes.c_uint]),
        "glShaderSource": (None, [ctypes.c_uint, ctypes.c_int, ctypes.POINTER(ctypes.c_char_p), ctypes.c_void_p]),
        "glCompileShader": (None, [ctypes.c_uint]),
        "glGetShaderiv": (None, [ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_int)]),
        "glGetShaderInfoLog": (None, [ctypes.c_uint, ctypes.c_int, ctypes.c_void_p, ctypes.c_char_p]),
        "glCreateProgram": (ctypes.c_uint, []),
        "glAttachShader": (None, [ctypes.c_uint, ctypes.c_uint]),
        "glLinkProgram": (None, [ctypes.c_uint]),
        "glGetProgramiv": (None, [ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_int)]),
        "glGetProgramInfoLog": (None, [ctypes.c_uint, ctypes.c_int, ctypes.c_void_p, ctypes.c_char_p]),
        "glDeleteShader": (None, [ctypes.c_uint]),
        "glDeleteProgram": (None, [ctypes.c_uint]),
        "glUseProgram": (None, [ctypes.c_uint]),
        "glGetUniformLocation": (ctypes.c_int, [ctypes.c_uint, ctypes.c_char_p]),
        "glUniformMatrix4fv": (None, [ctypes.c_int, ctypes.c_int, ctypes.c_ubyte, ctypes.POINTER(ctypes.c_float)]),
        "glUniform1f": (None, [ctypes.c_int, ctypes.c_float]),
        "glGenVertexArrays": (None, [ctypes.c_int, ctypes.POINTER(ctypes.c_uint)]),
        "glBindVertexArray": (None, [ctypes.c_uint]),
        "glDeleteVertexArrays": (None, [ctypes.c_int, ctypes.POINTER(ctypes.c_uint)]),
        "glGenBuffers": (None, [ctypes.c_int, ctypes.POINTER(ctypes.c_uint)]),
        "glBindBuffer": (None, [ctypes.c_uint, ctypes.c_uint]),
        "glBufferData": (None, [ctypes.c_uint, ctypes.c_ssize_t, ctypes.c_char_p, ctypes.c_uint]),
        "glDeleteBuffers": (None, [ctypes.c_int, ctypes.POINTER(ctypes.c_uint)]),
        "glVertexAttribPointer": (None, [ctypes.c_uint, ctypes.c_int, ctypes.c_uint, ctypes.c_ubyte, ctypes.c_int,
                                         ctypes.c_void_p]),
        "glEnableVertexAttribArray": (None, [ctypes.c_uint]),
        "glDisableVertexAttribArray": (None, [ctypes.c_uint]),
        "glVertexAttrib4f": (None, [ctypes.c_uint] + [ctypes.c_float] * 4),
        "glDrawArrays": (None, [ctypes.c_uint, ctypes.c_int, ctypes.c_int]),
        "glDrawElements": (None, [ctypes.c_uint, ctypes.c_int, ctypes.c_uint, ctypes.c_void_p]),
    }

    def __init__(self):
        lib = ctypes.CDLL("libOpenGL.so.0")
        for nombre, (devuelve, argumentos) in self.FIRMAS.items():
            fn = getattr(lib, nombre)
            fn.restype, fn.argtypes = devuelve, argumentos
            setattr(self, nombre[2:], fn)


def _sombreador(gl, tipo, fuente):
    s = gl.CreateShader(tipo)
    texto = ctypes.c_char_p(fuente.encode())
    gl.ShaderSource(s, 1, ctypes.byref(texto), None)
    gl.CompileShader(s)
    ok = ctypes.c_int()
    gl.GetShaderiv(s, GL_COMPILE_STATUS, ctypes.byref(ok))
    if not ok.value:
        error = ctypes.create_string_buffer(2048)
        gl.GetShaderInfoLog(s, 2048, None, error)
        raise RuntimeError(error.value.decode(errors="replace"))
    return s


def _perspectiva(fov, aspecto, cerca, lejos):
    f = 1 / math.tan(fov / 2)
    return (f / aspecto, 0, 0, 0, 0, f, 0, 0, 0, 0, (lejos + cerca) / (cerca - lejos), -1,
            0, 0, 2 * lejos * cerca / (cerca - lejos), 0)


def _giro(angulo, eje):
    c, s = math.cos(angulo), math.sin(angulo)
    if eje == "y":
        return (c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1)
    return (1, 0, 0, 0, 0, c, s, 0, 0, -s, c, 0, 0, 0, 0, 1)


class VistaModelo(Gtk.GLArea):
    """El modelo girando. Arrastrar lo gira a mano; al soltarlo sigue solo desde ahí."""

    VELOCIDAD = 0.25  # radianes por segundo

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.cfg = app.config.setdefault("modelo3d", {})
        self.set_has_alpha(True)
        self.set_has_depth_buffer(True)
        self.set_required_version(3, 3)
        self.set_size_request(-1, 120)
        self.set_vexpand(True)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK
                        | Gdk.EventMask.POINTER_MOTION_MASK)
        self.gl = None
        self.modelo = None
        self.error = None
        self._subido = None      # (vao, buffers, programa, uniformes) del modelo cargado en la gráfica
        self._timer = None
        self._inicio = time.monotonic()
        self._antes = self._inicio
        self.guinada = 0.0
        self.cabeceo = 0.25
        self.girar = self.cfg.get("girar", True)
        self._arrastre = None
        self.connect("realize", self._preparar)
        self.connect("unrealize", self._soltar_gl)
        self.connect("render", self._pintar)
        self.connect("map", lambda _w: self._programar())
        self.connect("unmap", lambda _w: self._parar())
        self.connect("button-press-event", self._pulsar)
        self.connect("button-release-event", self._soltar)
        self.connect("motion-notify-event", self._mover)
        self.cargar(self.cfg.get("ruta") or next(iter(sorted(glob.glob(os.path.join(MODELOS, "*.glb")))), None))

    def cargar(self, ruta):
        self.modelo, self.error = None, None
        if not ruta:
            self.error = _("Elige un modelo .glb con el clic derecho.")
        else:
            try:
                self.modelo = modelo_glb.Modelo(ruta)
                self.cfg["ruta"] = ruta
            except Exception as e:  # noqa: BLE001 - archivo roto, otro formato...
                log(f"No se pudo abrir el modelo {ruta}: {e}")
                self.error = _("No se pudo abrir el modelo.")
        if self.modelo:
            m = self.modelo
            texto = " · ".join(x for x in (m.titulo, m.autor.split(" (")[0], m.licencia.split(" (")[0]) if x)
            self.set_tooltip_text(texto or os.path.basename(ruta))
        else:
            self.set_tooltip_text(self.error)
        self._inicio = time.monotonic()
        if self.get_realized():
            self.make_current()
            self._soltar_gl()
            self._subir()
        self.queue_render()

    # --- OpenGL ---

    def _preparar(self, _w):
        self.make_current()
        if self.get_error():
            log("Modelo 3D: sin OpenGL:", self.get_error().message)
            return
        try:
            self.gl = GL()
            self._subir()
        except Exception as e:  # noqa: BLE001 - sin libOpenGL, sombreador que no compila...
            log(f"Modelo 3D: no se pudo preparar OpenGL: {e}")
            self.gl = None

    def _subir(self):
        """Sube a la gráfica los datos del modelo (una vez) y compila los sombreadores."""
        gl, m = self.gl, self.modelo
        if not gl or not m:
            return
        vs, fs = _sombreador(gl, GL_VERTEX_SHADER, VERTICES), _sombreador(gl, GL_FRAGMENT_SHADER, FRAGMENTOS)
        prog = gl.CreateProgram()
        gl.AttachShader(prog, vs)
        gl.AttachShader(prog, fs)
        gl.LinkProgram(prog)
        gl.DeleteShader(vs)
        gl.DeleteShader(fs)
        ok = ctypes.c_int()
        gl.GetProgramiv(prog, GL_LINK_STATUS, ctypes.byref(ok))
        if not ok.value:
            error = ctypes.create_string_buffer(2048)
            gl.GetProgramInfoLog(prog, 2048, None, error)
            raise RuntimeError(error.value.decode(errors="replace"))
        vao = ctypes.c_uint()
        gl.GenVertexArrays(1, ctypes.byref(vao))
        gl.BindVertexArray(vao)
        usados = {a[0] for prims in m.primitivas.values() for p in prims for a in p[1].values()}
        usados |= {p[2][0] for prims in m.primitivas.values() for p in prims if p[2]}
        buffers = {}
        for bv in usados:
            b = ctypes.c_uint()
            gl.GenBuffers(1, ctypes.byref(b))
            gl.BindBuffer(GL_ARRAY_BUFFER, b)
            datos = bytes(m.buffers[bv])
            gl.BufferData(GL_ARRAY_BUFFER, len(datos), datos, GL_STATIC_DRAW)
            buffers[bv] = b.value
        gl.BindVertexArray(0)
        self._subido = (vao.value, buffers, prog, gl.GetUniformLocation(prog, b"mvp"),
                        gl.GetUniformLocation(prog, b"punto"))

    def _soltar_gl(self, *_a):
        if not self._subido or not self.gl:
            self._subido = None
            return
        gl = self.gl
        vao, buffers, prog, *_u = self._subido
        if self.get_realized():
            self.make_current()
        gl.DeleteVertexArrays(1, ctypes.byref(ctypes.c_uint(vao)))
        for b in buffers.values():
            gl.DeleteBuffers(1, ctypes.byref(ctypes.c_uint(b)))
        gl.DeleteProgram(prog)
        self._subido = None

    def _pintar(self, _w, _ctx):
        gl = self.gl
        if not gl:
            return True
        escala = self.get_scale_factor()
        ancho, alto = self.get_allocated_width() * escala, self.get_allocated_height() * escala
        gl.Viewport(0, 0, ancho, alto)
        gl.ClearColor(0, 0, 0, 0)
        gl.Clear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        if not self._subido or not self.modelo:
            return True
        m = self.modelo
        vao, buffers, prog, u_mvp, u_punto = self._subido
        gl.Enable(GL_DEPTH_TEST)
        gl.Enable(GL_PROGRAM_POINT_SIZE)
        gl.UseProgram(prog)
        gl.BindVertexArray(vao)
        # Cámara: encuadra el modelo entero (su esfera) en el lado corto del widget.
        fov = math.radians(30)
        aspecto = max(1e-3, ancho / max(1, alto))
        distancia = m.radio / math.sin(fov / 2) * (1.0 if aspecto >= 1 else 1 / aspecto) * 1.02
        cx, cy, cz = m.centro
        vista = modelo_glb.multiplica(
            (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, -distancia, 1),
            modelo_glb.multiplica(_giro(self.cabeceo, "x"), modelo_glb.multiplica(
                _giro(self.guinada, "y"), (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -cx, -cy, -cz, 1))))
        pv = modelo_glb.multiplica(_perspectiva(fov, aspecto, distancia - m.radio * 2, distancia + m.radio * 2), vista)
        gl.Uniform1f(u_punto, max(1.0, min(ancho, alto) / 200))  # puntos de unos 1,5 px en un widget normal
        t = (time.monotonic() - self._inicio) % m.duracion if m.duracion else 0.0
        for matriz, (modo, atributos, indices, color, _lim) in m.dibujos(t):
            mvp = (ctypes.c_float * 16)(*modelo_glb.multiplica(pv, matriz))
            gl.UniformMatrix4fv(u_mvp, 1, 0, mvp)
            bv, ini, n, tipo, normal, salto, cuantos = atributos["POSITION"]
            gl.BindBuffer(GL_ARRAY_BUFFER, buffers[bv])
            gl.VertexAttribPointer(0, n, tipo, normal, salto, ini)
            gl.EnableVertexAttribArray(0)
            if "COLOR_0" in atributos:
                bv, ini, n, tipo, normal, salto, _c = atributos["COLOR_0"]
                gl.BindBuffer(GL_ARRAY_BUFFER, buffers[bv])
                gl.VertexAttribPointer(1, n, tipo, normal, salto, ini)
                gl.EnableVertexAttribArray(1)
            else:
                gl.DisableVertexAttribArray(1)
                gl.VertexAttrib4f(1, *color)
            if indices:
                bv, ini, _n, tipo, _norm, _s, cuantos_i = indices
                gl.BindBuffer(GL_ELEMENT_ARRAY_BUFFER, buffers[bv])
                gl.DrawElements(modo, cuantos_i, tipo, ini)
            else:
                gl.DrawArrays(modo, 0, cuantos)
        gl.BindVertexArray(0)
        return True

    # --- movimiento ---

    def _programar(self):
        if self._timer is None and self.get_mapped():
            self._antes = time.monotonic()
            self._timer = GLib.timeout_add(33, self._frame)  # 30 por segundo, como la animación

    def _parar(self):
        if self._timer is not None:
            GLib.source_remove(self._timer)
            self._timer = None

    def _frame(self):
        ahora = time.monotonic()
        if self.girar and not self._arrastre:
            self.guinada = (self.guinada + self.VELOCIDAD * (ahora - self._antes)) % (2 * math.pi)
        self._antes = ahora
        self.queue_render()
        return True

    def _pulsar(self, _w, ev):
        tarjeta = self.get_ancestor(Tarjeta)
        if ev.button != 1 or (tarjeta and tarjeta.en_edicion()):
            return False  # el derecho abre el menú de la tarjeta
        self._arrastre = (ev.x, ev.y, self.guinada, self.cabeceo)
        return True

    def _soltar(self, _w, ev):
        if ev.button == 1 and self._arrastre:
            self._arrastre = None
            return True
        return False

    def _mover(self, _w, ev):
        if not self._arrastre:
            return False
        x, y, g, c = self._arrastre
        self.guinada = g + (ev.x - x) * 0.01
        self.cabeceo = max(-1.5, min(1.5, c + (ev.y - y) * 0.01))
        self.queue_render()
        return True


def iniciar(self):
    if not self.config.get("modelo3d_visto"):  # widget nuevo: llega oculto
        self.config.setdefault("ocultos", []).append("modelo3d")
        self.config["modelo3d_visto"] = True


def construir(self, s):
    c = self.tarjeta("modelo3d", "Modelo 3D")
    self.modelo_vista = c.add_w(VistaModelo(self), expand=True)


def menu(self, tarjeta, menu):
    if tarjeta.clave != "modelo3d":
        return
    v = self.modelo_vista

    def elegir():
        d = Gtk.FileChooserDialog(title=_("Elegir modelo…"), action=Gtk.FileChooserAction.OPEN)
        d.add_buttons(_("Cancelar"), Gtk.ResponseType.CANCEL, _("Abrir"), Gtk.ResponseType.ACCEPT)
        filtro = Gtk.FileFilter()
        filtro.set_name("glTF (.glb)")
        filtro.add_pattern("*.glb")
        d.add_filter(filtro)
        if os.path.isdir(MODELOS):
            d.set_current_folder(MODELOS)
        if d.run() == Gtk.ResponseType.ACCEPT:
            v.cargar(d.get_filename())
            self.guardar_config()
        d.destroy()

    def alternar():
        v.girar = v.cfg["girar"] = not v.girar
        self.guardar_config()

    self.item(menu, "Elegir modelo…", elegir)
    self.item(menu, "Girar solo", alternar, v.girar)
    menu.append(Gtk.SeparatorMenuItem())
