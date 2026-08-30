"""SMAE_CONSULTA.csv está commiteado (es la tabla oficial pública, sin datos de personas reales
-- ver .gitignore), así que estas pruebas corren en cualquier clon del repo, no solo con los
datos reales de nutriguia/import_data.py."""

from nutriguia.smae_csv import (
    NO_SOPORTADO,
    UMBRAL_PROTEINA_LECHE_AOA,
    _grupo_desde_tipo_equivalente,
    _reparar_mojibake,
    cargar_filas_smae,
)
from nutriguia.texto import normalizar_busqueda


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
    # "Leche con azúcar" nunca se soporta, sin importar la proteína.
    assert _grupo_desde_tipo_equivalente("Leche con azúcar", 9.0) == NO_SOPORTADO


def test_leche_se_cataloga_como_aoa_solo_con_proteina_suficiente():
    for tipo in ("Leche descremada", "Leche semidescremada", "Leche entera"):
        assert _grupo_desde_tipo_equivalente(tipo, UMBRAL_PROTEINA_LECHE_AOA) == "AOA"
        assert _grupo_desde_tipo_equivalente(tipo, UMBRAL_PROTEINA_LECHE_AOA - 0.1) == NO_SOPORTADO
        assert _grupo_desde_tipo_equivalente(tipo, None) == NO_SOPORTADO


def test_reparar_mojibake_recupera_utf8_mal_leido_como_latin1():
    """BUG-012: bytes UTF-8 de "é" (0xC3 0xA9) leídos como Latin-1 dan "Ã©" -- debe recuperar
    "é"."""
    mojibake = "Caf\xc3\xa9"  # exactamente lo que produce open(..., encoding="latin1") sobre
    # los bytes UTF-8 de "Café" (0x43 0x61 0x66 0xC3 0xA9).
    assert _reparar_mojibake(mojibake) == "Café"


def test_reparar_mojibake_no_toca_texto_latin1_genuino():
    """Un acento decodificado correctamente como Latin-1 (ej. "ú" = U+00FA, un solo byte 0xFA en
    el CSV original) no debe alterarse -- re-decodificar esos bytes como UTF-8 debe fallar
    (0xFA no es un byte de inicio UTF-8 válido seguido de "n"), así que se conserva tal cual."""
    assert _reparar_mojibake("Atún") == "Atún"
    assert _reparar_mojibake("Acelga cruda") == "Acelga cruda"


def test_cafe_en_polvo_aparece_y_se_encuentra_buscando_cafe():
    """BUG-012: "Café en polvo" existe en el CSV (categoría "Alimentos libres en energía", libre)
    pero antes de reparar el mojibake, "Café" salía como "CafÃ©" -- normalizar_busqueda() le
    quitaba mal el acento (daba "cafa", no "cafe") y buscar "café" no lo encontraba. Ahora sí."""
    filas = cargar_filas_smae()
    alimentos = {f["alimento"] for f in filas}
    assert "Café en polvo" in alimentos
    assert "CafÃ©" not in " ".join(alimentos)  # ningún alimento debe quedar con mojibake

    encontrados = [f["alimento"] for f in filas if normalizar_busqueda("café") in normalizar_busqueda(f["alimento"])]
    assert "Café en polvo" in encontrados


def test_filas_de_leche_con_proteina_suficiente_llegan_como_aoa():
    filas = cargar_filas_smae()
    # "Leche descremada" (1 taza) aporta 8.4 g de proteína -- por arriba del umbral.
    leche = next(f for f in filas if f["alimento"] == "Leche descremada")
    assert leche["grupo_smae"] == "AOA"
    alimentos = {f["alimento"] for f in filas}
    # "Yoghur bajo en grasa" (0.33 taza, categoría "Leche descremada") aporta solo 2.7 g -- no
    # alcanza el umbral, no debe aparecer.
    assert "Yoghur bajo en grasa" not in alimentos
