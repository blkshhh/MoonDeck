"""Perros de escritorio: esqueleto, comportamiento y diseños (sin dibujo ni ventanas).

Todo sale de aquí como una lista de cápsulas 3D en coordenadas de vista, y quien dibuja no sabe
nada de perros. Para añadir una raza basta una entrada en DISENOS; para una acción, un peso en
Can.pesos y su efecto en posar. Coordenadas: x adelante, y abajo, z a la derecha del perro.
"""

import math
import random

CAMARA = 0.36  # lo que se mira desde arriba

# Materiales (los mismos índices en el shader). Desde OJO son detalles: no se funden con la piel.
PIEL, CLARO, MANCHA, OREJA, OJO, TINTA, LENGUA = range(7)
ZANCADA, LEVANTA = 26, 20
LADOS, FASES = (1, -1, 1, -1), (0, .5, .25, .75)
POSES = {
    "pie": ((-58, -78), (58, -84), .55, ((-58, 0), (-58, 0), (60, 0), (60, 0))),
    "sentado": ((-48, -42), (38, -106), .22, ((-18, 0), (-18, 0), (48, 0), (48, 0))),
    "tumbado": ((-66, -40), (52, -42), .95, ((-10, 0), (-10, 0), (98, 0), (98, 0))),
}
DISENOS = {
    "bizcocho": dict(nombre="Bizcocho", patas=1, largo=1, torso=46, cabeza=54, hocico=1, oreja="caida", cola=1,
                     colores=("#f6e2c2", "#fff4e0", "#eebd84", "#c98a52")),
    "tizon": dict(nombre="Tizón", patas=1.22, largo=1.08, torso=39, cabeza=45, hocico=1.55, oreja="tiesa", cola=.85,
                  colores=("#57504f", "#c98d57", "#3f3a3b", "#494344")),
    "morro": dict(nombre="Morro", patas=.86, largo=.94, torso=53, cabeza=52, hocico=.86, oreja="doblada", cola=.45,
                  colores=("#a9744a", "#f3e7d6", "#f3e7d6", "#6f4728")),
}


def _lerp(a, b, k):
    return a + (b - a) * k


def _mez(a, b, k):
    return tuple(_lerp(x, y, k) for x, y in zip(a, b))


def _clamp(v, a, b):
    return max(a, min(b, v))


def _girar(q, a):
    co, se = math.cos(a), math.sin(a)
    return q[0] * co - q[2] * se, q[1], q[0] * se + q[2] * co


def _ik(a, b, l1, l2, doblez):
    dx, dy = b[0] - a[0], b[1] - a[1]
    real = max(math.hypot(dx, dy), 1)
    d = _clamp(real, 1, l1 + l2 - .5)
    k = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(0, l1 * l1 - k * k))
    ux, uy = dx / real, dy / real
    return a[0] + ux * k - uy * h * doblez, a[1] + uy * k + ux * h * doblez, (a[2] + b[2]) / 2


class Resorte:
    """Inercia: sigue a su objetivo con retraso."""

    def __init__(self, k, d):
        self.a, self.v, self.k, self.d = 0.0, 0.0, k, d

    def ir(self, objetivo, dt):
        self.v += (self.k * (objetivo - self.a) - self.d * self.v) * dt
        self.a += self.v * dt


class Can:
    def __init__(self, ancho, alto, diseno="bizcocho"):
        self.ancho, self.alto, self.diseno = ancho, alto, diseno
        self.x, self.y = ancho * .4, alto * .6
        self.destino = (self.x, self.y)
        self.yaw, self.fase, self.espera = .4, 0.0, 1.0
        self.accion = "pie"
        self.pesos = dict(sentado=0.0, tumbado=0.0, andar=0.0, sacude=0.0, pis=0.0, patita=0.0)
        self.salto = -1.0
        self.raton = None  # (x, y) en pantalla, si está sobre la mascota
        self.orejas = [Resorte(130, 9), Resorte(130, 9)]
        self.cola = [Resorte(120 - i * 18, 8) for i in range(4)]
        self.alto_cab = None

    def saltar(self):
        if self.salto < 0:
            self.salto = 0.0

    def avanzar(self, dt):
        w = self.pesos
        dx, dy = self.destino[0] - self.x, self.destino[1] - self.y
        dist = math.hypot(dx, dy)
        anda = dist > 6
        accion = self.accion
        objetivos = dict(sentado=accion in ("sentado", "patita"), tumbado=accion == "tumbado", sacude=accion == "sacude",
                         pis=accion == "pis", patita=accion == "patita")
        for clave, si in objetivos.items():
            w[clave] += ((1 if si and not anda else 0) - w[clave]) * min(1, dt * 6)
        w["andar"] += ((1 if anda else 0) - w["andar"]) * min(1, dt * 8)
        objetivo = self.yaw
        if anda:
            v = min(dist, 76 * dt * _clamp(1 - w["sentado"] - w["tumbado"], .1, 1))
            self.x += dx / dist * v
            self.y += dy / dist * v
            self.fase += dt * 1.55
            objetivo = math.atan2(dy * 1.7, dx)
        elif accion == "patita":
            objetivo = math.pi / 2 - .3
        dif = math.atan2(math.sin(objetivo - self.yaw), math.cos(objetivo - self.yaw))
        self.yaw += dif * min(1, dt * 7)
        if self.salto >= 0:
            self.salto += dt / .7
            if self.salto >= 1:
                self.salto = -1.0
        self.espera -= dt
        if self.espera <= 0 and not anda:
            self.decidir()

    def decidir(self):
        r = random.random()
        self.accion = ("pie" if r < .5 else "sentado" if r < .68 else "tumbado" if r < .82 else
                       "sacude" if r < .92 else "patita")
        if random.random() < .2:
            self.saltar()
        if r < .5:
            self.destino = (random.uniform(120, self.ancho - 120), random.uniform(160, self.alto - 60))
        self.espera = 1.3 if self.accion == "sacude" else random.uniform(2.5, 6)

    def altura_salto(self):
        return math.sin(self.salto * math.pi) * 95 if self.salto >= 0 else 0.0

    def capsulas(self, t, dt):
        """[(a, b, r0, r1, material)] en vista: x derecha, y abajo, z hacia quien mira."""
        D, w = DISENOS[self.diseno], self.pesos
        s, l = _clamp(w["sentado"], 0, 1), _clamp(w["tumbado"], 0, 1)
        k, R, r = D["patas"], D["cabeza"], D["torso"]

        def pos(i):
            a, b, d = (POSES[n][i] for n in ("pie", "sentado", "tumbado"))
            q = _mez(_mez(a, b, s), d, l)
            return [q[0] * D["largo"], q[1] * k, 0.0]

        respira = math.sin(t * (1.4 if l > .7 else 2.6)) * (2.4 if l > .7 else 1.4)
        paso = math.sin(self.fase * math.pi * 4) * 2.6 * w["andar"]
        sacude = math.sin(t * 40) * w["sacude"]
        cadera, hombro = pos(0), pos(1)
        cadera[1] += paso + respira * .5 + w["pis"] * 4
        hombro[1] += -paso * .6 + respira + w["pis"] * 3
        cadera[2], hombro[2] = sacude * 10, -sacude * 12
        encoge = math.sin(self.salto * math.pi) * 18 if self.salto >= 0 else 0
        pies = []
        for i in range(4):
            a, b, d = (POSES[n][3][i] for n in ("pie", "sentado", "tumbado"))
            q = _mez(_mez(a, b, s), d, l)
            q = [q[0] * D["largo"], q[1] * k, LADOS[i] * r * .5]
            f = (self.fase + FASES[i]) % 1
            if w["andar"] > .01:
                nube = f / .36 if f < .36 else 0
                q[0] += (-1 + 2 * nube if f < .36 else 1 - 2 * (f - .36) / .64) * ZANCADA * w["andar"]
                q[1] -= math.sin(nube * math.pi) * LEVANTA * w["andar"]
            q[1] -= encoge
            q[0] += (-1 if i < 2 else 1) * encoge * .5
            pies.append(tuple(q))
        pies[0] = _mez(pies[0], (cadera[0] - 42, -62 * k, r + 16), w["pis"])
        pies[2] = _mez(pies[2], (hombro[0] + 44, hombro[1] + 14 + math.sin(t * 6) * 4, r * .5), w["patita"])
        raices = [(cadera[0] - 4, cadera[1] + 20, LADOS[i] * r * .5) if i < 2 else (hombro[0], hombro[1] + 22, LADOS[i] * r * .5)
                  for i in range(4)]
        rodillas = [_ik(raices[i], pies[i], 35 * k, 35 * k, -1 if i < 2 else 1) for i in range(4)]

        cuello = _lerp(_lerp(POSES["pie"][2], POSES["sentado"][2], s), POSES["tumbado"][2], l) + sacude * .05
        n0 = (hombro[0] + 16, hombro[1] - 14, 0.0)
        n1 = (n0[0] + math.sin(cuello) * 46, n0[1] - math.cos(cuello) * 46, 0.0)
        cab = (n1[0] + 8, n1[1] - 8, 0.0)
        h_yaw, h_pitch = sacude * .55, .2 if l > .7 else 0.0
        if self.raton:
            vista = _girar(cab, self.yaw)
            mx, my = self.raton[0] - self.x - vista[0], self.raton[1] - self.y - vista[1] - vista[2] * CAMARA
            hacia = math.atan2(my * 1.7, mx) - self.yaw
            hacia = math.atan2(math.sin(hacia), math.cos(hacia))
            h_yaw += _clamp(hacia, -.85, .85) * (.25 if abs(hacia) > 2.2 else .8)
            h_pitch = _clamp(my / 300, -.3, .28)

        def en_cabeza(q):
            x = q[0] * math.cos(h_pitch) - q[1] * math.sin(h_pitch)
            y = q[0] * math.sin(h_pitch) + q[1] * math.cos(h_pitch)
            g = _girar((x, y, q[2]), h_yaw)
            return cab[0] + g[0], cab[1] + g[1], g[2]

        antes = self.alto_cab if self.alto_cab is not None else cab[1]
        self.alto_cab = cab[1]
        tiron = (cab[1] - antes) / max(dt, .001) * .5 + (40 if w["andar"] > .3 else 0) + sacude * 90
        for e in self.orejas:
            e.ir(_clamp(-tiron * .009, -.9, .9), dt)
        meneo = 0 if w["sacude"] > .1 else math.sin(t * (3 if l > .7 else 11)) * (.12 if l > .7 else .5)
        for i, m in enumerate(self.cola):
            m.ir(meneo * (1 + i * .3) - sacude * .5, dt)

        lista = []

        def cap(a, b, r0, r1, mat=PIEL):
            lista.append((_girar(a, self.yaw), _girar(b, self.yaw), r0, r1, mat))

        medio = (*(_lerp(a, b, .5) for a, b in zip(cadera[:2], hombro[:2])), 0.0)
        cap(cadera, medio, r, r + 1)
        cap(medio, hombro, r + 1, r)
        cap(n0, n1, r * .82, r * .68)
        g = r / 46
        for i in range(4):
            cap(raices[i], rodillas[i], 23 * g, 17 * g)
            cap(rodillas[i], (pies[i][0], pies[i][1] - 9, pies[i][2]), 17 * g, 14 * g)
            cap((pies[i][0] - 3, pies[i][1] - 9, pies[i][2]), (pies[i][0] + 7, pies[i][1] - 10, pies[i][2]), 13 * g, 15 * g)
        q = (cadera[0] - r * .78, cadera[1] - 18, 0.0)
        if D["cola"] < .6:
            cap(q, (q[0] - 18, q[1] - 16, self.cola[0].a * 14), 12, 9, OREJA)
        else:
            for i, m in enumerate(self.cola):
                e, largo = .85 + i * .3, 20 * D["cola"]
                n = (q[0] - math.cos(e) * largo, q[1] - math.sin(e) * largo, q[2] + m.a * largo * .7)
                cap(q, n, (15 - i * 1.6) * D["cola"], (13.4 - i * 1.6) * D["cola"], MANCHA)
                q = n

        cap(cab, cab, R, R)
        for z in (-1, 1):
            c = en_cabeza((6, R * .22, z * R * .42))
            cap(c, c, R * .68, R * .68)
        hoc = R * (.78 + .34 * (D["hocico"] - 1) + .2)
        cap(en_cabeza((R * .72, R * .26, 0)), en_cabeza((hoc, R * .3, 0)), R * .47, R * .38, CLARO)
        punta = hoc + R * .36
        for i, lado in enumerate((1, -1)):
            raiz = (-R * .34, -R * .6, lado * R * .78)
            a, largo = self.orejas[i].a * .7 + .08, R * .56
            if D["oreja"] == "tiesa":
                m = (raiz[0] - 3, raiz[1] - largo * .8, raiz[2] + lado * 3)
                f = (m[0] - 2 + a * 7, m[1] - largo * .72, m[2] + lado * 2)
                radios = 15, 12, 5
            elif D["oreja"] == "doblada":
                m = (raiz[0] + 4, raiz[1] - largo * .3, raiz[2] + lado * 9)
                f = (m[0] + 12 + a * 8, m[1] + largo * .36, m[2] + lado * 3)
                radios = 13, 13, 9
            else:
                m = (raiz[0] + math.sin(a) * largo, raiz[1] + math.cos(a) * largo, raiz[2] + lado * 5)
                f = (m[0] + math.sin(a * 2) * largo, m[1] + math.cos(a * 2) * largo, m[2] + lado * 3)
                radios = 15, 21, 16
            cap(en_cabeza(raiz), en_cabeza(m), radios[0], radios[1], OREJA)
            cap(en_cabeza(m), en_cabeza(f), radios[1], radios[2], OREJA)

        cerrado = l > .7 or math.floor(t * 10) % 47 < 2
        for z in (-1, 1):
            c = en_cabeza((R * .86, -R * .08, z * R * .46))
            if cerrado:
                cap(en_cabeza((R * .9, -R * .08, z * R * .32)), en_cabeza((R * .9, -R * .08, z * R * .6)), 1.8, 1.8, TINTA)
            else:
                cap(c, c, R * .17, R * .17, OJO)
        n = en_cabeza((punta * .97, R * .16, 0))
        cap(n, n, R * .16, R * .16, OJO)
        boca = en_cabeza((punta * .93, R * .56, 0))
        cap(n, boca, 1.5, 1.5, TINTA)
        cap(boca, en_cabeza((punta * .8, R * .6, R * .26)), 1.6, 1.6, TINTA)
        cap(boca, en_cabeza((punta * .8, R * .6, -R * .26)), 1.6, 1.6, TINTA)
        if w["andar"] > .5 or w["sacude"] > .3:
            cap(en_cabeza((punta * .8, R * .6, 0)), en_cabeza((punta * .84, R * (.86 + math.sin(t * 16) * .05), 0)), 7, 8, LENGUA)

        # Manchas de color sobre la piel: esferas que solo tiñen
        cruz = _girar((cadera[0] - 6, cadera[1] - r * .75, 0), self.yaw)
        panza = _girar((medio[0] + 14, medio[1] + r * 1.05, 0), self.yaw)
        pecho = _girar((hombro[0] + r * .9, hombro[1] + 10, 0), self.yaw)
        coronilla = en_cabeza((-R * .15, -R * .8, 0))
        tintes = [(cruz, r * .92, MANCHA), (panza, r * .78, CLARO), (pecho, r * .6, CLARO), (coronilla, R * .55, MANCHA)]
        return lista, tintes
