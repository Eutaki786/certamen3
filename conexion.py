"""
Módulo de conexión a MongoDB.

Centraliza la creación del cliente y el acceso a las colecciones,
y maneja los errores de conexión de forma explícita en vez de dejar
que el programa se caiga con un traceback feo.
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

MONGO_URI = "mongodb://localhost:27017"
NOMBRE_BD = "certamen3"

_cliente = None
_bd = None


def obtener_bd():
    """
    Devuelve la base de datos, reutilizando la conexión si ya existe
    (patrón simple de conexión única para toda la app).
    """
    global _cliente, _bd

    if _bd is not None:
        return _bd

    try:
        _cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        _cliente.admin.command("ping")  # fuerza la conexión real, no solo la crea
        _bd = _cliente[NOMBRE_BD]
        return _bd
    except (ConnectionFailure, ServerSelectionTimeoutError) as error:
        raise ConnectionError(
            f"No se pudo conectar a MongoDB en {MONGO_URI}. "
            f"Verifica que el servicio esté corriendo (mongod). Detalle: {error}"
        )


def coleccion_eventos():
    return obtener_bd()["eventos"]


def coleccion_invitados():
    return obtener_bd()["invitados"]


def cerrar_conexion():
    global _cliente, _bd
    if _cliente is not None:
        _cliente.close()
        _cliente = None
        _bd = None
