"""Lee un modelo .glb (glTF 2.0 binario) para enseñarlo tal cual: sus puntos, líneas o triángulos,
con sus colores de vértice (o el color base del material), la jerarquía de nodos y su animación.

Sin numpy: los datos de los vértices no se tocan aquí, se pasan en crudo a OpenGL (`buffers`).
Las animaciones de Sketchfab por fotogramas (un nodo «sketchfab.timeframe» con un hijo por
fotograma que se enciende escalándolo) se ven como en Sketchfab: un fotograma cada vez.
"""

import json
import math
import struct

COMPONENTES = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
TAMANOS = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}  # byte, ubyte, short, ushort, uint, float
FORMATOS = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
IDENTIDAD = (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)


# --- matrices 4x4 por columnas (como glTF y OpenGL) ---------------------------------------------------

def multiplica(a, b):
    return tuple(sum(a[k * 4 + f] * b[c * 4 + k] for k in range(4)) for c in range(4) for f in range(4))


def trs(t, r, s):
    x, y, z, w = r
    sx, sy, sz = s
    return ((1 - 2 * (y * y + z * z)) * sx, 2 * (x * y + z * w) * sx, 2 * (x * z - y * w) * sx, 0.0,
            2 * (x * y - z * w) * sy, (1 - 2 * (x * x + z * z)) * sy, 2 * (y * z + x * w) * sy, 0.0,
            2 * (x * z + y * w) * sz, 2 * (y * z - x * w) * sz, (1 - 2 * (x * x + y * y)) * sz, 0.0,
            t[0], t[1], t[2], 1.0)


def aplica(m, p):
    x, y, z = p
    return tuple(m[f] * x + m[4 + f] * y + m[8 + f] * z + m[12 + f] for f in range(3))


class Modelo:
    def __init__(self, ruta):
        with open(ruta, "rb") as f:
            datos = f.read()
        magia, version, _largo = struct.unpack_from("<III", datos, 0)
        if magia != 0x46546C67 or version != 2:
            raise ValueError("No es un .glb de glTF 2.0")
        largo, tipo = struct.unpack_from("<II", datos, 12)
        if tipo != 0x4E4F534A:
            raise ValueError("Al .glb le falta el JSON")
        self.gltf = j = json.loads(datos[20:20 + largo])
        pos = 20 + largo
        binario = b""
        if pos + 8 <= len(datos):
            largo_bin, _tipo = struct.unpack_from("<II", datos, pos)
            binario = memoryview(datos)[pos + 8:pos + 8 + largo_bin]
        extras = j.get("asset", {}).get("extras", {})
        self.titulo = extras.get("title", "")
        self.autor = extras.get("author", "")
        self.licencia = extras.get("license", "")
        self.fuente = extras.get("source", "")
        # Cada bufferView con vértices o índices, en crudo (lo sube a la gráfica quien dibuja).
        self.buffers = {}
        for i, bv in enumerate(j.get("bufferViews", [])):
            if bv.get("buffer", 0) == 0:
                ini = bv.get("byteOffset", 0)
                self.buffers[i] = binario[ini:ini + bv["byteLength"]]
        self.primitivas = {}  # malla -> [(modo, atributos, índices, color fijo, (mín, máx) de las posiciones)]
        for m, malla in enumerate(j.get("meshes", [])):
            self.primitivas[m] = [self._primitiva(p) for p in malla["primitives"]
                                  if "POSITION" in p["attributes"]]
        self.nodos = j.get("nodes", [])
        escena = j.get("scenes", [{}])[j.get("scene", 0)] if j.get("scenes") else {}
        self.raices = escena.get("nodes", [i for i in range(len(self.nodos))
                                           if not any(i in n.get("children", ()) for n in self.nodos)])
        self._animacion(j)
        self.centro, self.radio = self._tamano()

    def _accesor(self, i):
        """(bufferView, desplazamiento, componentes, tipo, normalizado, salto, cuántos) de un accessor."""
        a = self.gltf["accessors"][i]
        bv = self.gltf["bufferViews"][a["bufferView"]]
        n = COMPONENTES[a["type"]]
        salto = bv.get("byteStride") or n * TAMANOS[a["componentType"]]
        return (a["bufferView"], a.get("byteOffset", 0), n, a["componentType"], a.get("normalized", False),
                salto, a["count"])

    def _valores(self, i):
        bv, ini, n, tipo, normal, salto, cuantos = self._accesor(i)
        b = self.buffers[bv]
        fmt = "<%d%s" % (n, FORMATOS[tipo])
        sal = [struct.unpack_from(fmt, b, ini + salto * k) for k in range(cuantos)]
        if normal and tipo != 5126:
            tope = float((1 << (8 * TAMANOS[tipo] - (1 if tipo in (5120, 5122) else 0))) - 1)
            sal = [tuple(max(-1.0, v / tope) for v in t) for t in sal]
        return sal

    def _primitiva(self, p):
        atr = p["attributes"]
        atributos = {"POSITION": self._accesor(atr["POSITION"])}
        if "COLOR_0" in atr:
            bv, ini, n, tipo, normal, salto, cuantos = self._accesor(atr["COLOR_0"])
            atributos["COLOR_0"] = (bv, ini, n, tipo, normal or tipo != 5126, salto, cuantos)
        indices = self._accesor(p["indices"]) if "indices" in p else None
        mat = self.gltf.get("materials", [])[p["material"]] if "material" in p else {}
        color = tuple(mat.get("pbrMetallicRoughness", {}).get("baseColorFactor", (1.0, 1.0, 1.0, 1.0)))
        a = self.gltf["accessors"][atr["POSITION"]]
        limites = (a["min"], a["max"]) if "min" in a and "max" in a else None
        return p.get("mode", 4), atributos, indices, color, limites

    def _animacion(self, j):
        """Las pistas de la primera animación: nodo -> {propiedad: (tiempos, valores, interpolación)}."""
        self.pistas, self.duracion = {}, 0.0
        anims = j.get("animations", [])
        if not anims:
            return
        a = anims[0]
        for canal in a["channels"]:
            destino = canal["target"]
            if "node" not in destino or destino["path"] not in ("translation", "rotation", "scale"):
                continue
            s = a["samplers"][canal["sampler"]]
            tiempos = [v[0] for v in self._valores(s["input"])]
            valores = self._valores(s["output"])
            if s.get("interpolation") == "CUBICSPLINE":
                valores = valores[1::3]
            self.pistas.setdefault(destino["node"], {})[destino["path"]] = (tiempos, valores,
                                                                            s.get("interpolation", "LINEAR"))
            self.duracion = max(self.duracion, tiempos[-1])
        # Fotogramas de Sketchfab: cada hijo se ve desde que se enciende hasta que lo hace el siguiente.
        self.fotogramas = {}
        for i, n in enumerate(self.nodos):
            if n.get("name") == "sketchfab.timeframe" and n.get("children"):
                inicios = []
                for h in n["children"]:
                    tiempos, valores, _ = self.pistas.get(h, {}).get("scale", ([0.0], [(1, 1, 1)], ""))
                    inicios.append((next((t for t, v in zip(tiempos, valores) if v[0] > 1e-6), 0.0), h))
                inicios.sort()
                self.fotogramas[i] = inicios
                if len(inicios) > 1:
                    paso = (inicios[-1][0] - inicios[0][0]) / (len(inicios) - 1)
                    self.duracion = max(self.duracion, inicios[-1][0] + paso)

    def _muestra(self, pista, t):
        tiempos, valores, interp = pista
        if t <= tiempos[0] or len(tiempos) == 1:
            return valores[0]
        if t >= tiempos[-1]:
            return valores[-1]
        k = next(i for i in range(1, len(tiempos)) if tiempos[i] >= t)
        if interp == "STEP":
            return valores[k - 1]
        a, b = valores[k - 1], valores[k]
        f = (t - tiempos[k - 1]) / ((tiempos[k] - tiempos[k - 1]) or 1)
        v = tuple(x + (y - x) * f for x, y in zip(a, b))
        if len(v) == 4:  # cuaternión: normalizado (basta para pasos cortos entre claves)
            m = math.sqrt(sum(c * c for c in v)) or 1.0
            v = tuple(c / m for c in v)
        return v

    def _local(self, i, t):
        n = self.nodos[i]
        pista = self.pistas.get(i)
        if "matrix" in n and not pista:
            return tuple(n["matrix"])
        if not pista and not any(k in n for k in ("translation", "rotation", "scale")):
            return IDENTIDAD
        tr = pista.get("translation") if pista else None
        ro = pista.get("rotation") if pista else None
        es = pista.get("scale") if pista else None
        return trs(self._muestra(tr, t) if tr else n.get("translation", (0, 0, 0)),
                   self._muestra(ro, t) if ro else n.get("rotation", (0, 0, 0, 1)),
                   self._muestra(es, t) if es else n.get("scale", (1, 1, 1)))

    def dibujos(self, t):
        """Lo que se ve en el instante t (en segundos, ya dentro del bucle): [(matriz, primitiva)]."""
        sal = []

        def recorre(i, padre):
            m = multiplica(padre, self._local(i, t))
            n = self.nodos[i]
            if "mesh" in n:
                sal.extend((m, p) for p in self.primitivas.get(n["mesh"], ()))
            hijos = n.get("children", ())
            if i in self.fotogramas:
                hijos = [h for inicio, h in self.fotogramas[i] if inicio <= t + 1e-6][-1:] or \
                    [self.fotogramas[i][0][1]]
                for h in hijos:  # el fotograma que toca, aunque su propia escala diga otra cosa
                    nh = self.nodos[h]
                    mh = multiplica(m, trs(nh.get("translation", (0, 0, 0)), nh.get("rotation", (0, 0, 0, 1)),
                                           (1, 1, 1)))
                    for nieto in nh.get("children", ()):
                        recorre(nieto, mh)
                    if "mesh" in nh:
                        sal.extend((mh, p) for p in self.primitivas.get(nh["mesh"], ()))
                return
            for h in hijos:
                recorre(h, m)

        for r in self.raices:
            recorre(r, IDENTIDAD)
        return sal

    def _tamano(self):
        """Centro y radio de lo que se ve al empezar (para encuadrarlo)."""
        bajo, alto = [math.inf] * 3, [-math.inf] * 3
        for m, (_modo, _atributos, _ind, _color, limites) in self.dibujos(0.0):
            if not limites:
                continue
            a, b = limites
            for esquina in ((x, y, z) for x in (a[0], b[0]) for y in (a[1], b[1]) for z in (a[2], b[2])):
                p = aplica(m, esquina)
                bajo = [min(u, v) for u, v in zip(bajo, p)]
                alto = [max(u, v) for u, v in zip(alto, p)]
        if bajo[0] == math.inf:
            return (0.0, 0.0, 0.0), 1.0
        centro = tuple((u + v) / 2 for u, v in zip(bajo, alto))
        return centro, max(1e-6, max(v - u for u, v in zip(bajo, alto)) / 2)
