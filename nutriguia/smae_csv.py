"""Lectura de SMAE_CONSULTA.csv (tabla oficial SMAE -- información pública, no de personas
reales, ver README) para el botón "Agregar de SMAE" del editor de ingredientes. Solo lectura: la
app nunca escribe de vuelta a este archivo.

El archivo tiene más categorías ("Tipo Equivalente") que los 7 grupos canónicos que este proyecto
usa (ver CLAUDE.md) -- Azúcares y Bebidas alcohólicas no tienen equivalente directo y se excluyen
del picker; si algún día hace falta soportarlas, es una decisión de extender los 7 grupos
canónicos, no algo para improvisar aquí. Leche (descremada/semidescremada/entera) es un caso
aparte, a pedido del usuario (2026-08-29): SÍ se soporta, catalogada como AOA, pero solo la
porción que de verdad aporta suficiente proteína como para contar como tal -- ver
`UMBRAL_PROTEINA_LECHE_AOA`. "Leche con azúcar" (helados, malteadas, leches saborizadas) se queda
fuera a propósito, no es la misma decisión que la leche simple. La clasificación por categoría se
hace por texto normalizado (sin acentos/mayúsculas) en vez de comparar el texto exacto, porque el
CSV mezcla más de una codificación de caracteres entre secciones (algunas filas vienen en Latin-1,
otras no) y comparar así es robusto a eso; los nombres de alimento en sí se decodifican como
Latin-1 (correcto para la gran mayoría) y pueden salir con acentos mal formados en un puñado de
filas -- no se persiguió exhaustivamente, mismo criterio que la regla 9 de CLAUDE.md.
"""

import csv
from pathlib import Path

from nutriguia.cantidades import formatear_decimal_como_fraccion
from nutriguia.texto import normalizar_busqueda

SMAE_CSV_PATH = Path(__file__).resolve().parent.parent / "SMAE_CONSULTA.csv"

NO_SOPORTADO = "no_soportado"  # Azúcares / "Leche con azúcar" / Alcohol -- sin grupo canónico

# Categorías de leche simple que SÍ se soportan (a pedido del usuario, 2026-08-29) -- deliberadamente
# NO incluye "Leche con azúcar" (helados, malteadas, leches saborizadas: otra decisión).
TIPOS_LECHE_SOPORTADOS = {"leche descremada", "leche semidescremada", "leche entera"}

# Gramos de proteína mínimos que debe aportar la PORCIÓN sugerida de una fila de leche para
# catalogarse como AOA -- por debajo de esto, la porción es sobre todo carbohidrato/grasa y no
# aporta lo que se espera de un equivalente de AOA (a pedido del usuario, 2026-08-29).
UMBRAL_PROTEINA_LECHE_AOA = 7.0


def _grupo_desde_tipo_equivalente(tipo: str, proteina_g: float | None = None) -> str | None:
    """None = libre (sin grupo, ej. especias/agua). NO_SOPORTADO = categoría SMAE sin equivalente
    entre los 7 grupos canónicos de este proyecto, o una fila de leche cuya porción no alcanza
    `UMBRAL_PROTEINA_LECHE_AOA` de proteína. `proteina_g` solo importa para las categorías de leche
    soportadas -- se ignora para el resto."""
    t = normalizar_busqueda(tipo)
    if t in TIPOS_LECHE_SOPORTADOS:
        if proteina_g is not None and proteina_g >= UMBRAL_PROTEINA_LECHE_AOA:
            return "AOA"
        return NO_SOPORTADO
    if t.startswith("cereales"):
        return "Cereal"
    if t.startswith("a.o.a") or t.startswith("aoa"):
        return "AOA"
    if t == "frutas":
        return "Fruta"
    if t == "verdura":
        return "Verdura"
    if t.startswith("aceites y grasas") and "prote" in t:
        return "Aceite c/p"
    if t == "aceites y grasas":
        return "Aceite s/p"
    if t == "leguminosas":
        return "Leguminosa"
    if t.startswith("alimentos libres"):
        return None
    return NO_SOPORTADO


def cargar_filas_smae() -> list[dict]:
    """Una entrada por fila soportada del CSV: {alimento, grupo_smae, cantidad_por_equivalente,
    tipo_original}. `grupo_smae` es None para alimentos libres. Se saltan encabezados repetidos
    (el CSV trae varias secciones, cada una con su propio encabezado) y categorías NO_SOPORTADAS
    (incluye filas de leche cuya porción no alcanza `UMBRAL_PROTEINA_LECHE_AOA` de proteína)."""
    filas = []
    with SMAE_CSV_PATH.open(encoding="latin1", newline="") as f:
        for r in csv.DictReader(f):
            alimento = (r.get("ALIMENTOS") or "").strip()
            tipo = (r.get("Tipo Equivalente") or "").strip()
            if not alimento or alimento == "ALIMENTOS" or not tipo:
                continue
            try:
                proteina = float(r.get("Proteina (g)", ""))
            except ValueError:
                proteina = None
            grupo = _grupo_desde_tipo_equivalente(tipo, proteina)
            if grupo == NO_SOPORTADO:
                continue
            try:
                cantidad = float(r["Cantidad sugerida"])
            except (KeyError, ValueError):
                continue
            unidad = (r.get("Unidad") or "").strip()
            cantidad_texto = f"{formatear_decimal_como_fraccion(cantidad)} {unidad}".strip()
            filas.append(
                {
                    "alimento": alimento,
                    "grupo_smae": grupo,
                    "cantidad_por_equivalente": cantidad_texto,
                    "tipo_original": tipo,
                }
            )
    return filas
