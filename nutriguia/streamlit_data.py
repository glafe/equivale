"""Acceso a Mongo cacheado, compartido entre las páginas de Streamlit (build_your_menu,
editor_recetas). No contiene lógica de negocio — eso vive en nutriguia/validation.py.
"""

import streamlit as st

from nutriguia.db import get_db
from nutriguia.validation import sumar_por_grupo


@st.cache_resource
def db():
    return get_db()


@st.cache_data(ttl=300)
def cargar_personas() -> list[str]:
    return sorted(p["persona"] for p in db().personas.find({}, {"persona": 1}))


@st.cache_data(ttl=300)
def cargar_objetivo(persona: str) -> dict[str, int]:
    doc = db().objetivos.find_one({"persona": persona}, sort=[("vigente_desde", -1)])
    if doc is None:
        return {}
    return sumar_por_grupo(doc["equivalentes_diarios"], "grupo", "cantidad")


@st.cache_data(ttl=300)
def cargar_recetas(tiempo: str | None = None) -> list[dict]:
    filtro = {"tiempo_tipico": tiempo} if tiempo else {}
    return list(db().recetas.find(filtro, {"_id": 0}))


@st.cache_data(ttl=300)
def cargar_catalogo() -> dict[str, dict]:
    docs = db().catalogo_alimentos.find({}, {"_id": 0})
    return {d["alimento"]: d for d in docs}


@st.cache_data(ttl=300)
def cargar_nombres_alimentos() -> list[str]:
    return sorted(cargar_catalogo().keys())


def invalidar_cache_recetas() -> None:
    cargar_recetas.clear()
