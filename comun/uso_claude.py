"""Lee el uso del plan de Claude que deja el mod de Claude Code en ~/.claude/uso-plan.json."""

import json
import os
from datetime import datetime, timezone

ARCHIVO = os.path.expanduser("~/.claude/uso-plan.json")


def _fecha(texto):
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def leer(ahora=None):
    """{"cinco": %, "semana": %, "vuelve": datetime|None, "leido": datetime} o None si aún no hay datos.
    Una ventana cuyo reinicio ya pasó cuenta como 0: el archivo es de la última vez que se usó Claude."""
    try:
        with open(ARCHIVO, encoding="utf-8") as f:
            d = json.load(f)
        limites = {l["kind"]: l for l in d["limites"]}
    except (OSError, ValueError, KeyError, TypeError):
        return None
    ahora = ahora or datetime.now(timezone.utc)

    def ventana(tipo):
        l = limites.get(tipo)
        if not l:
            return None, None
        fin = _fecha(l.get("resetsAt"))
        if fin and fin <= ahora:
            return 0, None
        return l.get("percentUsed"), fin

    cinco, vuelve = ventana("five_hour")
    semana, _fin = ventana("seven_day")
    return {"cinco": cinco, "semana": semana, "vuelve": vuelve, "leido": _fecha(d.get("leido"))}


def duracion(hasta, ahora=None):
    """Lo que falta hasta `hasta`, corto: "1 h 12 min", "8 min"."""
    minutos = int((hasta - (ahora or datetime.now(timezone.utc))).total_seconds() // 60) + 1
    return f"{minutos // 60} h {minutos % 60} min" if minutos >= 60 else f"{minutos} min"
