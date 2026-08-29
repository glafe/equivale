"""EquiVale — "Menú semanal" (2026-08-29, a pedido del usuario): menús reutilizables ("Menú 1",
"Menú 2", ...) más simples que "Menú del día" -- solo eligen recetas por tiempo, sin ajustar
ingredientes uno por uno -- y su asignación a los días de la semana, para ver de un vistazo si un
ciclo de menús cubre la semana completa (ej. Menú 1 -> lunes/miércoles/viernes, Menú 2 ->
martes/jueves/sábado, domingo libre).

Ver UI-BUILD-YOUR-MENU.md -> "Menú semanal" para la especificación completa.
"""

import streamlit as st

from nutriguia.colores import GRUPO_ETIQUETA, chip_html
from nutriguia.streamlit_data import cargar_personas, cargar_recetas, db

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
DIA_LABEL = {
    "lunes": "Lunes", "martes": "Martes", "miercoles": "Miércoles", "jueves": "Jueves",
    "viernes": "Viernes", "sabado": "Sábado", "domingo": "Domingo",
}
TIEMPOS = ["al_despertar", "desayuno", "colacion", "comida", "cena"]
TIEMPO_LABEL = {
    "al_despertar": "🌅 Al despertar", "desayuno": "🍳 Desayuno", "colacion": "🍎 Colación",
    "comida": "🍽️ Comida", "cena": "🌙 Cena",
}
LIBRE = "— Libre / descanso —"
NUEVO_MENU = "— Nuevo menú —"


def _selectbox_seguro(label: str, opciones: list[str], key: str, **kwargs):
    """st.selectbox que no truena si el valor guardado en session_state para `key` ya no está en
    `opciones` (ej. cambiaste "Ver recetas de todas las personas", o renombraste/eliminaste un
    menú mientras el selector seguía apuntando al valor viejo) -- lo limpia antes de instanciar el
    widget. Mismo patrón que views/menu_del_dia.py."""
    if key in st.session_state and st.session_state[key] not in opciones:
        del st.session_state[key]
    return st.selectbox(label, options=opciones, key=key, **kwargs)


def _sumar_dicts(dicts: list[dict[str, int]]) -> dict[str, int]:
    total: dict[str, int] = {}
    for d in dicts:
        for g, c in d.items():
            total[g] = total.get(g, 0) + c
    return total


def _chips(vector: dict[str, int]) -> str:
    return " ".join(chip_html(g, f"{GRUPO_ETIQUETA.get(g, g)} {c}") for g, c in sorted(vector.items()))


def _cargar_plantillas(persona: str) -> list[dict]:
    return list(db().plantillas_semana.find({"persona": persona}, {"_id": 0}))


def _cargar_asignacion(persona: str) -> dict[str, str | None]:
    doc = db().asignacion_semanal.find_one({"persona": persona}, {"_id": 0})
    dias_guardados = doc.get("dias", {}) if doc else {}
    return {d: dias_guardados.get(d) for d in DIAS}


def _vector_de_plantilla(plantilla: dict) -> dict[str, int]:
    vectores = [r["vector_equivalentes"] for recetas in plantilla["tiempos"].values() for r in recetas]
    return _sumar_dicts(vectores)


def _draft_vacio() -> dict:
    return {"nombre": "", "tiempos": {t: [] for t in TIEMPOS}}


def _draft_desde_plantilla(plantilla: dict) -> dict:
    return {
        "nombre": plantilla["nombre"],
        "tiempos": {t: list(plantilla["tiempos"].get(t, [])) for t in TIEMPOS},
    }


def _renombrar_en_asignacion(persona: str, nombre_viejo: str, nombre_nuevo: str) -> None:
    """La asignación semanal referencia una plantilla por `nombre` (no por id) -- si se renombra
    la plantilla y no se actualiza acá, el día se quedaría apuntando a un nombre inexistente."""
    doc = db().asignacion_semanal.find_one({"persona": persona})
    if not doc:
        return
    cambios = {f"dias.{d}": nombre_nuevo for d, v in doc.get("dias", {}).items() if v == nombre_viejo}
    if cambios:
        db().asignacion_semanal.update_one({"persona": persona}, {"$set": cambios})


def _quitar_de_asignacion(persona: str, nombre: str) -> None:
    doc = db().asignacion_semanal.find_one({"persona": persona})
    if not doc:
        return
    cambios = {f"dias.{d}": None for d, v in doc.get("dias", {}).items() if v == nombre}
    if cambios:
        db().asignacion_semanal.update_one({"persona": persona}, {"$set": cambios})


def render() -> None:
    st.title("🗓️ EquiVale — Menú semanal")
    st.caption(
        "Arma menús reutilizables (ej. \"Menú 1\", \"Menú 2\") y asígnalos a los días de la "
        "semana, para ver de un vistazo si tu ciclo de menús cubre toda la semana. A diferencia "
        "de \"Menú del día\", aquí solo eliges recetas por tiempo -- sin ajustar ingredientes uno "
        "por uno; ese ajuste fino sigue siendo trabajo de \"Menú del día\" el día que corresponda."
    )

    if "_flash_semanal" in st.session_state:
        st.success(st.session_state.pop("_flash_semanal"))
    # Mismo patrón que el editor de recetas/ingredientes: aplicar un cambio de selección
    # pendiente ANTES de instanciar el selectbox, nunca después (Streamlit no lo permite).
    if "_pendiente_menu_semanal_selector" in st.session_state:
        st.session_state["menu_semanal_selector"] = st.session_state.pop("_pendiente_menu_semanal_selector")

    personas = cargar_personas()
    persona = st.selectbox("Persona", personas, key="semanal_persona")

    plantillas = _cargar_plantillas(persona)
    plantillas_por_nombre = {p["nombre"]: p for p in plantillas}

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
            if asignado and asignado in plantillas_por_nombre:
                st.caption(asignado)
            elif asignado:
                st.caption(f"⚠️ '{asignado}' ya no existe")
            else:
                st.caption("Libre")

    if plantillas:
        with st.expander("Ver equivalentes totales por menú"):
            for p in plantillas:
                vector = _vector_de_plantilla(p)
                st.markdown(f"**{p['nombre']}** — " + (_chips(vector) if vector else "_sin recetas_"), unsafe_allow_html=True)

    with st.expander("✏️ Editar asignación de días"):
        opciones_dia = [LIBRE] + list(plantillas_por_nombre.keys())
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

    # --- Editor de menús reutilizables ---
    st.subheader("Tus menús")
    opciones_menu = [NUEVO_MENU] + list(plantillas_por_nombre.keys())
    # _selectbox_seguro, no st.selectbox: cambiar de persona (u otra sesión renombrando/eliminando
    # un menú) puede dejar este selector apuntando a un nombre que ya no existe para la persona
    # actual -- sin esto, Streamlit truena en vez de solo resetear a "Nuevo menú".
    elegido = _selectbox_seguro("Menú a editar", opciones_menu, key="menu_semanal_selector")

    if st.session_state.get("_semanal_actual") != (persona, elegido):
        st.session_state["_semanal_actual"] = (persona, elegido)
        plantilla = None if elegido == NUEVO_MENU else plantillas_por_nombre.get(elegido)
        st.session_state["semanal_draft"] = (
            _draft_vacio() if plantilla is None else _draft_desde_plantilla(plantilla)
        )

    draft = st.session_state["semanal_draft"]
    draft["nombre"] = st.text_input("Nombre del menú", value=draft["nombre"], key=f"nombre_menu_{elegido}")

    ver_todas = st.checkbox("Ver recetas de todas las personas", key=f"ver_todas_semanal_{elegido}")

    tabs = st.tabs([TIEMPO_LABEL[t] for t in TIEMPOS])
    for tab, tiempo in zip(tabs, TIEMPOS):
        with tab:
            recetas_tiempo = cargar_recetas(tiempo)
            if not ver_todas:
                recetas_tiempo = [r for r in recetas_tiempo if persona in r.get("personas_vistas", [])]
            opciones = {r["receta_id"]: r for r in recetas_tiempo}

            c1, c2 = st.columns([3, 1])
            with c1:
                receta_id_sel = _selectbox_seguro(
                    "Agregar receta",
                    list(opciones.keys()),
                    format_func=lambda rid: opciones[rid]["nombre"],
                    key=f"receta_sel_semanal_{tiempo}_{elegido}",
                )
            if c2.button(
                "+ Agregar", key=f"agregar_semanal_{tiempo}_{elegido}",
                disabled=receta_id_sel is None,
            ):
                r = opciones[receta_id_sel]
                draft["tiempos"][tiempo].append({
                    "receta_id": r["receta_id"],
                    "nombre": r["nombre"],
                    "vector_equivalentes": r["vector_equivalentes"],
                })
                st.rerun()

            for i, r in enumerate(list(draft["tiempos"][tiempo])):
                c_nombre, c_quitar = st.columns([4, 1])
                c_nombre.markdown(f"**{r['nombre']}** — {_chips(r['vector_equivalentes'])}", unsafe_allow_html=True)
                if c_quitar.button("quitar", key=f"quitar_semanal_{tiempo}_{elegido}_{i}"):
                    draft["tiempos"][tiempo].pop(i)
                    st.rerun()

            vector_tiempo = _sumar_dicts([r["vector_equivalentes"] for r in draft["tiempos"][tiempo]])
            if vector_tiempo:
                st.markdown("Total de este tiempo: " + _chips(vector_tiempo), unsafe_allow_html=True)

    vector_total = _sumar_dicts([
        r["vector_equivalentes"] for recetas in draft["tiempos"].values() for r in recetas
    ])
    st.markdown("**Total del menú**")
    if vector_total:
        st.markdown(_chips(vector_total), unsafe_allow_html=True)
    else:
        st.caption("Sin recetas todavía.")

    st.divider()
    hay_contenido = any(draft["tiempos"][t] for t in TIEMPOS)
    puede_guardar = bool(draft["nombre"].strip()) and hay_contenido
    c_guardar, c_eliminar = st.columns(2)

    if c_guardar.button("💾 Guardar menú", type="primary", disabled=not puede_guardar, key=f"guardar_menu_{elegido}"):
        nombre_final = draft["nombre"].strip()
        colision = nombre_final in plantillas_por_nombre and nombre_final != elegido
        if colision:
            st.error(f"Ya existe un menú llamado '{nombre_final}' para {persona} -- elige otro nombre.")
        else:
            db().plantillas_semana.create_index([("persona", 1), ("nombre", 1)], unique=True)
            if elegido != NUEVO_MENU and elegido != nombre_final:
                db().plantillas_semana.delete_one({"persona": persona, "nombre": elegido})
                _renombrar_en_asignacion(persona, elegido, nombre_final)
            documento = {"persona": persona, "nombre": nombre_final, "tiempos": draft["tiempos"]}
            db().plantillas_semana.replace_one(
                {"persona": persona, "nombre": nombre_final}, documento, upsert=True
            )
            st.session_state["_semanal_actual"] = (persona, nombre_final)
            st.session_state["_pendiente_menu_semanal_selector"] = nombre_final
            st.session_state["_flash_semanal"] = f"Menú '{nombre_final}' guardado."
            st.rerun()

    if elegido != NUEVO_MENU:
        confirmar = c_eliminar.checkbox("Confirmo eliminar", key=f"confirmar_menu_{elegido}")
        if c_eliminar.button("🗑️ Eliminar menú", disabled=not confirmar, key=f"eliminar_menu_{elegido}"):
            db().plantillas_semana.delete_one({"persona": persona, "nombre": elegido})
            _quitar_de_asignacion(persona, elegido)
            st.session_state["_semanal_actual"] = (persona, NUEVO_MENU)
            st.session_state["_pendiente_menu_semanal_selector"] = NUEVO_MENU
            st.session_state["_flash_semanal"] = f"Menú '{elegido}' eliminado."
            st.rerun()


render()
