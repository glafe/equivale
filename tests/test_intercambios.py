"""Cereal/Leguminosa intercambiables en "Menú del día" (2026-08-30, a pedido del usuario: "un
cereal puede ser intercambiable por 1 leguminosa"). Datos sintéticos, no reales de ninguna
persona."""

from nutriguia.validation import ajustar_delta_por_intercambios, delta_objetivo, estado_por_grupo


def test_no_cambia_nada_si_ningun_par_esta_en_desequilibrio():
    delta = {"Cereal": 2, "Leguminosa": 1, "AOA": 0}
    assert ajustar_delta_por_intercambios(delta) == delta


def test_leguminosa_de_sobra_cubre_parte_del_cereal_faltante():
    # Falta 2 Cereal, sobra 1 Leguminosa -- la Leguminosa cubre 1, sigue faltando 1 Cereal.
    delta = {"Cereal": 2, "Leguminosa": -1}
    assert ajustar_delta_por_intercambios(delta) == {"Cereal": 1, "Leguminosa": 0}


def test_se_cancelan_por_completo_si_faltan_y_sobran_lo_mismo():
    delta = {"Cereal": 1, "Leguminosa": -1}
    ajustado = ajustar_delta_por_intercambios(delta)
    assert ajustado == {"Cereal": 0, "Leguminosa": 0}
    assert estado_por_grupo(ajustado) == {"Cereal": "exacto", "Leguminosa": "exacto"}


def test_funciona_en_cualquier_orden_del_par():
    # Mismo caso, pero ahora es el Cereal el que sobra y la Leguminosa la que falta.
    delta = {"Cereal": -1, "Leguminosa": 2}
    assert ajustar_delta_por_intercambios(delta) == {"Cereal": 0, "Leguminosa": 1}


def test_no_hace_nada_si_ambos_faltan_o_ambos_sobran():
    assert ajustar_delta_por_intercambios({"Cereal": 2, "Leguminosa": 1}) == {"Cereal": 2, "Leguminosa": 1}
    assert ajustar_delta_por_intercambios({"Cereal": -2, "Leguminosa": -1}) == {"Cereal": -2, "Leguminosa": -1}


def test_no_truena_si_falta_uno_de_los_dos_grupos():
    delta = {"Cereal": 1}
    assert ajustar_delta_por_intercambios(delta) == {"Cereal": 1}


def test_otros_grupos_no_se_tocan():
    delta = {"Cereal": 1, "Leguminosa": -1, "AOA": 3, "Fruta": -2}
    ajustado = ajustar_delta_por_intercambios(delta)
    assert ajustado["AOA"] == 3
    assert ajustado["Fruta"] == -2


def test_integracion_con_delta_objetivo_caso_del_usuario():
    """El caso concreto que motivó esto: alguien comió 1 Cereal de menos y 1 Leguminosa de más (o
    viceversa) -- antes se veía como "sin cuadrar" en ambos grupos, ahora debe verse exacto."""
    objetivo = {"Cereal": 9, "Leguminosa": 1, "AOA": 15}
    actual = {"Cereal": 8, "Leguminosa": 2, "AOA": 15}
    delta = delta_objetivo(objetivo, actual)
    ajustado = ajustar_delta_por_intercambios(delta)
    estado = estado_por_grupo(ajustado)
    assert estado == {"Cereal": "exacto", "Leguminosa": "exacto", "AOA": "exacto"}
