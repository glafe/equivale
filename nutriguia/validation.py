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
