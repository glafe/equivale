"""SMAE_CONSULTA.csv está commiteado (es la tabla oficial pública, sin datos de personas reales
-- ver .gitignore), así que estas pruebas corren en cualquier clon del repo, no solo con los
datos reales de nutriguia/import_data.py."""

from nutriguia.smae_csv import NO_SOPORTADO, _grupo_desde_tipo_equivalente, cargar_filas_smae


def test_cargar_filas_smae_no_esta_vacio():
    filas = cargar_filas_smae()
    assert len(filas) > 1000


def test_fila_conocida_con_grupo():
    filas = cargar_filas_smae()
    acelga = next(f for f in filas if f["alimento"] == "Acelga cruda")
    assert acelga["grupo_smae"] == "Verdura"
    assert acelga["cantidad_por_equivalente"] == "2 taza"


def test_alimento_libre_no_tiene_grupo():
    filas = cargar_filas_smae()
    agua = next(f for f in filas if f["alimento"] == "Agua")
    assert agua["grupo_smae"] is None


def test_categorias_no_soportadas_excluidas():
    alimentos = {f["alimento"] for f in cargar_filas_smae()}
    # "Whisky" es la última fila del CSV, categoría "Bebidas alcoholicas" (no soportada).
    assert "Whisky" not in alimentos


def test_clasificacion_por_categoria():
    assert _grupo_desde_tipo_equivalente("Cereales sin grasa") == "Cereal"
    assert _grupo_desde_tipo_equivalente("Cereales con grasa") == "Cereal"
    assert _grupo_desde_tipo_equivalente("A.O.A Alto en grasa") == "AOA"
    assert _grupo_desde_tipo_equivalente("Frutas") == "Fruta"
    assert _grupo_desde_tipo_equivalente("Verdura") == "Verdura"
    assert _grupo_desde_tipo_equivalente("Leguminosas") == "Leguminosa"
    assert _grupo_desde_tipo_equivalente("Aceites y grasas") == "Aceite s/p"
    assert _grupo_desde_tipo_equivalente("Bebidas alcoholicas") == NO_SOPORTADO
    assert _grupo_desde_tipo_equivalente("Leche entera") == NO_SOPORTADO
