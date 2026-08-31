"""Revisión de "Chequeos automáticos" tras las limpiezas recientes (2026-08-31, a pedido del
usuario): mismo caso que BUG-013 (renombrar en el catálogo no cascaba a días ya guardados), pero
para ingredientes duplicados dentro de una misma instancia de un día ya guardado -- puede pasar si
el día se guardó ANTES de que la receta original se corrigiera en el banco (ver BUG-009). Datos
sintéticos, no reales de ninguna persona."""

from nutriguia.validation import fusionar_duplicados_en_menu_guardado


def _dia_con_duplicado() -> dict:
    return {
        "persona": "Persona de prueba",
        "fecha": "2026-08-31",
        "nombre": "Menú de prueba",
        "objetivo_diario": {"AOA": 4, "Cereal": 2},
        "tiempos": {
            "comida": {
                "seleccion": [
                    {
                        "receta_id": "espagueti-v1",
                        "nombre": "Espagueti Boloñesa",
                        "ingredientes": [
                            {"alimento": "Res molida", "grupo_smae": "AOA", "equivalentes": 3, "incluido": True},
                            {"alimento": "Res molida", "grupo_smae": "AOA", "equivalentes": 1, "incluido": True},
                            {"alimento": "Pasta cocida", "grupo_smae": "Cereal", "equivalentes": 2, "incluido": True},
                        ],
                    }
                ],
                "actual": {"AOA": 4, "Cereal": 2},
            }
        },
        "actual_diario": {"AOA": 4, "Cereal": 2},
        "delta_diario": {"AOA": 0, "Cereal": 0},
        "estado": "completo",
    }


def test_fusiona_duplicados_y_no_cambia_el_total_por_grupo():
    doc = _dia_con_duplicado()
    cambio = fusionar_duplicados_en_menu_guardado(doc, "comida", 0)
    assert cambio is True
    ingredientes = doc["tiempos"]["comida"]["seleccion"][0]["ingredientes"]
    nombres = [i["alimento"] for i in ingredientes]
    assert nombres.count("Res molida") == 1
    fusionada = next(i for i in ingredientes if i["alimento"] == "Res molida")
    assert fusionada["equivalentes"] == 4
    # El total por grupo del tiempo/día no debe cambiar -- es la misma cantidad repartida distinto.
    assert doc["tiempos"]["comida"]["actual"] == {"AOA": 4, "Cereal": 2}
    assert doc["actual_diario"] == {"AOA": 4, "Cereal": 2}
    assert doc["estado"] == "completo"


def test_no_cambia_nada_si_no_hay_duplicados():
    doc = _dia_con_duplicado()
    fusionar_duplicados_en_menu_guardado(doc, "comida", 0)  # fusiona la primera vez
    antes = {k: (v.copy() if isinstance(v, dict) else v) for k, v in doc.items()}
    cambio = fusionar_duplicados_en_menu_guardado(doc, "comida", 0)  # ya no hay nada que fusionar
    assert cambio is False
    assert doc["actual_diario"] == antes["actual_diario"]


def test_indice_o_tiempo_invalido_no_truena():
    doc = _dia_con_duplicado()
    assert fusionar_duplicados_en_menu_guardado(doc, "desayuno", 0) is False
    assert fusionar_duplicados_en_menu_guardado(doc, "comida", 5) is False
