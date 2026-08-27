"""EquiVale — página Personas (Fase 3.6): crear una persona nueva o editar el objetivo diario de
una existente.

Ver UI-BUILD-YOUR-MENU.md -> "Página Personas" para la especificación completa.
"""

from datetime import date

import streamlit as st

from nutriguia.colores import GRUPO_ETIQUETA, chip_html
from nutriguia.streamlit_data import cargar_objetivo, cargar_personas, db, invalidar_cache_personas

GRUPOS_CANONICOS = ["AOA", "Cereal", "Verdura", "Fruta", "Aceite s/p", "Aceite c/p", "Leguminosa"]
NUEVA_PERSONA = "— Nueva persona —"


def _draft_desde_persona(persona: str | None) -> dict:
    objetivo_actual = cargar_objetivo(persona) if persona else {}
    return {
        "nombre": persona or "",
        "objetivo": {g: objetivo_actual.get(g, 0) for g in GRUPOS_CANONICOS},
    }


def render() -> None:
    st.title("🧑‍🤝‍🧑 Personas")
    st.caption("Crea una persona nueva o edita el objetivo diario de una existente.")

    if "_flash_personas" in st.session_state:
        st.success(st.session_state.pop("_flash_personas"))
    if "_seleccionar_persona_tras_guardar" in st.session_state:
        st.session_state["personas_selector"] = st.session_state.pop("_seleccionar_persona_tras_guardar")

    personas_existentes = cargar_personas()
    opciones = [NUEVA_PERSONA] + personas_existentes
    elegido = st.selectbox("Persona", options=opciones, key="personas_selector")

    if st.session_state.get("_personas_actual") != elegido:
        st.session_state["_personas_actual"] = elegido
        persona_previa = None if elegido == NUEVA_PERSONA else elegido
        st.session_state["personas_draft"] = _draft_desde_persona(persona_previa)

    draft = st.session_state["personas_draft"]

    if elegido == NUEVA_PERSONA:
        draft["nombre"] = st.text_input("Nombre de la persona", value=draft["nombre"])
    else:
        st.text_input("Nombre de la persona", value=draft["nombre"], disabled=True)

    st.subheader("Objetivo diario")
    st.caption("0 = ese grupo no aplica para esta persona (no se guarda).")
    cols = st.columns(4)
    for i, grupo in enumerate(GRUPOS_CANONICOS):
        with cols[i % 4]:
            # key incluye `elegido` a propósito: al cambiar de persona esto es un widget "nuevo"
            # para Streamlit, así que muestra el objetivo recién cargado en vez de arrastrar el
            # valor que hubiera quedado de la persona anterior en este mismo campo.
            draft["objetivo"][grupo] = st.number_input(
                GRUPO_ETIQUETA.get(grupo, grupo),
                min_value=0,
                step=1,
                value=draft["objetivo"][grupo],
                key=f"objetivo_{elegido}_{grupo}",
            )

    resumen = {g: c for g, c in draft["objetivo"].items() if c > 0}
    st.subheader("Resumen")
    if resumen:
        st.markdown(
            " ".join(chip_html(g, f"{GRUPO_ETIQUETA.get(g, g)} {c}") for g, c in sorted(resumen.items())),
            unsafe_allow_html=True,
        )
    else:
        st.caption("Sin equivalentes todavía.")

    nombre = draft["nombre"].strip()
    es_nueva = elegido == NUEVA_PERSONA
    nombre_disponible = not es_nueva or nombre not in personas_existentes
    if es_nueva and nombre and not nombre_disponible:
        st.warning(f"Ya existe una persona llamada '{nombre}'.")
    puede_guardar = bool(nombre) and bool(resumen) and nombre_disponible

    if st.button("💾 Guardar", disabled=not puede_guardar, type="primary"):
        equivalentes_diarios = [{"grupo": g, "cantidad": c} for g, c in resumen.items()]
        db().personas.update_one(
            {"persona": nombre}, {"$setOnInsert": {"persona": nombre}}, upsert=True
        )
        # Un solo objetivo vigente por persona en esta fase (no se lleva historial de versiones
        # anteriores -- ver "Ideas para más adelante" en BUILD-PLAN.md).
        db().objetivos.delete_many({"persona": nombre})
        db().objetivos.insert_one(
            {
                "persona": nombre,
                "vigente_desde": date.today().isoformat(),
                "equivalentes_diarios": equivalentes_diarios,
            }
        )
        invalidar_cache_personas()
        if es_nueva:
            # Necesita rerun para que el selectbox deje de mostrar "Nueva persona" y apunte a la
            # persona recién creada -> el mensaje debe sobrevivir ese rerun (mismo patrón que el
            # Editor de recetas).
            st.session_state["_seleccionar_persona_tras_guardar"] = nombre
            st.session_state["_personas_actual"] = nombre
            st.session_state["_flash_personas"] = f"Persona '{nombre}' creada."
            st.rerun()
        # Editando una persona existente: no hace falta rerun, se puede mostrar directo.
        st.success(f"Objetivo de '{nombre}' actualizado.")


render()
