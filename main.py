"""
Aplicación de consola para gestión de eventos e invitados sobre MongoDB.

Ejecutar primero cargar_datos.py una vez, y luego este archivo.
"""

from conexion import cerrar_conexion, obtener_bd
import consultas


def _pedir_texto(mensaje: str) -> str:
    return input(mensaje).strip()


def _mostrar_eventos(eventos):
    if not eventos:
        print("No se encontraron eventos.")
        return
    print(f"\n{'Código':<14}{'Nombre':<28}{'Fecha':<22}{'Lugar':<16}{'Categoría'}")
    print("-" * 95)
    for e in eventos:
        fecha = e["fecha"].strftime("%Y-%m-%d %H:%M") if hasattr(e["fecha"], "strftime") else e["fecha"]
        print(f"{e['codigo']:<14}{e['nombre']:<28}{fecha:<22}{e['lugar']:<16}{e['categoria']}")
    print()


def _mostrar_invitados(invitados):
    if not invitados:
        print("No se encontraron invitados.")
        return
    print(f"\n{'RUT':<14}{'Nombre':<22}{'Correo':<30}{'Empresa':<16}{'Estado'}")
    print("-" * 95)
    for i in invitados:
        print(f"{i['rut']:<14}{i['nombre']:<22}{i['correo']:<30}{i['empresa']:<16}{i['estado']}")
    print()


def opcion_listar_eventos():
    eventos = consultas.listar_eventos()
    _mostrar_eventos(eventos)


def opcion_filtrar_eventos():
    print("Deja en blanco cualquier campo que no quieras usar como filtro.")
    categoria = _pedir_texto("Categoría (charla/workshop/meetup): ")
    lugar = _pedir_texto("Lugar: ")
    fecha_desde = _pedir_texto("Fecha desde (YYYY-MM-DD): ")
    fecha_hasta = _pedir_texto("Fecha hasta (YYYY-MM-DD): ")

    eventos = consultas.filtrar_eventos(
        categoria=categoria or None,
        lugar=lugar or None,
        fecha_desde=fecha_desde or None,
        fecha_hasta=fecha_hasta or None,
    )
    _mostrar_eventos(eventos)


def opcion_buscar_invitados_nombre():
    fragmento = _pedir_texto("Fragmento del nombre a buscar: ")
    invitados = consultas.buscar_invitados_por_nombre(fragmento)
    _mostrar_invitados(invitados)


def opcion_filtrar_por_dominio():
    dominio = _pedir_texto("Dominio de correo (ej: empresa.cl): ")
    invitados = consultas.filtrar_invitados_por_dominio(dominio)
    _mostrar_invitados(invitados)


def opcion_verificar_subdocumento():
    codigo = _pedir_texto("Código del evento (EVT-YYYY-NNN): ")
    rut = _pedir_texto("RUT del invitado (11.111.111-1): ")
    resultado = consultas.verificar_invitado_en_evento(codigo, rut)
    if resultado is None:
        print("Ese invitado no está registrado en ese evento.\n")
    else:
        print(f"\nEvento: {resultado['evento']}")
        print(f"RUT: {resultado['rut']}")
        print(f"Estado: {resultado['estado']}")
        print(f"Check-in: {'Sí' if resultado['checkin'] else 'No'}\n")


def opcion_top_confirmados():
    top = consultas.top_eventos_por_confirmados(3)
    if not top:
        print("No hay datos suficientes.\n")
        return
    print("\nTop 3 eventos con más confirmados:")
    for pos, e in enumerate(top, start=1):
        print(f"{pos}. {e['nombre']} ({e['codigo']}) - {e['cantidad_confirmados']} confirmados")
    print()


def opcion_validar_acceso():
    codigo = _pedir_texto("Código del evento (EVT-YYYY-NNN): ")
    rut = _pedir_texto("RUT del invitado (11.111.111-1): ")
    resultado = consultas.validar_acceso_invitado(codigo, rut)

    print()
    if resultado["acceso"]:
        print(f"ACCESO PERMITIDO -> {resultado['motivo']}")
    else:
        print(f"ACCESO DENEGADO -> {resultado['motivo']}")

    detalle = resultado.get("detalle")
    if detalle:
        print(f"   Nombre: {detalle.get('nombre_invitado')}")
        print(f"   Empresa: {detalle.get('empresa')}")
        print(f"   Estado en evento: {detalle.get('estado_en_evento')}")
    print()


def opcion_correos_confirmados_por_evento():
    nombre_evento = _pedir_texto("Nombre del evento (o parte de él): ")
    resultados = consultas.correos_confirmados_por_nombre_evento(nombre_evento)

    if not resultados:
        print("No se encontraron confirmados para ese evento (o el evento no existe).\n")
        return

    eventos_vistos = set()
    for r in resultados:
        if r["evento"] not in eventos_vistos:
            print(f"\nEvento: {r['evento']} ({r['codigo_evento']})")
            eventos_vistos.add(r["evento"])
        correo = r["correo"] or "(sin perfil en invitados.json)"
        print(f"  - {r['nombre_invitado'] or r['rut']}: {correo}")
    print()


def opcion_categoria_por_evento():
    nombre_evento = _pedir_texto("Nombre del evento (o parte de él): ")
    resultados = consultas.categoria_por_nombre_evento(nombre_evento)

    if not resultados:
        print("No se encontró ningún evento con ese nombre.\n")
        return

    print()
    for r in resultados:
        print(f"  {r['nombre']} ({r['codigo']}) -> categoría: {r['categoria']}")
    print()


OPCIONES = {
    "1": ("Listar todos los eventos", opcion_listar_eventos),
    "2": ("Filtrar eventos por categoría / lugar / fecha", opcion_filtrar_eventos),
    "3": ("Buscar invitados por nombre (parcial)", opcion_buscar_invitados_nombre),
    "4": ("Filtrar invitados por dominio de correo", opcion_filtrar_por_dominio),
    "5": ("Verificar invitado dentro de un evento (subdocumento)", opcion_verificar_subdocumento),
    "6": ("Top 3 eventos con más confirmados", opcion_top_confirmados),
    "7": ("Validar acceso de invitado a evento ($lookup)", opcion_validar_acceso),
    "8": ("Correos de confirmados de un evento (buscar por nombre)", opcion_correos_confirmados_por_evento),
    "9": ("Categoría de un evento (buscar por nombre)", opcion_categoria_por_evento),
}


def mostrar_menu():
    print("=" * 55)
    print(" GESTOR DE EVENTOS - MongoDB")
    print("=" * 55)
    for clave, (descripcion, _) in OPCIONES.items():
        print(f" {clave}. {descripcion}")
    print(" 0. Salir")
    print("=" * 55)


def main():
    try:
        obtener_bd()  # valida la conexión apenas arranca el programa
    except ConnectionError as error:
        print(f"[ERROR FATAL] {error}")
        return

    while True:
        mostrar_menu()
        opcion = _pedir_texto("Elige una opción: ")

        if opcion == "0":
            print("Hasta luego.")
            break

        accion = OPCIONES.get(opcion)
        if accion is None:
            print("Opción inválida, intenta nuevamente.\n")
            continue

        try:
            accion[1]()
        except (ValueError, RuntimeError) as error:
            print(f"[ERROR] {error}\n")
        except Exception as error:
            print(f"[ERROR INESPERADO] {error}\n")

    cerrar_conexion()


if __name__ == "__main__":
    main()
