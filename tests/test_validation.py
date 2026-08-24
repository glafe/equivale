import json
from pathlib import Path

import pytest

from nutriguia.validation import validar_menu

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "Json-outputs-sin-notas"
ARCHIVOS = sorted(p for p in DATA_DIR.glob("*.json") if p.name != "catalogo-alimentos.json")


def _casos():
    casos = []
    for archivo in ARCHIVOS:
        data = json.loads(archivo.read_text(encoding="utf-8"))
        for variante in data["menus"]:
            id_caso = f"{archivo.stem}-menu{variante['menu_id']}"
            casos.append(pytest.param(archivo.name, data["persona"], variante, id=id_caso))
    return casos


@pytest.mark.parametrize("nombre_archivo,persona,variante", _casos())
def test_menu_historico_valido(nombre_archivo, persona, variante):
    es_valido_dia, delta_diario, tiempos_invalidos = validar_menu(variante)
    assert es_valido_dia, (
        f"{nombre_archivo} ({persona}, menu_id={variante['menu_id']}): "
        f"delta_diario={delta_diario}"
    )
    assert tiempos_invalidos == [], (
        f"{nombre_archivo} ({persona}, menu_id={variante['menu_id']}): "
        f"tiempos inválidos={tiempos_invalidos}"
    )


def test_se_encontraron_17_archivos():
    assert len(ARCHIVOS) == 17
