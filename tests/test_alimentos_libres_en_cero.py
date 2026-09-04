"""alimentos_libres_en_cero() / corregir_alimentos_libres_en_cero() -- KC-003 en BUGS.md, datos
sintéticos sin depender de Mongo/SQLite reales."""

from nutriguia.validation import alimentos_libres_en_cero, corregir_alimentos_libres_en_cero


def test_sin_libres_en_cero_no_encuentra_nada():
    ingredientes = [
        {"alimento": "Pollo", "grupo_smae": "AOA", "equivalentes": 4},
        {"alimento": "Canela en polvo", "grupo_smae": None, "equivalentes": 1},
    ]
    assert alimentos_libres_en_cero(ingredientes) == []
    assert corregir_alimentos_libres_en_cero(ingredientes) == ingredientes


def test_detecta_libre_en_cero_pero_ignora_grupo_real_en_cero():
    ingredientes = [
        {"alimento": "Limón y tajín", "grupo_smae": None, "equivalentes": 0},
        {"alimento": "Pollo", "grupo_smae": "AOA", "equivalentes": 0},  # dato sucio distinto, no aplica aquí
    ]
    assert alimentos_libres_en_cero(ingredientes) == ["Limón y tajín"]


def test_corrige_solo_los_libres_en_cero_a_uno():
    ingredientes = [
        {"alimento": "Limón y tajín", "grupo_smae": None, "equivalentes": 0, "cantidad": "al gusto"},
        {"alimento": "Pollo", "grupo_smae": "AOA", "equivalentes": 0},
        {"alimento": "Canela en polvo", "grupo_smae": None, "equivalentes": 1},
    ]
    corregidos = corregir_alimentos_libres_en_cero(ingredientes)
    assert corregidos[0]["equivalentes"] == 1
    assert corregidos[0]["cantidad"] == "al gusto"  # el resto del ingrediente no se toca
    assert corregidos[1]["equivalentes"] == 0  # grupo real en 0 no es competencia de esta función
    assert corregidos[2]["equivalentes"] == 1  # ya estaba bien, no cambia
    assert alimentos_libres_en_cero(ingredientes) == ["Limón y tajín"]  # no muta el original


def test_no_duplica_nombres_repetidos():
    ingredientes = [
        {"alimento": "Canela en polvo", "grupo_smae": None, "equivalentes": 0},
        {"alimento": "Canela en polvo", "grupo_smae": None, "equivalentes": 0},
    ]
    assert alimentos_libres_en_cero(ingredientes) == ["Canela en polvo"]
