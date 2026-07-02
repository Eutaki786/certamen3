"""
Carga inicial de datos desde los archivos JSON hacia MongoDB.

Se ejecuta una sola vez (o cada vez que se quiera resetear la BD de prueba)
antes de usar main.py, porque main.py solo consulta, no crea datos.
"""

import sys
import json
from datetime import datetime
from pathlib import Path

from conexion import coleccion_eventos, coleccion_invitados

CARPETA_DATOS = Path(__file__).parent


def _parsear_fecha(fecha_iso: str) -> datetime:
    """Convierte 'YYYY-MM-DDTHH:MM:SSZ' a datetime real para poder filtrar por rango."""
    return datetime.fromisoformat(fecha_iso.replace("Z", "+00:00"))


def _cargar_json(nombre_archivo: str) -> list:
    ruta = CARPETA_DATOS / nombre_archivo
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró {ruta}. Colócalo junto a este script.")
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_eventos():
    datos = _cargar_json("eventos.json")
    for evento in datos:
        evento["fecha"] = _parsear_fecha(evento["fecha"])

    col = coleccion_eventos()
    col.delete_many({})
    col.insert_many(datos)
    col.create_index("codigo", unique=True)
    col.create_index("invitados.rut")
    print(f"[OK] {len(datos)} eventos cargados.")


def cargar_invitados():
    datos = _cargar_json("invitados.json")
    col = coleccion_invitados()
    col.delete_many({})
    col.insert_many(datos)
    col.create_index("rut", unique=True)
    print(f"[OK] {len(datos)} invitados cargados.")


if __name__ == "__main__":
    try:
        cargar_eventos()
        cargar_invitados()
        print("Carga completa.")
    except Exception as error:
        print(f"[ERROR] {error}")
        sys.exit(1)