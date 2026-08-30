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
