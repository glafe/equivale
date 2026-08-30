import pytest

from nutriguia.cantidades import cantidad_real, formatear_decimal_como_fraccion

CATALOGO_EJEMPLO = {
    "Avena en hojuelas": {"alimento": "Avena en hojuelas", "grupo": "Cereal", "cantidad_por_equivalente": "1/4 taza"},
    "Pollo": {"alimento": "Pollo", "grupo": "AOA", "cantidad_por_equivalente": "30 g"},
}


def test_cantidad_real_escala_contra_el_catalogo():
    assert cantidad_real("Avena en hojuelas", 2, CATALOGO_EJEMPLO) == "1/2 taza"
    assert cantidad_real("Pollo", 3, CATALOGO_EJEMPLO) == "90 g"


def test_cantidad_real_usa_fallback_de_equivalentes_si_no_esta_en_catalogo():
    """Ej. una referencia huérfana -- no debe tronar, cae a "N equiv."."""
    assert cantidad_real("Fruta libre", 1, CATALOGO_EJEMPLO) == "1 equiv."


@pytest.mark.parametrize(
    "valor,esperado",
    [
        (2.0, "2"),
        (0.5, "1/2"),
        (0.25, "1/4"),
        (1.5, "1 1/2"),
        (0.333333333333333, "1/3"),
        (1.0, "1"),
    ],
)
def test_formatear_decimal_como_fraccion(valor, esperado):
    assert formatear_decimal_como_fraccion(valor) == esperado
