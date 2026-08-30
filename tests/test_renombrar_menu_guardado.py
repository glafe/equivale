"""BUG-013: renombrar/fusionar un alimento del catálogo solo tocaba `recetas` (el banco) -- un
día ya guardado en `menus_construidos` es un snapshot completo, no una referencia viva, así que el
nombre viejo quedaba huérfano para siempre ahí. `renombrar_ingrediente_en_menu_guardado()` cierra
esa cascada. Datos sintéticos, no reales de ninguna persona."""

from nutriguia.validation import renombrar_ingrediente_en_menu_guardado


def _dia(equivalentes_leche: int = 1, incluido: bool = True) -> dict:
    return {
        "persona": "Persona de prueba",
        "fecha": "2026-08-31",
        "nombre": "Menú de prueba",
        "objetivo_diario": {"AOA": 3, "Cereal": 2},
        "tiempos": {
            "desayuno": {
                "seleccion": [
                    {
                        "receta_id": "avena-v1",
                        "nombre": "Avena con leche",
                        "ingredientes": [
                            {
                                "alimento": "Leche",
                                "grupo_smae": "AOA",
                                "equivalentes": equivalentes_leche,
                                "incluido": incluido,
                            },
                            {"alimento": "Avena", "grupo_smae": "Cereal", "equivalentes": 2, "incluido": True},
                        ],
                    }
                ],
                "actual": {"AOA": equivalentes_leche if incluido else 0, "Cereal": 2},
            }
        },
        "actual_diario": {"AOA": equivalentes_leche if incluido else 0, "Cereal": 2},
        "delta_diario": {},
        "estado": "en_progreso",
    }


def test_no_cambia_nada_si_el_nombre_viejo_no_aparece():
    doc = _dia()
    original = {k: (v.copy() if isinstance(v, dict) else v) for k, v in doc.items()}
    cambio = renombrar_ingrediente_en_menu_guardado(doc, "Yogur", "Leche descremada")
    assert cambio is False
    assert doc["tiempos"]["desayuno"]["seleccion"][0]["ingredientes"][0]["alimento"] == "Leche"
    assert doc["actual_diario"] == original["actual_diario"]


def test_renombra_y_recalcula_actual_diario_y_delta():
    doc = _dia(equivalentes_leche=1)
    cambio = renombrar_ingrediente_en_menu_guardado(doc, "Leche", "Leche descremada")
    assert cambio is True
    ing = doc["tiempos"]["desayuno"]["seleccion"][0]["ingredientes"][0]
    assert ing["alimento"] == "Leche descremada"
    assert doc["tiempos"]["desayuno"]["actual"] == {"AOA": 1, "Cereal": 2}
    assert doc["actual_diario"] == {"AOA": 1, "Cereal": 2}
    assert doc["delta_diario"] == {"AOA": 2, "Cereal": 0}
    assert doc["estado"] == "en_progreso"


def test_objetivo_diario_no_se_toca():
    doc = _dia()
    objetivo_original = dict(doc["objetivo_diario"])
    renombrar_ingrediente_en_menu_guardado(doc, "Leche", "Leche descremada")
    assert doc["objetivo_diario"] == objetivo_original


def test_estado_completo_si_el_delta_da_todo_cero_tras_renombrar():
    doc = _dia(equivalentes_leche=3)  # AOA 3 = objetivo AOA 3, Cereal 2 = objetivo Cereal 2
    renombrar_ingrediente_en_menu_guardado(doc, "Leche", "Leche descremada")
    assert doc["delta_diario"] == {"AOA": 0, "Cereal": 0}
    assert doc["estado"] == "completo"


def test_ingrediente_no_incluido_no_cuenta_en_actual():
    doc = _dia(equivalentes_leche=5, incluido=False)
    renombrar_ingrediente_en_menu_guardado(doc, "Leche", "Leche descremada")
    assert doc["tiempos"]["desayuno"]["actual"] == {"Cereal": 2}
    assert doc["actual_diario"] == {"Cereal": 2}


def test_fusiona_si_la_misma_instancia_ya_tenia_el_nombre_nuevo():
    """Mismo caso que BUG-009, pero dentro de un día ya guardado en vez de en el banco de
    recetas."""
    doc = _dia()
    doc["tiempos"]["desayuno"]["seleccion"][0]["ingredientes"].append(
        {"alimento": "Leche descremada", "grupo_smae": "AOA", "equivalentes": 2, "incluido": True}
    )
    cambio = renombrar_ingrediente_en_menu_guardado(doc, "Leche", "Leche descremada")
    assert cambio is True
    ingredientes = doc["tiempos"]["desayuno"]["seleccion"][0]["ingredientes"]
    nombres = [i["alimento"] for i in ingredientes]
    assert nombres.count("Leche descremada") == 1  # fusionadas en una sola fila
    fusionada = next(i for i in ingredientes if i["alimento"] == "Leche descremada")
    assert fusionada["equivalentes"] == 3  # 1 (renombrada) + 2 (ya existente)
