"""Dibuja las cápsulas de can_esqueleto en la GPU: trazado de rayos sobre una superficie suave.

OpenGL por ctypes, sin dependencias: el código no sabe qué es un perro, solo recibe cápsulas,
tintes y colores. Si un día hay miles de píxeles que no llegan, aquí se cambia el dibujo sin
tocar el esqueleto.
"""

import ctypes
from ctypes import byref, c_char_p, c_float, c_int, c_uint

MAX_CAPSULAS, MAX_TINTES = 48, 6
gl = ctypes.CDLL("libGL.so.1")
gl.glCreateShader.restype = c_uint
gl.glCreateProgram.restype = c_uint
gl.glGetUniformLocation.restype = c_int
gl.glGetUniformLocation.argtypes = (c_uint, c_char_p)
gl.glGetError.restype = c_uint
gl.glUniform1f.argtypes = (c_int, c_float)
gl.glUniform2f.argtypes = (c_int, c_float, c_float)

VERTICES = b"""#version 330 core
void main() {
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
"""

FRAGMENTOS = b"""#version 330 core
#define N 48
out vec4 color;
uniform vec2 uTam, uPie;
uniform float uEsc, uCamara;
uniform int uN, uNT;
uniform vec4 uA[N], uB[N];
uniform int uMat[N];
uniform vec4 uTinte[6];
uniform int uTinteM[6];
uniform vec3 uColor[7];
uniform vec4 uCaja;

float capsula(vec3 p, vec3 a, vec3 b, float r0, float r1) {
    vec3 ba = b - a;
    float q = dot(ba, ba);
    float t = q > 0.001 ? clamp(dot(p - a, ba) / q, 0.0, 1.0) : 0.0;
    return length(p - a - ba * t) - mix(r0, r1, t);
}
float suave(float a, float b, float k) {
    float h = max(k - abs(a - b), 0.0) / k;
    return min(a, b) - h * h * k * 0.25;
}
float mapa(vec3 p) {
    float piel = 1e5, detalle = 1e5;
    for (int i = 0; i < uN; i++) {
        float d = capsula(p, uA[i].xyz, uB[i].xyz, uA[i].w, uB[i].w);
        if (uMat[i] >= 4) detalle = min(detalle, d);
        else piel = suave(piel, d, 11.0);
    }
    return min(piel, detalle);
}
vec3 normal(vec3 p) {
    vec2 e = vec2(0.6, -0.6);
    return normalize(e.xyy * mapa(p + e.xyy) + e.yyx * mapa(p + e.yyx) + e.yxy * mapa(p + e.yxy) + e.xxx * mapa(p + e.xxx));
}
vec3 tono(vec3 p, out int mat) {
    float mejor = 1e5, pesos = 0.0;
    vec3 suma = vec3(0.0);
    mat = 0;
    for (int i = 0; i < uN; i++) {
        float d = capsula(p, uA[i].xyz, uB[i].xyz, uA[i].w, uB[i].w);
        if (d < mejor) { mejor = d; mat = uMat[i]; }
        if (uMat[i] < 4) { float w = exp(-max(d, 0.0) * 0.45 - abs(d) * 0.3); suma += uColor[uMat[i]] * w; pesos += w; }
    }
    if (mat >= 4) return uColor[mat];
    vec3 c = suma / max(pesos, 0.001);
    if (mat == 0) for (int i = 0; i < uNT; i++) {
        float k = 1.0 - smoothstep(uTinte[i].w - 2.0, uTinte[i].w + 2.0, distance(p, uTinte[i].xyz));
        c = mix(c, uColor[uTinteM[i]], k);
    }
    return c;
}
void main() {
    vec2 q = vec2(gl_FragCoord.x, uTam.y - gl_FragCoord.y) - uPie;
    q /= uEsc;
    vec3 dir = normalize(vec3(0.0, uCamara, -1.0));
    vec3 ro = vec3(q, 0.0) - dir * 320.0;
    float cerca = length(cross(uCaja.xyz - ro, dir));
    color = vec4(0.0);
    if (cerca > uCaja.w) return;
    float t = 0.0, minimo = 1e5;
    bool hay = false;
    for (int i = 0; i < 56 && t < 640.0; i++) {
        float d = mapa(ro + dir * t);
        minimo = min(minimo, d);
        if (d < 0.25) { hay = true; break; }
        t += d;
    }
    float borde = 2.4 / uEsc;
    if (!hay) {
        float a = 1.0 - smoothstep(borde - 0.6, borde + 0.6, minimo);
        color = vec4(vec3(0.17, 0.12, 0.1) * a, a);
        return;
    }
    vec3 p = ro + dir * t, n = normal(p);
    int mat;
    vec3 base = tono(p, mat);
    vec3 luz = normalize(vec3(-0.45, -0.75, 0.6));
    float dl = dot(n, luz);
    float banda = mix(0.74, 1.0, smoothstep(-0.02, 0.1, dl)) + 0.07 * smoothstep(0.62, 0.74, dl);
    vec3 c = base * banda;
    float frente = max(dot(n, -dir), 0.0);
    if (mat == 4) {
        float brillo = pow(max(dot(n, normalize(luz - dir)), 0.0), 90.0);
        c = base + vec3(0.72) * brillo;
    } else c = mix(vec3(0.17, 0.12, 0.1), c, smoothstep(0.1, 0.3, frente));
    color = vec4(c, 1.0);
}
"""


class Dibujo:
    def preparar(self):
        self.vao = c_uint()
        gl.glGenVertexArrays(1, byref(self.vao))
        self.prog = gl.glCreateProgram()
        for tipo, fuente in ((0x8B31, VERTICES), (0x8B30, FRAGMENTOS)):
            s = gl.glCreateShader(tipo)
            gl.glShaderSource(s, 1, byref(c_char_p(fuente)), None)
            gl.glCompileShader(s)
            ok = c_int()
            gl.glGetShaderiv(s, 0x8B81, byref(ok))
            if not ok.value:
                raz = ctypes.create_string_buffer(4096)
                gl.glGetShaderInfoLog(s, 4096, None, raz)
                raise RuntimeError(raz.value.decode())
            gl.glAttachShader(self.prog, s)
        gl.glLinkProgram(self.prog)
        ok = c_int()
        gl.glGetProgramiv(self.prog, 0x8B82, byref(ok))
        if not ok.value:
            raise RuntimeError("No se pudo enlazar el shader")
        self.u = {n: gl.glGetUniformLocation(self.prog, n.encode()) for n in (
            "uTam", "uPie", "uEsc", "uCamara", "uN", "uNT", "uA", "uB", "uMat", "uTinte", "uTinteM", "uColor", "uCaja")}

    def dibujar(self, ancho, alto, pie, esc, camara, capsulas, tintes, colores):
        gl.glViewport(0, 0, ancho, alto)
        gl.glClearColor(c_float(0), c_float(0), c_float(0), c_float(0))
        gl.glClear(0x4000)
        n = min(len(capsulas), MAX_CAPSULAS)
        a, b, m = (c_float * (4 * n))(), (c_float * (4 * n))(), (c_int * n)()
        minimo, maximo = [1e9] * 3, [-1e9] * 3
        for i, (p, q, r0, r1, mat) in enumerate(capsulas[:n]):
            a[4 * i:4 * i + 4] = (*p, r0)
            b[4 * i:4 * i + 4] = (*q, r1)
            m[i] = mat
            for j in range(3):
                minimo[j] = min(minimo[j], p[j] - r0, q[j] - r1)
                maximo[j] = max(maximo[j], p[j] + r0, q[j] + r1)
        centro = [(x + y) / 2 for x, y in zip(minimo, maximo)]
        radio = sum((y - x) ** 2 for x, y in zip(minimo, maximo)) ** .5 / 2 + 8
        t, tm = (c_float * 24)(), (c_int * 6)()
        for i, (p, r, mat) in enumerate(tintes[:MAX_TINTES]):
            t[4 * i:4 * i + 4] = (*p, r)
            tm[i] = mat
        col = (c_float * 21)(*[x for c in colores for x in c])
        u = self.u
        gl.glUseProgram(self.prog)
        gl.glUniform2f(u["uTam"], ancho, alto)
        gl.glUniform2f(u["uPie"], *pie)
        gl.glUniform1f(u["uEsc"], esc)
        gl.glUniform1f(u["uCamara"], camara)
        gl.glUniform1i(u["uN"], n)
        gl.glUniform1i(u["uNT"], min(len(tintes), MAX_TINTES))
        gl.glUniform4fv(u["uA"], n, a)
        gl.glUniform4fv(u["uB"], n, b)
        gl.glUniform1iv(u["uMat"], n, m)
        gl.glUniform4fv(u["uTinte"], 6, t)
        gl.glUniform1iv(u["uTinteM"], 6, tm)
        gl.glUniform3fv(u["uColor"], 7, col)
        gl.glUniform4f(u["uCaja"], c_float(centro[0]), c_float(centro[1]), c_float(centro[2]), c_float(radio))
        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(4, 0, 3)
        return gl.glGetError()
