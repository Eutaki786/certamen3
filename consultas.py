"""
Funciones de consulta contra MongoDB.

Cada función corresponde a uno de los requerimientos del certamen.
Todas validan su entrada antes de tocar la base de datos: eso cubre
el ítem de seguridad de la pauta (validar entrada, manejar errores).
"""

import re
from datetime import datetime, timedelta

from pymongo.errors import PyMongoError

from conexion import coleccion_eventos, coleccion_invitados

RUT_REGEX = re.compile(r"^\d{1,2}\.\d{3}\.\d{3}-[\dkK]$")
CODIGO_EVENTO_REGEX = re.compile(r"^EVT-\d{4}-\d{3}$")


# ---------- Validaciones (seguridad: 3.1.4.I.10) ----------

def validar_rut(rut: str) -> str:
    rut = (rut or "").strip()
    if not RUT_REGEX.match(rut):
        raise ValueError(f"RUT con formato inválido: '{rut}' (esperado 11.111.111-1)")
    return rut


def validar_codigo_evento(codigo: str) -> str:
    codigo = (codigo or "").strip().upper()
    if not CODIGO_EVENTO_REGEX.match(codigo):
        raise ValueError(f"Código de evento inválido: '{codigo}' (esperado EVT-YYYY-NNN)")
    return codigo


def validar_texto_busqueda(texto: str, campo: str = "texto") -> str:
    texto = (texto or "").strip()
    if not texto:
        raise ValueError(f"El {campo} de búsqueda no puede estar vacío.")
    if len(texto) > 100:
        raise ValueError(f"El {campo} de búsqueda es demasiado largo.")
    return texto


def _regex_seguro(texto: str) -> str:
    """Escapa caracteres especiales para que el usuario no pueda inyectar
    una regex arbitraria en la consulta (evita abusar operadores de Mongo)."""
    return re.escape(texto)


# ---------- 3.1.1.I.1 / 3.1.1.I.3: filtros básicos y por criterios ----------

def listar_eventos():
    """Requerimiento 1: código, nombre, fecha, lugar y categoría de todos los eventos."""
    try:
        proyeccion = {"_id": 0, "codigo": 1, "nombre": 1, "fecha": 1, "lugar": 1, "categoria": 1}
        return list(coleccion_eventos().find({}, proyeccion).sort("fecha", 1))
    except PyMongoError as error:
        raise RuntimeError(f"Error al listar eventos: {error}")


def filtrar_eventos(categoria: str = None, lugar: str = None,
                     fecha_desde: str = None, fecha_hasta: str = None):
    """Filtra eventos por categoría, lugar y/o rango de fechas (criterios combinables)."""
    filtro = {}

    if categoria:
        filtro["categoria"] = categoria.strip().lower()

    if lugar:
        filtro["lugar"] = {"$regex": _regex_seguro(lugar.strip()), "$options": "i"}

    if fecha_desde or fecha_hasta:
        rango = {}
        try:
            if fecha_desde:
                rango["$gte"] = datetime.fromisoformat(fecha_desde)
            if fecha_hasta:
                rango["$lte"] = datetime.fromisoformat(fecha_hasta) + timedelta(days=1)
        except ValueError:
            raise ValueError("Fecha inválida. Usa formato YYYY-MM-DD.")
        filtro["fecha"] = rango

    try:
        proyeccion = {"_id": 0, "codigo": 1, "nombre": 1, "fecha": 1, "lugar": 1, "categoria": 1}
        return list(coleccion_eventos().find(filtro, proyeccion).sort("fecha", 1))
    except PyMongoError as error:
        raise RuntimeError(f"Error al filtrar eventos: {error}")


# ---------- 3.1.2.I.4 / 3.1.2.I.5: invitados por nombre parcial y por dominio ----------

def buscar_invitados_por_nombre(fragmento: str):
    """Requerimiento 2: búsqueda parcial, case-insensitive, por nombre (regex)."""
    fragmento = validar_texto_busqueda(fragmento, "nombre")
    try:
        filtro = {"nombre": {"$regex": _regex_seguro(fragmento), "$options": "i"}}
        return list(coleccion_invitados().find(filtro, {"_id": 0}))
    except PyMongoError as error:
        raise RuntimeError(f"Error al buscar invitados: {error}")


def filtrar_invitados_por_dominio(dominio: str):
    """Filtra invitados cuyo correo termina en el dominio dado (ej: empresa.cl)."""
    dominio = validar_texto_busqueda(dominio, "dominio")
    dominio = dominio.lstrip("@")
    try:
        patron = f"@{_regex_seguro(dominio)}$"
        filtro = {"correo": {"$regex": patron, "$options": "i"}}
        return list(coleccion_invitados().find(filtro, {"_id": 0}))
    except PyMongoError as error:
        raise RuntimeError(f"Error al filtrar por dominio: {error}")


# ---------- 3.1.3.I.6: búsqueda en subdocumentos ----------

def verificar_invitado_en_evento(codigo_evento: str, rut: str):
    """
    Busca dentro del array 'invitados' (subdocumento) de un evento específico
    si existe un invitado con ese rut, y devuelve su estado y checkin.
    """
    codigo_evento = validar_codigo_evento(codigo_evento)
    rut = validar_rut(rut)

    try:
        filtro = {
            "codigo": codigo_evento,
            "invitados": {"$elemMatch": {"rut": rut}},
        }
        proyeccion = {"_id": 0, "nombre": 1, "invitados.$": 1}
        resultado = coleccion_eventos().find_one(filtro, proyeccion)
    except PyMongoError as error:
        raise RuntimeError(f"Error al verificar invitado en evento: {error}")

    if not resultado:
        return None

    invitado_en_evento = resultado["invitados"][0]
    return {
        "evento": resultado["nombre"],
        "rut": invitado_en_evento["rut"],
        "estado": invitado_en_evento["estado"],
        "checkin": invitado_en_evento["checkin"],
    }


# ---------- 3.1.3.I.7 (Requerimiento 4): top 3 eventos con más confirmados ----------

def top_eventos_por_confirmados(top_n: int = 3):
    """Agregación: cuenta invitados con estado 'confirmado' por evento y devuelve el top N."""
    if not isinstance(top_n, int) or top_n <= 0:
        raise ValueError("top_n debe ser un entero positivo.")

    pipeline = [
        {
            "$addFields": {
                "cantidad_confirmados": {
                    "$size": {
                        "$filter": {
                            "input": "$invitados",
                            "as": "inv",
                            "cond": {"$eq": ["$$inv.estado", "confirmado"]},
                        }
                    }
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "codigo": 1,
                "nombre": 1,
                "fecha": 1,
                "categoria": 1,
                "cantidad_confirmados": 1,
            }
        },
        {"$sort": {"cantidad_confirmados": -1}},
        {"$limit": top_n},
    ]

    try:
        return list(coleccion_eventos().aggregate(pipeline))
    except PyMongoError as error:
        raise RuntimeError(f"Error al calcular el top de eventos: {error}")


# ---------- 3.1.4.I.8 (Requerimiento 3): validar acceso cruzando colecciones con $lookup ----------

def validar_acceso_invitado(codigo_evento: str, rut: str):
    """
    Cruza la colección eventos (subdocumento invitados) con la colección
    invitados (perfil completo) usando $lookup, para responder:
    ¿esta persona está invitada, confirmada, y quién es realmente?
    """
    codigo_evento = validar_codigo_evento(codigo_evento)
    rut = validar_rut(rut)

    pipeline = [
        {"$match": {"codigo": codigo_evento}},
        {"$unwind": "$invitados"},
        {"$match": {"invitados.rut": rut}},
        {
            "$lookup": {
                "from": "invitados",
                "localField": "invitados.rut",
                "foreignField": "rut",
                "as": "perfil",
            }
        },
        {"$unwind": {"path": "$perfil", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "_id": 0,
                "evento": "$nombre",
                "codigo_evento": "$codigo",
                "rut": "$invitados.rut",
                "estado_en_evento": "$invitados.estado",
                "checkin": "$invitados.checkin",
                "nombre_invitado": "$perfil.nombre",
                "correo": "$perfil.correo",
                "empresa": "$perfil.empresa",
                "estado_cuenta": "$perfil.estado",
            }
        },
    ]

    try:
        resultado = list(coleccion_eventos().aggregate(pipeline))
    except PyMongoError as error:
        raise RuntimeError(f"Error al validar acceso: {error}")

    if not resultado:
        return {"acceso": False, "motivo": "El invitado no está registrado en este evento.", "detalle": None}

    datos = resultado[0]

    if datos.get("estado_cuenta") == "bloqueado":
        return {"acceso": False, "motivo": "La cuenta del invitado está bloqueada.", "detalle": datos}

    if datos["estado_en_evento"] != "confirmado":
        return {
            "acceso": False,
            "motivo": f"El invitado está '{datos['estado_en_evento']}', no confirmado.",
            "detalle": datos,
        }

    return {"acceso": True, "motivo": "Acceso autorizado.", "detalle": datos}


# ---------- Consulta adicional 1: correos de confirmados, buscando evento por nombre ----------

def correos_confirmados_por_nombre_evento(nombre_evento: str):
    """
    Busca evento(s) por nombre (parcial, case-insensitive) y devuelve el correo
    electrónico de cada invitado con estado 'confirmado' en ese evento.
    Usa $lookup porque el correo vive en la colección 'invitados', no en el
    subdocumento embebido dentro de 'eventos'.
    """
    nombre_evento = validar_texto_busqueda(nombre_evento, "nombre de evento")

    pipeline = [
        {"$match": {"nombre": {"$regex": _regex_seguro(nombre_evento), "$options": "i"}}},
        {"$unwind": "$invitados"},
        {"$match": {"invitados.estado": "confirmado"}},
        {
            "$lookup": {
                "from": "invitados",
                "localField": "invitados.rut",
                "foreignField": "rut",
                "as": "perfil",
            }
        },
        {"$unwind": {"path": "$perfil", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "_id": 0,
                "evento": "$nombre",
                "codigo_evento": "$codigo",
                "rut": "$invitados.rut",
                "nombre_invitado": "$perfil.nombre",
                "correo": "$perfil.correo",
            }
        },
        {"$sort": {"evento": 1, "correo": 1}},
    ]

    try:
        return list(coleccion_eventos().aggregate(pipeline))
    except PyMongoError as error:
        raise RuntimeError(f"Error al buscar correos de confirmados: {error}")


# ---------- Consulta adicional 2: categoría de un evento, buscando por nombre ----------

def categoria_por_nombre_evento(nombre_evento: str):
    """
    Busca evento(s) por nombre (parcial, case-insensitive) y devuelve su categoría.
    Consulta simple con find(), sin agregación, porque toda la info vive en
    el mismo documento de 'eventos'.
    """
    nombre_evento = validar_texto_busqueda(nombre_evento, "nombre de evento")

    try:
        filtro = {"nombre": {"$regex": _regex_seguro(nombre_evento), "$options": "i"}}
        proyeccion = {"_id": 0, "codigo": 1, "nombre": 1, "categoria": 1}
        return list(coleccion_eventos().find(filtro, proyeccion))
    except PyMongoError as error:
        raise RuntimeError(f"Error al obtener categoría: {error}")
