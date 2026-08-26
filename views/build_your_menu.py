"""EquiVale — "Build your menu" (Fase 3 MVP: un solo tiempo, en memoria, sin guardar a Mongo).

Ver UI-BUILD-YOUR-MENU.md puntos 1-3 para la especificación de interacción.
"""

import uuid

import streamlit as st

from nutriguia.cantidades import escalar_cantidad
from nutriguia.colores import GRUPO_ETIQUETA, chip_html
from nutriguia.streamlit_data import cargar_catalogo, cargar_objetivo, cargar_personas, cargar_recetas
from nutriguia.validation import (
    delta_objetivo,
    estado_por_grupo,
    paso_equivalente,
    sumar_por_grupo,
)

TIEMPO = "comida"
TIEMPO_LABEL = "Comida"

ICONO_POR_ESTADO = {"exacto": "✅", "falta": "🔺", "excedido": "🔻"}


def _formatear_cantidad_real(paso: str, n: int) -> str:
    return f"{escalar_cantidad(paso, n)} ({n} equivalentes)"


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
                "bloqueado": ing.get("bloqueado", False),
                "opcional": ing.get("opcional", False),
                # opcional=True arranca incluido -> reproduce la versión más completa de la
                # receta por default; el usuario lo desmarca si no quiere ese extra.
                "incluido": True,
            }
            for ing in receta["ingredientes"]
        ],
    }


def render() -> None:
    st.title("🥗 EquiVale — Build your menu")
    st.caption(f"MVP Fase 3 — un solo tiempo ({TIEMPO_LABEL}), en memoria, sin guardar todavía.")

    personas = cargar_personas()
    persona = st.selectbox("Persona", personas)

    if st.session_state.get("_persona_actual") != persona:
        st.session_state["_persona_actual"] = persona
        st.session_state[f"seleccion_{TIEMPO}"] = []

    objetivo = cargar_objetivo(persona)
    catalogo = cargar_catalogo()

    st.subheader(f"Presupuesto diario de {persona}")
    st.markdown(
        " ".join(chip_html(g, f"{GRUPO_ETIQUETA.get(g, g)} {c}") for g, c in sorted(objetivo.items())),
        unsafe_allow_html=True,
    )

    st.divider()
    st.subheader(f"Tiempo: {TIEMPO_LABEL}")

    ver_todas = st.checkbox("Ver recetas de todas las personas", value=False)
    recetas = cargar_recetas(TIEMPO)
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
        st.markdown(
            "Vector: " + " ".join(chip_html(g, f"{GRUPO_ETIQUETA.get(g, g)} {c}") for g, c in sorted(preview.items())),
            unsafe_allow_html=True,
        )
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
                if ing.get("opcional"):
                    c0, c1, c2, c3, c4 = st.columns([1, 2, 1, 3, 1])
                    ing["incluido"] = c0.checkbox(
                        "Incluir", value=ing.get("incluido", True),
                        key=f"incluir_{instancia['instancia_id']}_{ing['alimento']}",
                        label_visibility="collapsed",
                        help="Ingrediente opcional de esta receta",
                    )
                else:
                    c1, c2, c3, c4 = st.columns([3, 1, 3, 1])

                etiqueta = ing["alimento"] + (" *(opcional)*" if ing.get("opcional") else "")
                c1.markdown(etiqueta)

                if ing.get("opcional") and not ing.get("incluido", True):
                    c3.write("(no incluido)")
                    continue

                paso = paso_equivalente(ing["alimento"], catalogo)
                ajustable = paso is not None and not ing.get("bloqueado", False)
                if not ajustable:
                    motivo = "bloqueado" if ing.get("bloqueado") else "no ajustable"
                    c3.write(f"({motivo})")
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
        ing
        for instancia in seleccion
        for ing in instancia["ingredientes"]
        if ing.get("incluido", True)
    ]
    actual = sumar_por_grupo(ingredientes_actuales, "grupo_smae", "equivalentes")
    delta = delta_objetivo(objetivo, actual)
    estado = estado_por_grupo(delta)

    for grupo in sorted(set(objetivo) | set(actual)):
        icono = ICONO_POR_ESTADO[estado[grupo]]
        st.markdown(
            chip_html(grupo, GRUPO_ETIQUETA.get(grupo, grupo))
            + f" &nbsp; {icono} objetivo {objetivo.get(grupo, 0)} · "
            f"actual {actual.get(grupo, 0)} · delta {delta[grupo]:+d}",
            unsafe_allow_html=True,
        )


render()
