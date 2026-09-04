"""Acceso a SQLite cacheado, compartido entre las páginas de Streamlit (menu_del_dia,
editor_recetas). No contiene lógica de negocio — eso vive en nutriguia/validation.py.
"""

import streamlit as st

from nutriguia import db as bd
from nutriguia.smae_csv import cargar_filas_smae as _cargar_filas_smae
from nutriguia.validation import sumar_por_grupo


@st.cache_resource
def db():
    return bd.get_conn()


@st.cache_data(ttl=300)
def cargar_personas() -> list[str]:
    return bd.listar_personas(db())


@st.cache_data(ttl=300)
def cargar_objetivo(persona: str) -> dict[str, int]:
    doc = bd.obtener_objetivo(db(), persona)
    if doc is None:
        return {}
    return sumar_por_grupo(doc["equivalentes_diarios"], "grupo", "cantidad")


@st.cache_data(ttl=300)
def cargar_recetas(tiempo: str | None = None) -> list[dict]:
    return bd.listar_recetas(db(), tiempo)


@st.cache_data(ttl=300)
def cargar_catalogo() -> dict[str, dict]:
    return {d["alimento"]: d for d in bd.listar_catalogo(db())}


@st.cache_data(ttl=300)
def cargar_nombres_alimentos() -> list[str]:
    return sorted(cargar_catalogo().keys())


@st.cache_data
def cargar_filas_smae() -> list[dict]:
    """Sin ttl: el CSV no cambia mientras el servidor corre (a diferencia de Mongo)."""
    return _cargar_filas_smae()


def invalidar_cache_recetas() -> None:
    cargar_recetas.clear()


def invalidar_cache_personas() -> None:
    cargar_personas.clear()
    cargar_objetivo.clear()


def invalidar_cache_catalogo() -> None:
    cargar_catalogo.clear()
    cargar_nombres_alimentos.clear()
