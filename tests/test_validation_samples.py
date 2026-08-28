"""Regresión de validar_menu() contra datos 100% ficticios, committeados en el repo.

A diferencia de test_validation.py (que necesita los 17 menús históricos reales, fuera de git),
este archivo siempre corre en un clon fresco del repo público -- ver data/samples/.
"""
import json
from pathlib import Path

import pytest

from nutriguia.validation import validar_menu

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"
ARCHIVOS = sorted(DATA_DIR.glob("*.json"))


def _casos():
    casos = []
    for archivo in ARCHIVOS:
        data = json.loads(archivo.read_text(encoding="utf-8"))
        for variante in data["menus"]:
            id_caso = f"{archivo.stem}-menu{variante['menu_id']}"
            casos.append(pytest.param(archivo.name, data["persona"], variante, id=id_caso))
    return casos


@pytest.mark.parametrize("nombre_archivo,persona,variante", _casos())
def test_menu_sintetico_valido(nombre_archivo, persona, variante):
    es_valido_dia, delta_diario, tiempos_invalidos = validar_menu(variante)
    assert es_valido_dia, (
        f"{nombre_archivo} ({persona}, menu_id={variante['menu_id']}): "
        f"delta_diario={delta_diario}"
    )
    assert tiempos_invalidos == [], (
        f"{nombre_archivo} ({persona}, menu_id={variante['menu_id']}): "
        f"tiempos inválidos={tiempos_invalidos}"
    )


def test_hay_al_menos_un_archivo_de_muestra():
    assert len(ARCHIVOS) >= 1
