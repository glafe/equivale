"""Escalar una 'cantidad_por_equivalente' del catálogo por N equivalentes (ej. '30 g' x3 -> '90
g'). Lógica de presentación (parseo de texto libre), no aritmética de equivalentes -- eso vive en
validation.py. Compartido entre views/build_your_menu.py y views/editor_recetas.py.
"""

import re
from fractions import Fraction

RE_FRACCION = re.compile(r"^(\d+)/(\d+)\s*(.*)$")
RE_NUMERO = re.compile(r"^(\d+(?:\.\d+)?)\s*(.*)$")


def escalar_cantidad(paso: str, n: int) -> str:
    """paso = 'cantidad_por_equivalente' de un alimento (ej. '30 g', '1/2 taza'). Multiplica por
    n equivalentes cuando el formato es reconocible (fracción o número al inicio); si no, muestra
    el paso tal cual con un '× n'."""
    m = RE_FRACCION.match(paso)
    if m:
        num, den, resto = m.groups()
        valor = Fraction(int(num), int(den)) * n
        entero, resto_frac = divmod(valor.numerator, valor.denominator)
        if resto_frac == 0:
            texto = str(entero)
        elif entero == 0:
            texto = f"{resto_frac}/{valor.denominator}"
        else:
            texto = f"{entero} {resto_frac}/{valor.denominator}"
        return f"{texto} {resto}".strip()
    m = RE_NUMERO.match(paso)
    if m:
        val, resto = m.groups()
        valor = float(val) * n
        texto = str(int(valor)) if valor == int(valor) else str(valor)
        return f"{texto} {resto}".strip()
    return f"{paso} × {n}"
