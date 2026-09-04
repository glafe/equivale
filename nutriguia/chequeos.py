"""Detección de problemas de integridad entre tablas de la base de datos -- sin UI. Factorizado
2026-08-31 (a pedido del usuario, revisión de "Chequeos automáticos" tras las limpiezas de datos
recientes) desde `views/configuracion.py`, que antes tenía esta lógica mezclada con el renderizado
de cada chequeo. Separarla permite que `app.py` la reutilice para el badge de alertas junto a
"Configuración" en la barra lateral (ver UI-BUILD-YOUR-MENU.md) sin duplicar el criterio de qué
cuenta como "problema" -- el mismo criterio que ya se usaba para decidir verde/amarillo dentro de
la página.

Cada función de detección regresa una lista/dict de "problemas" (la forma varía por chequeo, la
misma que ya consumía `views/configuracion.py`) -- vacío/falsy = todo bien, sin problemas.
`total_alertas()` es la única función que sabe CUÁNTOS chequeos (no problemas individuales) tienen
algo que revisar, para el badge.
"""

import difflib

import streamlit as st

from nutriguia import db as bd
from nutriguia.streamlit_data import cargar_catalogo, cargar_objetivo, cargar_personas, cargar_recetas, db
from nutriguia.texto import normalizar_busqueda
from nutriguia.validation import (
    ajustar_delta_por_intercambios,
    alimentos_libres_en_cero,
    delta_objetivo,
    sumar_por_grupo,
)

UMBRAL_SIMILITUD_CATALOGO = 0.82


def ingredientes_huerfanos() -> dict[str, dict]:
    """{alimento: {"grupo", "recetas": set(nombre_receta), "dias": set(etiqueta_dia)}} para
    alimentos usados en `recetas` o `menus_construidos` que no están en `catalogo_alimentos`.
    Escanea ambas colecciones desde `BUG-013` -- un alimento fusionado/renombrado en el catálogo
    queda huérfano para siempre en cualquier día ya guardado que lo usara, aunque el banco de
    recetas ya esté limpio."""
    catalogo = cargar_catalogo()
    por_alimento: dict[str, dict] = {}
    for r in cargar_recetas():
        for ing in r["ingredientes"]:
            if ing["alimento"] not in catalogo:
                entry = por_alimento.setdefault(
                    ing["alimento"], {"grupo": ing.get("grupo_smae"), "recetas": set(), "dias": set()}
                )
                entry["recetas"].add(r["nombre"])
    for doc in bd.listar_todos_los_dias(db()):
        for tiempo, datos in doc.get("tiempos", {}).items():
            for inst in datos.get("seleccion", []):
                for ing in inst["ingredientes"]:
                    if ing["alimento"] not in catalogo:
                        entry = por_alimento.setdefault(
                            ing["alimento"], {"grupo": ing.get("grupo_smae"), "recetas": set(), "dias": set()}
                        )
                        entry["dias"].add(f"{doc['persona']} · {doc.get('nombre') or doc['fecha']}")
    return por_alimento


def recetas_huerfanas() -> list[tuple[dict, str, dict]]:
    """[(documento, tiempo, instancia), ...] con un `receta_id` que ya no existe en `recetas`.
    `receta_id: None` (ingrediente suelto, FR-007) no cuenta -- no es una referencia rota."""
    recetas_ids = {r["receta_id"] for r in cargar_recetas()}
    return [
        (doc, tiempo, inst)
        for doc in bd.listar_todos_los_dias(db())
        for tiempo, datos in doc.get("tiempos", {}).items()
        for inst in datos.get("seleccion", [])
        if inst["receta_id"] is not None and inst["receta_id"] not in recetas_ids
    ]


def vectores_desincronizados() -> list[tuple[dict, dict]]:
    """[(receta, vector_real), ...] cuyo `vector_equivalentes` guardado no coincide con la suma
    real de sus ingredientes."""
    problemas = []
    for r in cargar_recetas():
        real = sumar_por_grupo(r["ingredientes"], "grupo_smae", "equivalentes")
        if real != r.get("vector_equivalentes", {}):
            problemas.append((r, real))
    return problemas


def ingredientes_duplicados_en_recetas() -> list[tuple[dict, list[str]]]:
    """[(receta, [alimentos_repetidos]), ...] -- mismo `alimento` listado 2+ veces en una receta
    del banco."""
    problemas = []
    for r in cargar_recetas():
        vistos: dict[str, int] = {}
        for ing in r["ingredientes"]:
            vistos[ing["alimento"]] = vistos.get(ing["alimento"], 0) + 1
        repetidos = sorted(n for n, veces in vistos.items() if veces > 1)
        if repetidos:
            problemas.append((r, repetidos))
    return problemas


def ingredientes_duplicados_en_dias() -> list[tuple[dict, str, int, dict, list[str]]]:
    """[(documento, tiempo, indice, instancia, [alimentos_repetidos]), ...] -- mismo caso que
    `ingredientes_duplicados_en_recetas()`, pero dentro de una instancia de un día YA GUARDADO
    (2026-08-31, revisión de "Chequeos automáticos" tras `BUG-013`: el banco se puede limpiar sin
    que eso toque los días ya guardados, así que un duplicado puede sobrevivir ahí aunque la
    receta original en el banco ya esté corregida). `indice` es la posición de la instancia dentro
    de `seleccion` -- un día guardado no tiene `instancia_id` (ver schema.md)."""
    problemas = []
    for doc in bd.listar_todos_los_dias(db()):
        for tiempo, datos in doc.get("tiempos", {}).items():
            for indice, inst in enumerate(datos.get("seleccion", [])):
                vistos: dict[str, int] = {}
                for ing in inst["ingredientes"]:
                    vistos[ing["alimento"]] = vistos.get(ing["alimento"], 0) + 1
                repetidos = sorted(n for n, veces in vistos.items() if veces > 1)
                if repetidos:
                    problemas.append((doc, tiempo, indice, inst, repetidos))
    return problemas


def ingredientes_libres_en_cero_en_recetas() -> list[tuple[dict, list[str]]]:
    """[(receta, [alimentos_libres_en_cero]), ...] -- ingrediente sin grupo SMAE con
    `equivalentes: 0` en una receta del banco (KC-003 en BUGS.md, detectado 2026-09-04 tras una
    semana de uso: "Lista del súper" escala la cantidad a comprar con `equivalentes`, así que un
    0 ahí se ve como "0 cucharadita" en una lista de compras real, aunque no afecte la aritmética
    de equivalentes por grupo)."""
    problemas = []
    for r in cargar_recetas():
        afectados = alimentos_libres_en_cero(r["ingredientes"])
        if afectados:
            problemas.append((r, afectados))
    return problemas


def ingredientes_libres_en_cero_en_dias() -> list[tuple[dict, str, int, dict, list[str]]]:
    """Mismo caso que `ingredientes_libres_en_cero_en_recetas()`, pero dentro de un día ya
    guardado -- mismo patrón que `ingredientes_duplicados_en_dias()` (limpiar el banco no toca
    los días que ya se guardaron con la receta en su versión anterior)."""
    problemas = []
    for doc in bd.listar_todos_los_dias(db()):
        for tiempo, datos in doc.get("tiempos", {}).items():
            for indice, inst in enumerate(datos.get("seleccion", [])):
                afectados = alimentos_libres_en_cero(inst["ingredientes"])
                if afectados:
                    problemas.append((doc, tiempo, indice, inst, afectados))
    return problemas


def normalizar_par(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def pares_descartados() -> set[tuple[str, str]]:
    return {normalizar_par(a, b) for a, b in bd.listar_pares_descartados(db())}


def pares_similares_en_catalogo(umbral: float = UMBRAL_SIMILITUD_CATALOGO) -> list[tuple[str, str, float]]:
    """[(a, b, similitud), ...] ordenado por similitud descendente -- pares de nombres del
    catálogo parecidos por texto (`difflib`, no exacto), excluyendo los ya marcados "son
    diferentes" en `duplicados_descartados`."""
    catalogo = cargar_catalogo()
    nombres = sorted(catalogo.keys())
    descartados = pares_descartados()
    pares = []
    for i, a in enumerate(nombres):
        norm_a = normalizar_busqueda(a)
        for b in nombres[i + 1 :]:
            if normalizar_par(a, b) in descartados:
                continue
            ratio = difflib.SequenceMatcher(None, norm_a, normalizar_busqueda(b)).ratio()
            if ratio >= umbral:
                pares.append((a, b, ratio))
    pares.sort(key=lambda x: -x[2])
    return pares


def personas_sin_objetivo() -> list[str]:
    return [p for p in cargar_personas() if not cargar_objetivo(p)]


def asignacion_rota() -> list[tuple[str, str, str]]:
    """[(persona, dia, nombre_eliminado), ...] -- un día de `asignacion_semanal` que apunta a un
    nombre que ya no existe en `menus_construidos` de esa persona."""
    problemas = []
    for doc in bd.listar_todas_las_asignaciones(db()):
        nombres_persona = {
            m["nombre"]
            for m in bd.listar_dias(db(), doc["persona"])
            if m["nombre"] is not None
        }
        for dia, nombre in doc.get("dias", {}).items():
            if nombre and nombre not in nombres_persona:
                problemas.append((doc["persona"], dia, nombre))
    return problemas


def dias_con_estado_desactualizado() -> list[tuple[dict, dict, str]]:
    """[(documento, delta_nuevo, estado_nuevo), ...] para días guardados cuyo `estado`/
    `delta_diario` guardado no coincide con lo que daría recalcularlo HOY -- ej. si el criterio de
    qué cuenta como "completo" cambió después de guardar ese día (2026-08-30: Cereal/Leguminosa
    intercambiables) y nadie volvió a abrir/guardar ese día desde entonces, se queda mostrando
    "en progreso" en el historial aunque ya sea "completo" con el criterio actual. Nuevo
    2026-08-31, revisión de "Chequeos automáticos" tras esa misma limpieza -- pensado como red de
    seguridad general para cualquier cambio futuro de este tipo, no solo este caso puntual."""
    problemas = []
    for doc in bd.listar_todos_los_dias(db()):
        delta_nuevo = ajustar_delta_por_intercambios(
            delta_objetivo(doc.get("objetivo_diario", {}), doc.get("actual_diario", {}))
        )
        estado_nuevo = "completo" if delta_nuevo and all(v == 0 for v in delta_nuevo.values()) else "en_progreso"
        if estado_nuevo != doc.get("estado") or delta_nuevo != doc.get("delta_diario", {}):
            problemas.append((doc, delta_nuevo, estado_nuevo))
    return problemas


@st.cache_data(ttl=60)
def total_alertas() -> int:
    """Cuántos CHEQUEOS (no problemas individuales) tienen al menos un hallazgo -- para el badge
    de "Configuración" en la barra lateral (`app.py`). Un conteo de chequeos, no de problemas
    individuales, es más legible como número chico en un badge (3 secciones a revisar dice más que
    47 problemas sueltos). Cacheado 60s -- esta página no se visita seguido, pero `app.py` se
    re-ejecuta en CADA interacción de CUALQUIER página de la app, así que sin cache este chequeo
    completo correría de más en cada clic en toda la app."""
    chequeos = [
        ingredientes_huerfanos(),
        recetas_huerfanas(),
        vectores_desincronizados(),
        ingredientes_duplicados_en_recetas(),
        ingredientes_duplicados_en_dias(),
        pares_similares_en_catalogo(),
        personas_sin_objetivo(),
        asignacion_rota(),
        dias_con_estado_desactualizado(),
        ingredientes_libres_en_cero_en_recetas(),
        ingredientes_libres_en_cero_en_dias(),
    ]
    return sum(1 for problema in chequeos if problema)


def invalidar_cache_alertas() -> None:
    total_alertas.clear()
