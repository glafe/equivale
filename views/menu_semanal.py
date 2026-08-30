"""EquiVale — "Menú semanal" (2026-08-29, a pedido del usuario; corregido el mismo día tras
aclaración del usuario): asigna días ya guardados y con nombre desde "Menú del día" a los 7 días
de la semana, para ver de un vistazo si un ciclo de menús cubre la semana completa (ej. "Menú 1"
-> lunes/miércoles/viernes, "Menú 2" -> martes/jueves/sábado, domingo libre).

**Esta página NO arma menús** -- eso sigue siendo trabajo exclusivo de "Menú del día" (con sus
steppers, ingredientes opcionales, etc.). El flujo real es: 1) armar un día en "Menú del día" y
guardarlo con un nombre (ej. "Menú 1") además de su fecha; 2) venir aquí y asignar ese nombre a
los días de la semana que le toquen. La primera versión de esta página (mismo día, antes de esta
corrección) tenía su propio picker de recetas simplificado -- se quitó porque duplicaba, con
menos funciones, lo que "Menú del día" ya hace bien.

Ver UI-BUILD-YOUR-MENU.md -> "Menú semanal" para la especificación completa.
"""

import streamlit as st

from nutriguia.colores import GRUPO_ETIQUETA, chip_html
from nutriguia.pdf_semanal import generar_pdf_semanal
from nutriguia.streamlit_data import cargar_objetivo, cargar_personas, db

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
DIA_LABEL = {
    "lunes": "Lunes", "martes": "Martes", "miercoles": "Miércoles", "jueves": "Jueves",
    "viernes": "Viernes", "sabado": "Sábado", "domingo": "Domingo",
}
LIBRE = "— Libre / descanso —"


def _selectbox_seguro(label: str, opciones: list[str], key: str, **kwargs):
    """st.selectbox que no truena si el valor guardado en session_state para `key` ya no está en
    `opciones` (ej. el menú nombrado que tenía asignado ese día ya no existe) -- lo limpia antes
    de instanciar el widget. Mismo patrón que views/menu_del_dia.py."""
    if key in st.session_state and st.session_state[key] not in opciones:
        del st.session_state[key]
    return st.selectbox(label, options=opciones, key=key, **kwargs)


def _chips(vector: dict) -> str:
    if not vector:
        return "_(sin equivalentes)_"
    return " ".join(chip_html(g, f"{GRUPO_ETIQUETA.get(g, g)} {c}") for g, c in sorted(vector.items()))


def _cargar_menus_nombrados(persona: str) -> list[dict]:
    """Los "menús" que se pueden asignar a un día de la semana son simplemente días de "Menú del
    día" que se guardaron con un nombre -- no hay una colección aparte."""
    return list(
        db().menus_construidos.find(
            {"persona": persona, "nombre": {"$ne": None}}, {"_id": 0}
        ).sort("nombre", 1)
    )


def _cargar_asignacion(persona: str) -> dict[str, str | None]:
    doc = db().asignacion_semanal.find_one({"persona": persona}, {"_id": 0})
    dias_guardados = doc.get("dias", {}) if doc else {}
    return {d: dias_guardados.get(d) for d in DIAS}


def render() -> None:
    st.title("🗓️ EquiVale — Menú semanal")
    st.caption(
        "Asigna días ya guardados y con nombre (desde \"Menú del día\") a los días de la semana, "
        "para ver de un vistazo si tu ciclo de menús cubre toda la semana."
    )

    if "_flash_semanal" in st.session_state:
        st.success(st.session_state.pop("_flash_semanal"))

    personas = cargar_personas()
    persona = st.selectbox("Persona", personas, key="semanal_persona")

    menus = _cargar_menus_nombrados(persona)
    menus_por_nombre = {m["nombre"]: m for m in menus}

    # --- Cobertura semanal: la pregunta que motivó esta página ---
    st.subheader("Cobertura de la semana")
    asignacion = _cargar_asignacion(persona)
    dias_libres = sum(1 for d in DIAS if not asignacion.get(d))
    st.caption(f"{7 - dias_libres} día(s) con menú asignado · {dias_libres} día(s) libre(s)/descanso.")
    cols = st.columns(7)
    for col, dia in zip(cols, DIAS):
        with col:
            st.markdown(f"**{DIA_LABEL[dia][:3]}**")
            asignado = asignacion.get(dia)
            if asignado and asignado in menus_por_nombre:
                st.caption(asignado)
            elif asignado:
                st.caption(f"⚠️ '{asignado}' ya no existe")
            else:
                st.caption("Libre")

    st.download_button(
        "📄 Descargar PDF para imprimir",
        data=generar_pdf_semanal(persona, cargar_objetivo(persona), asignacion, menus_por_nombre),
        file_name=f"menu-semanal-{persona}.pdf",
        mime="application/pdf",
        help=(
            "Letra grande y colores por grupo, pensado para pegar en la cocina -- solo nombres "
            "de receta, sin ingredientes ni porciones (eso se sigue viendo en \"Menú del día\")."
        ),
    )

    with st.expander("✏️ Editar asignación de días"):
        opciones_dia = [LIBRE] + list(menus_por_nombre.keys())
        nueva_asignacion = {}
        for dia in DIAS:
            valor_actual = asignacion.get(dia) or LIBRE
            if valor_actual not in opciones_dia:
                valor_actual = LIBRE
            sel = _selectbox_seguro(
                DIA_LABEL[dia], opciones_dia,
                index=opciones_dia.index(valor_actual),
                key=f"asignar_{persona}_{dia}",
            )
            nueva_asignacion[dia] = None if sel == LIBRE else sel
        if st.button("💾 Guardar asignación", type="primary", key="guardar_asignacion"):
            db().asignacion_semanal.create_index([("persona", 1)], unique=True)
            db().asignacion_semanal.update_one(
                {"persona": persona}, {"$set": {"dias": nueva_asignacion}}, upsert=True
            )
            st.session_state["_flash_semanal"] = "Asignación semanal guardada."
            st.rerun()

    st.divider()

    # --- Tus menús: solo lectura -- armar/editar sigue siendo trabajo de "Menú del día" ---
    st.subheader("Tus menús")
    st.caption(
        "Los menús que puedes asignar arriba son días de \"Menú del día\" guardados con un "
        "nombre. Para crear uno nuevo o cambiar sus recetas, ve a \"Menú del día\"."
    )
    st.page_link("views/menu_del_dia.py", label="Ir a Menú del día", icon="🥗")

    if not menus:
        st.info(f"{persona} todavía no tiene ningún día guardado con nombre.")
    else:
        for m in menus:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{m['nombre']}**")
                c2.caption(m["fecha"])
                st.markdown(_chips(m.get("actual_diario", {})), unsafe_allow_html=True)


render()
