"""fusionar_ingredientes_duplicados() -- datos sintéticos, sin depender de Mongo ni de los menús
reales fuera de git."""

from nutriguia.validation import fusionar_ingredientes_duplicados


def test_sin_duplicados_no_cambia_nada():
    ingredientes = [
        {"alimento": "Pollo", "grupo_smae": "AOA", "equivalentes": 4},
        {"alimento": "Arroz", "grupo_smae": "Cereal", "equivalentes": 2},
    ]
    assert fusionar_ingredientes_duplicados(ingredientes) == ingredientes


def test_fusiona_dos_ocurrencias_sumando_equivalentes():
    ingredientes = [
        {"cantidad": "2 cdt", "alimento": "Crema de cacahuate", "grupo_smae": "Aceite c/p", "equivalentes": 1, "opcional": True},
        {"cantidad": "1/2 tz", "alimento": "Mezcla verdura", "grupo_smae": "Verdura", "equivalentes": 1, "opcional": True},
        {"cantidad": "2 ct", "alimento": "Crema de cacahuate", "grupo_smae": "Aceite c/p", "equivalentes": 1, "opcional": True},
    ]
    resultado = fusionar_ingredientes_duplicados(ingredientes)
    assert len(resultado) == 2
    crema = next(i for i in resultado if i["alimento"] == "Crema de cacahuate")
    assert crema["equivalentes"] == 2
    assert crema["opcional"] is True
    # No debe haber una segunda entrada de "Crema de cacahuate".
    assert sum(1 for i in resultado if i["alimento"] == "Crema de cacahuate") == 1


def test_preserva_orden_de_primera_aparicion():
    ingredientes = [
        {"alimento": "B", "grupo_smae": "Fruta", "equivalentes": 1},
        {"alimento": "A", "grupo_smae": "Cereal", "equivalentes": 1},
        {"alimento": "B", "grupo_smae": "Fruta", "equivalentes": 1},
    ]
    resultado = fusionar_ingredientes_duplicados(ingredientes)
    assert [i["alimento"] for i in resultado] == ["B", "A"]


def test_bandera_opcional_bloqueado_asuncion_se_activa_si_alguna_ocurrencia_la_tiene():
    ingredientes = [
        {"alimento": "X", "grupo_smae": "AOA", "equivalentes": 1},  # sin banderas
        {"alimento": "X", "grupo_smae": "AOA", "equivalentes": 2, "opcional": True, "bloqueado": True, "asuncion": True},
    ]
    resultado = fusionar_ingredientes_duplicados(ingredientes)
    assert len(resultado) == 1
    assert resultado[0]["equivalentes"] == 3
    assert resultado[0]["opcional"] is True
    assert resultado[0]["bloqueado"] is True
    assert resultado[0]["asuncion"] is True


def test_no_cambia_el_total_de_equivalentes_del_grupo():
    """La suma por grupo antes y después de fusionar debe ser idéntica -- fusionar es un cambio
    de forma, no de contenido nutricional."""
    from nutriguia.validation import sumar_por_grupo

    ingredientes = [
        {"alimento": "Res molida", "grupo_smae": "AOA", "equivalentes": 5, "opcional": True},
        {"alimento": "Res molida", "grupo_smae": "AOA", "equivalentes": 5, "opcional": True},
        {"alimento": "Pasta cocida", "grupo_smae": "Cereal", "equivalentes": 2},
    ]
    antes = sumar_por_grupo(ingredientes, "grupo_smae", "equivalentes")
    despues = sumar_por_grupo(fusionar_ingredientes_duplicados(ingredientes), "grupo_smae", "equivalentes")
    assert antes == despues == {"AOA": 10, "Cereal": 2}
