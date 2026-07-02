# Gestor de Eventos - MongoDB

## Estructura
- `conexion.py` — conexión a MongoDB (colecciones `eventos` e `invitados`).
- `cargar_datos.py` — carga `eventos.json` e `invitados.json` a MongoDB (correr una sola vez).
- `consultas.py` — todas las funciones de consulta/agregación (una por requerimiento).
- `main.py` — menú de consola que usa las funciones de `consultas.py`.

## Cómo correrlo

1. Instalar dependencias:
   ```
   pip install -r requirements.txt
   ```

2. Tener MongoDB corriendo localmente (por defecto en `mongodb://localhost:27017`).
   Si usas Atlas u otra URI, cambia `MONGO_URI` en `conexion.py`.

3. Cargar los datos (una sola vez, o cuando quieras resetear):
   ```
   python cargar_datos.py
   ```

4. Ejecutar la app:
   ```
   python main.py
   ```

## Mapeo con la pauta

| Ítem pauta | Dónde está |
|---|---|
| Conexión y filtros básicos | `conexion.py`, `consultas.listar_eventos` |
| Req. 1 - listar eventos | `consultas.listar_eventos` |
| Filtros por criterios (fecha/categoría) | `consultas.filtrar_eventos` |
| Req. 2 - nombre parcial (regex) | `consultas.buscar_invitados_por_nombre` |
| Filtro por dominio de correo (regex) | `consultas.filtrar_invitados_por_dominio` |
| Búsqueda en subdocumentos | `consultas.verificar_invitado_en_evento` |
| Req. 4 - Top 3 confirmados (agregación) | `consultas.top_eventos_por_confirmados` |
| Req. 3 - validar acceso con `$lookup` | `consultas.validar_acceso_invitado` |
| App estructurada con menú | `main.py` |
| Validación de entrada / manejo de errores | funciones `validar_*` en `consultas.py`, try/except en `main.py` |

## Tomas Cardenas
## ingenieria en ciberseguridad inacap concepcion talcahuano