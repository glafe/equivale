import pytest

from nutriguia.cantidades import formatear_decimal_como_fraccion


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
