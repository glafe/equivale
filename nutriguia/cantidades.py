"""Escalar una 'cantidad_por_equivalente' del catálogo por N equivalentes (ej. '30 g' x3 -> '90
g'). Lógica de presentación (parseo de texto libre), no aritmética de equivalentes -- eso vive en
validation.py. Compartido entre views/menu_del_dia.py y views/editor_recetas.py.
"""

import re
from fractions import Fraction

from nutriguia.validation import paso_equivalente

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


def cantidad_real(alimento: str, equivalentes: int, catalogo: dict) -> str:
    """Cantidad real de `equivalentes` equivalentes de `alimento`, resuelta contra el catálogo
    (`paso_equivalente()` + `escalar_cantidad()`) -- fallback "N equiv." si el alimento no está en
    el catálogo (ej. una referencia huérfana), en vez de tronar. Factorizado 2026-08-30 (antes
    vivía duplicado como `_cantidad_real()` en `nutriguia/html_semanal.py`) para compartirlo con
    `nutriguia/html_lista_super.py`."""
    paso = paso_equivalente(alimento, catalogo)
    if paso is None:
        return f"{equivalentes} equiv."
    return escalar_cantidad(paso, equivalentes)


def formatear_decimal_como_fraccion(valor: float) -> str:
    """Convierte un decimal (ej. 0.333333333333333, 1.5, 2.0) a la notación de fracción mixta que
    usa el catálogo (ej. '1/3', '1 1/2', '2'). Usado al importar una fila de SMAE_CONSULTA.csv,
    donde 'Cantidad sugerida' viene como decimal de Excel en vez de fracción legible."""
    frac = Fraction(valor).limit_denominator(100)
    entero, resto = divmod(frac.numerator, frac.denominator)
    if resto == 0:
        return str(entero)
    if entero == 0:
        return f"{resto}/{frac.denominator}"
    return f"{entero} {resto}/{frac.denominator}"
