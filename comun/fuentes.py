"""Las fuentes de los tipos de arte: se sacan de fuentes_datos.py a la carpeta de configuración
para que cada sistema las cargue. Si fallan, cada texto sigue con la letra del sistema."""

import base64
import os

import fuentes_datos


def extraer(carpeta):
    """Escribe las fuentes que falten en <carpeta>/fuentes y devuelve sus rutas."""
    destino = os.path.join(carpeta, "fuentes")
    os.makedirs(destino, exist_ok=True)
    rutas = []
    for nombre, datos in fuentes_datos.DATOS.items():
        ruta = os.path.join(destino, nombre)
        crudo = base64.b64decode(datos)
        if not os.path.exists(ruta) or os.path.getsize(ruta) != len(crudo):
            with open(ruta, "wb") as f:
                f.write(crudo)
        rutas.append(ruta)
    return rutas
