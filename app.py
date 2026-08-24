"""EquiVale — "Build your menu" (Fase 3: MVP de un solo tiempo, en memoria, sin guardar a Mongo).

Ver UI-BUILD-YOUR-MENU.md puntos 1-3 para la especificación de interacción.
"""

import re
import uuid
from fractions import Fraction

import streamlit as st

from nutriguia.db import get_db
from nutriguia.validation import (
    delta_objetivo,
    estado_por_grupo,
    paso_equivalente,
    sumar_por_grupo,
)

TIEMPO = "comida"
TIEMPO_LABEL = "Comida"

COLOR_POR_ESTADO = {"exacto": "🟢", "falta": "🟡", "excedido": "🔴"}

RE_FRACCION = re.compile(r"^(\d+)/(\d+)\s*(.*)$")
RE_NUMERO = re.compile(r"^(\d+(?:\.\d+)?)\s*(.*)$")


@st.cache_resource
def _db():
    return get_db()


@st.cache_data(ttl=300)
def _cargar_personas() -> list[str]:
    return sorted(p["persona"] for p in _db().personas.find({}, {"persona": 1}))


@st.cache_data(ttl=300)
def _cargar_objetivo(persona: str) -> dict[str, int]:
    doc = _db().objetivos.find_one({"persona": persona}, sort=[("vigente_desde", -1)])
    if doc is None:
        return {}
    return sumar_por_grupo(doc["equivalentes_diarios"], "grupo", "cantidad")


@st.cache_data(ttl=300)
def _cargar_recetas(tiempo: str) -> list[dict]:
    return list(_db().recetas.find({"tiempo_tipico": tiempo}, {"_id": 0}))


@st.cache_data(ttl=300)
def _cargar_catalogo() -> dict[str, dict]:
    docs = _db().catalogo_alimentos.find({}, {"_id": 0})
    return {d["alimento"]: d for d in docs}


def _formatear_cantidad_real(paso: str, n: int) -> str:
    """paso = 'cantidad_por_equivalente' de un alimento (ej. '30 g', '1/2 taza'). Multiplica por
    n equivalentes cuando el formato es reconocible; si no, muestra el paso tal cual."""
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
        return f"{texto} {resto} ({n} equivalentes)".strip()
    m = RE_NUMERO.match(paso)
    if m:
        val, resto = m.groups()
        valor = float(val) * n
        texto = str(int(valor)) if valor == int(valor) else str(valor)
        return f"{texto} {resto} ({n} equivalentes)".strip()
    return f"{paso} × {n} ({n} equivalentes)"


def _nueva_instancia(receta: dict) -> dict:
    return {
        "instancia_id": str(uuid.uuid4()),
        "receta_id": receta["receta_id"],
        "nombre": receta["nombre"],
        "ingredientes": [
            {
                "alimento": ing["alimento"],
                "grupo_smae": ing["grupo_smae"],
                "equivalentes": ing["equivalentes"],
            }
            for ing in receta["ingredientes"]
        ],
    }


def main() -> None:
    st.set_page_config(page_title="EquiVale — Build your menu", page_icon="🥗")
    st.title("🥗 EquiVale — Build your menu")
    st.caption(f"MVP Fase 3 — un solo tiempo ({TIEMPO_LABEL}), en memoria, sin guardar todavía.")

    personas = _cargar_personas()
    persona = st.selectbox("Persona", personas)

    if st.session_state.get("_persona_actual") != persona:
        st.session_state["_persona_actual"] = persona
        st.session_state[f"seleccion_{TIEMPO}"] = []

    objetivo = _cargar_objetivo(persona)
    catalogo = _cargar_catalogo()

    st.subheader(f"Presupuesto diario de {persona}")
    st.write(
        " · ".join(f"{grupo} {cantidad}" for grupo, cantidad in sorted(objetivo.items()))
    )

    st.divider()
    st.subheader(f"Tiempo: {TIEMPO_LABEL}")

    ver_todas = st.checkbox("Ver recetas de todas las personas", value=False)
    recetas = _cargar_recetas(TIEMPO)
    if not ver_todas:
        recetas = [r for r in recetas if persona in r.get("personas_vistas", [])]

    opciones = {r["receta_id"]: r for r in recetas}
    col1, col2 = st.columns([3, 1])
    with col1:
        receta_id_elegida = st.selectbox(
            "Selecciona una receta",
            options=list(opciones.keys()),
            format_func=lambda rid: opciones[rid]["nombre"],
        )
    if receta_id_elegida:
        preview = opciones[receta_id_elegida]["vector_equivalentes"]
        st.caption("Vector: " + " · ".join(f"{g} {c}" for g, c in sorted(preview.items())))
    with col2:
        st.write("")
        st.write("")
        if st.button("+ Agregar", disabled=receta_id_elegida is None):
            instancia = _nueva_instancia(opciones[receta_id_elegida])
            st.session_state[f"seleccion_{TIEMPO}"].append(instancia)

    seleccion = st.session_state.get(f"seleccion_{TIEMPO}", [])

    for instancia in list(seleccion):
        with st.container(border=True):
            top_l, top_r = st.columns([4, 1])
            top_l.markdown(f"**{instancia['nombre']}**")
            if top_r.button("quitar", key=f"quitar_{instancia['instancia_id']}"):
                seleccion.remove(instancia)
                st.rerun()

            for ing in instancia["ingredientes"]:
                paso = paso_equivalente(ing["alimento"], catalogo)
                c1, c2, c3, c4 = st.columns([3, 1, 3, 1])
                c1.write(ing["alimento"])
                if paso is None:
                    c3.write("(no ajustable)")
                    continue
                if c2.button(
                    "-", key=f"menos_{instancia['instancia_id']}_{ing['alimento']}",
                    disabled=ing["equivalentes"] <= 1,
                ):
                    ing["equivalentes"] -= 1
                    st.rerun()
                c3.write(_formatear_cantidad_real(paso, ing["equivalentes"]))
                if c4.button("+", key=f"mas_{instancia['instancia_id']}_{ing['alimento']}"):
                    ing["equivalentes"] += 1
                    st.rerun()

    st.divider()
    st.subheader("Estado del tiempo")

    ingredientes_actuales = [
        ing for instancia in seleccion for ing in instancia["ingredientes"]
    ]
    actual = sumar_por_grupo(ingredientes_actuales, "grupo_smae", "equivalentes")
    delta = delta_objetivo(objetivo, actual)
    estado = estado_por_grupo(delta)

    for grupo in sorted(set(objetivo) | set(actual)):
        icono = COLOR_POR_ESTADO[estado[grupo]]
        st.write(
            f"{icono} **{grupo}** — objetivo {objetivo.get(grupo, 0)} · "
            f"actual {actual.get(grupo, 0)} · delta {delta[grupo]:+d}"
        )


if __name__ == "__main__":
    main()
