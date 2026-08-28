"""Normalización de texto para búsquedas/comparaciones insensibles a acentos y mayúsculas (ej.
"atun" debe encontrar "Atún"). No es lógica de negocio -- solo texto, compartido entre
nutriguia/smae_csv.py y las páginas del editor de ingredientes.
"""

import unicodedata


def normalizar_busqueda(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sin_acentos.strip().lower()
