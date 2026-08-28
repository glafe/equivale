from nutriguia.texto import normalizar_busqueda


def test_normalizar_quita_acentos_y_mayusculas():
    assert normalizar_busqueda("Atún") == "atun"
    assert normalizar_busqueda("JÍCAMA") == "jicama"


def test_normalizar_permite_coincidir_sin_acento():
    assert normalizar_busqueda("atun") in normalizar_busqueda("Atún en agua")
