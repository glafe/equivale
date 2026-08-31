"""Aritmética de equivalentes SMAE. Módulo puro: sin Mongo, sin Streamlit, sin I/O.

Ver VALIDATION.md para el contrato exacto de cada función. No reimplementar esta lógica en
ningún otro lado (app.py, import_data.py, tests) — todo pasa por aquí.
"""


def sumar_por_grupo(items: list[dict], campo_grupo: str, campo_cantidad: str) -> dict[str, int]:
    resultado: dict[str, int] = {}
    for item in items:
        grupo = item.get(campo_grupo)
        if grupo is None:
            continue
        resultado[grupo] = resultado.get(grupo, 0) + item[campo_cantidad]
    return resultado


def delta_objetivo(objetivo: dict[str, int], actual: dict[str, int]) -> dict[str, int]:
    grupos = set(objetivo) | set(actual)
    return {grupo: objetivo.get(grupo, 0) - actual.get(grupo, 0) for grupo in grupos}


# Grupos que se pueden cubrir uno al otro (a pedido del usuario, 2026-08-30 -- "un cereal puede
# ser intercambiable por 1 leguminosa"). Ver CLAUDE.md: el campo histórico `grupos_intercambiables`
# de `menus` (schema.md) declaraba esto por periodo para los menús YA importados -- acá es un
# equivalente para "Menú del día" en vivo, pero fijo (no varía por persona/periodo) porque nadie
# lo pidió configurable todavía; si algún día hace falta que varíe, este constante ya no alcanza y
# habría que moverlo a `objetivos`/`personas`.
GRUPOS_INTERCAMBIABLES: list[tuple[str, str]] = [("Cereal", "Leguminosa")]


def ajustar_delta_por_intercambios(
    delta: dict[str, int], pares: list[tuple[str, str]] = GRUPOS_INTERCAMBIABLES
) -> dict[str, int]:
    """Redistribuye un `delta` (salida de `delta_objetivo()`) entre pares de grupos intercambiables
    -- si uno tiene delta positivo (falta) y el otro negativo (excedido), usa el excedente del
    segundo para cubrir parte (o todo) del faltante del primero, hasta agotar el menor de los dos
    en valor absoluto. No hace nada si los dos tienen el mismo signo (ambos "falta" o ambos
    "excedido" -- ahí no hay excedente que redirigir) o si alguno de los dos grupos no aparece en
    `delta`. Devuelve un delta NUEVO (no muta el original) -- ej. `{"Cereal": 2, "Leguminosa": -1}`
    -> `{"Cereal": 1, "Leguminosa": 0}` (la Leguminosa de más cubrió 1 de los 2 Cereal faltantes;
    sigue faltando 1 Cereal, ya no hay Leguminosa de sobra que lo compense). El orden del par no
    importa -- funciona igual si el que sobra es el primero o el segundo del par."""
    ajustado = dict(delta)
    for g1, g2 in pares:
        if g1 not in ajustado or g2 not in ajustado:
            continue
        d1, d2 = ajustado[g1], ajustado[g2]
        if d1 > 0 and d2 < 0:
            transferencia = min(d1, -d2)
            ajustado[g1] = d1 - transferencia
            ajustado[g2] = d2 + transferencia
        elif d2 > 0 and d1 < 0:
            transferencia = min(d2, -d1)
            ajustado[g2] = d2 - transferencia
            ajustado[g1] = d1 + transferencia
    return ajustado


def es_exacto(delta: dict[str, int]) -> bool:
    return all(valor == 0 for valor in delta.values())


def estado_por_grupo(delta: dict[str, int]) -> dict[str, str]:
    estado = {}
    for grupo, valor in delta.items():
        if valor == 0:
            estado[grupo] = "exacto"
        elif valor > 0:
            estado[grupo] = "falta"
        else:
            estado[grupo] = "excedido"
    return estado


def validar_tiempo(tiempo: dict) -> tuple[bool, dict]:
    declarado = sumar_por_grupo(tiempo["equivalentes"], "grupo", "cantidad")
    ingredientes = [
        ingrediente
        for platillo in tiempo["platillos"]
        for ingrediente in platillo["ingredientes"]
    ]
    real = sumar_por_grupo(ingredientes, "grupo_smae", "equivalentes")
    delta = delta_objetivo(declarado, real)
    return es_exacto(delta), delta


def validar_menu(menu: dict) -> tuple[bool, dict, list[tuple[str, dict]]]:
    declarado_diario = sumar_por_grupo(menu["equivalentes_diarios"], "grupo", "cantidad")
    equivalentes_por_tiempo = [
        equivalente for tiempo in menu["tiempos"] for equivalente in tiempo["equivalentes"]
    ]
    suma_tiempos = sumar_por_grupo(equivalentes_por_tiempo, "grupo", "cantidad")
    delta_diario = delta_objetivo(declarado_diario, suma_tiempos)
    es_valido_dia = es_exacto(delta_diario)

    tiempos_invalidos = []
    for tiempo in menu["tiempos"]:
        valido, delta = validar_tiempo(tiempo)
        if not valido:
            tiempos_invalidos.append((tiempo["tiempo"], delta))

    return es_valido_dia, delta_diario, tiempos_invalidos


def paso_equivalente(alimento: str, catalogo_por_nombre: dict) -> str | None:
    entrada = catalogo_por_nombre.get(alimento)
    if entrada is None:
        return None
    return entrada["cantidad_por_equivalente"]


def fusionar_ingredientes_duplicados(ingredientes: list[dict]) -> list[dict]:
    """Colapsa ingredientes con el mismo `alimento` (2+ ocurrencias) en uno solo, sumando sus
    `equivalentes` -- no cambia el total por grupo (la suma es la misma repartida en 1 fila en vez
    de N), así que es seguro aplicarla sin revisar caso por caso. `opcional`/`bloqueado`/`asuncion`
    quedan en True si CUALQUIER ocurrencia los tenía en True; `cantidad`/`grupo_smae` se toman de
    la primera ocurrencia (deberían coincidir entre duplicados del mismo alimento). Preserva el
    orden de primera aparición. Detectado 2026-08-30: "🔗 Usar este" en Configuración/Editor de
    ingredientes renombraba un huérfano al nombre de un alimento que la receta YA tenía, dejando
    dos filas con el mismo `alimento` en vez de fusionarlas."""
    orden: list[str] = []
    por_alimento: dict[str, list[dict]] = {}
    for ing in ingredientes:
        nombre = ing["alimento"]
        if nombre not in por_alimento:
            por_alimento[nombre] = []
            orden.append(nombre)
        por_alimento[nombre].append(ing)

    resultado = []
    for nombre in orden:
        ocurrencias = por_alimento[nombre]
        if len(ocurrencias) == 1:
            resultado.append(ocurrencias[0])
            continue
        fusionado = dict(ocurrencias[0])
        fusionado["equivalentes"] = sum(o["equivalentes"] for o in ocurrencias)
        for bandera in ("opcional", "bloqueado", "asuncion"):
            if any(o.get(bandera) for o in ocurrencias):
                fusionado[bandera] = True
        resultado.append(fusionado)
    return resultado


def renombrar_ingrediente_en_menu_guardado(documento: dict, nombre_viejo: str, nombre_nuevo: str) -> bool:
    """Renombra `nombre_viejo` -> `nombre_nuevo` dentro de un `menus_construidos` YA GUARDADO
    (mutado in place) -- necesario porque limpiar/fusionar el catálogo (`views/editor_ingredientes
    .py`, `views/configuracion.py`) solo tocaba `recetas` (el banco): un día ya guardado es un
    snapshot completo, no una referencia viva al banco (ver schema.md), así que renombrar ahí NO
    lo alcanza -- el ingrediente viejo queda huérfano para siempre en cualquier día que lo usara,
    aunque el banco ya esté limpio (BUG-013, detectado 2026-08-30: "Leche"/"Leche semi" fusionadas
    a "Leche descremada" en el catálogo y en `recetas`, pero seguían huérfanas en días ya
    guardados -- "Lista del súper" las mostraba como "Sin grupo / libre" en vez de AOA).

    Devuelve True si `nombre_viejo` aparecía en algún ingrediente (y ya mutó `documento`), False si
    no había nada que hacer -- así el caller sabe si vale la pena escribir de vuelta a Mongo.
    Aplica `fusionar_ingredientes_duplicados()` por instancia (mismo caso que BUG-009: la receta
    ya podía tener un ingrediente con el nombre nuevo) y recalcula `actual`/`actual_diario`/
    `delta_diario`/`estado` -- `objetivo_diario` NO se toca, sigue siendo el snapshot original de
    cuando se guardó ese día (ver schema.md)."""
    hubo_cambio = False
    for datos in documento.get("tiempos", {}).values():
        tiempo_cambio = False
        for inst in datos.get("seleccion", []):
            renombrado = False
            for ing in inst["ingredientes"]:
                if ing["alimento"] == nombre_viejo:
                    ing["alimento"] = nombre_nuevo
                    renombrado = True
            if renombrado:
                inst["ingredientes"] = fusionar_ingredientes_duplicados(inst["ingredientes"])
                tiempo_cambio = True
        if tiempo_cambio:
            incluidos = [
                ing
                for inst in datos.get("seleccion", [])
                for ing in inst["ingredientes"]
                if ing.get("incluido", True)
            ]
            datos["actual"] = sumar_por_grupo(incluidos, "grupo_smae", "equivalentes")
            hubo_cambio = True

    if not hubo_cambio:
        return False

    actual_diario: dict[str, int] = {}
    for datos in documento.get("tiempos", {}).values():
        for grupo, cantidad in datos.get("actual", {}).items():
            actual_diario[grupo] = actual_diario.get(grupo, 0) + cantidad
    documento["actual_diario"] = actual_diario
    # Cereal/Leguminosa intercambiables (2026-08-30, a pedido del usuario) -- mismo criterio que
    # "Menú del día" en vivo (views/menu_del_dia.py), para que un día recalculado aquí (por un
    # renombrado en el catálogo) no se vea "sin cuadrar" por algo que ya no cuenta como problema.
    delta_diario = ajustar_delta_por_intercambios(delta_objetivo(documento.get("objetivo_diario", {}), actual_diario))
    documento["delta_diario"] = delta_diario
    documento["estado"] = "completo" if delta_diario and all(v == 0 for v in delta_diario.values()) else "en_progreso"
    return True
