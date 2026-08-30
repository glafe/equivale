"""EquiVale — "Menú del día" (antes "Build your menu"; renombrado 2026-08-29 para homologar el
idioma de la app -- Fase 4: día completo, guardado por fecha, historial).

Ver UI-BUILD-YOUR-MENU.md para la especificación de interacción completa.
"""

import uuid
from datetime import date

import streamlit as st

from nutriguia.cantidades import escalar_cantidad
from nutriguia.colores import GRUPO_ETIQUETA, chip_html, chip_muted_html
from nutriguia.streamlit_data import cargar_catalogo, cargar_objetivo, cargar_personas, cargar_recetas, db
from nutriguia.validation import delta_objetivo, estado_por_grupo, paso_equivalente, sumar_por_grupo

TIEMPOS = ["al_despertar", "desayuno", "colacion", "comida", "cena"]
TIEMPO_LABEL = {
    "al_despertar": "🌅 Al despertar",
    "desayuno": "🍳 Desayuno",
    "colacion": "🍎 Colación",
    "comida": "🍽️ Comida",
    "cena": "🌙 Cena",
}
# Versión sin emoji de TIEMPO_LABEL, para usar como sufijo de texto dentro del picker de recetas
# (ver _renderizar_tiempo) y otros lugares donde el emoji no aporta.
TIEMPO_LABEL_PLAIN = {
    "al_despertar": "Al despertar",
    "desayuno": "Desayuno",
    "colacion": "Colación",
    "comida": "Comida",
    "cena": "Cena",
}

ICONO_POR_ESTADO = {"exacto": "✅", "falta": "🔺", "excedido": "🔻"}


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
                "incluido": True,
            }
            for ing in receta["ingredientes"]
        ],
    }


def _instancia_desde_guardado(inst: dict) -> dict:
    return {
        "instancia_id": str(uuid.uuid4()),
        "receta_id": inst["receta_id"],
        "nombre": inst["nombre"],
        "ingredientes": [dict(ing) for ing in inst["ingredientes"]],
    }


def _actual_de(instancias: list[dict]) -> dict[str, int]:
    ingredientes = [
        ing for inst in instancias for ing in inst["ingredientes"] if ing.get("incluido", True)
    ]
    return sumar_por_grupo(ingredientes, "grupo_smae", "equivalentes")


def _sumar_dicts(dicts: list[dict[str, int]]) -> dict[str, int]:
    total: dict[str, int] = {}
    for d in dicts:
        for g, c in d.items():
            total[g] = total.get(g, 0) + c
    return total


def _dia_vacio(persona: str) -> dict:
    return {"persona": persona, "fecha": date.today(), "nombre": "", "tiempos": {t: [] for t in TIEMPOS}}


def _cargar_plan_guardado(doc: dict) -> dict:
    dia = {
        "persona": doc["persona"],
        "fecha": date.fromisoformat(doc["fecha"]),
        "nombre": doc.get("nombre") or "",
        "tiempos": {t: [] for t in TIEMPOS},
    }
    for t, datos in doc.get("tiempos", {}).items():
        if t in dia["tiempos"]:
            dia["tiempos"][t] = [_instancia_desde_guardado(i) for i in datos.get("seleccion", [])]
    return dia


def _nombre_en_uso_por_otra_fecha(persona: str, nombre: str, fecha_iso: str) -> str | None:
    """Un nombre debe identificar UN solo menú por persona (para poder elegirlo sin ambigüedad
    en "Menú semanal") -- si ya lo usa otra fecha, regresa esa fecha para poder avisar."""
    otro = db().menus_construidos.find_one(
        {"persona": persona, "nombre": nombre, "fecha": {"$ne": fecha_iso}}, {"fecha": 1}
    )
    return otro["fecha"] if otro else None


def _cargar_historial(persona: str) -> list[dict]:
    return list(db().menus_construidos.find({"persona": persona}, {"_id": 0}).sort("fecha", -1))


def _selectbox_seguro(label: str, opciones: list[str], key: str, **kwargs):
    """st.selectbox que no truena si el valor guardado en session_state para `key` ya no está en
    `opciones` (ej. cambiaste de persona y esa receta ya no aplica) -- lo limpia antes de
    instanciar el widget en vez de dejar que Streamlit reciba un valor fuera de rango."""
    if key in st.session_state and st.session_state[key] not in opciones:
        del st.session_state[key]
    return st.selectbox(label, options=opciones, key=key, **kwargs)


def _renderizar_tiempo(tiempo: str, dia: dict, objetivo_diario: dict, catalogo: dict) -> None:
    st.subheader(TIEMPO_LABEL[tiempo])

    actual_otros = _sumar_dicts([
        _actual_de(instancias) for t, instancias in dia["tiempos"].items() if t != tiempo
    ])
    restante = delta_objetivo(objetivo_diario, actual_otros)

    ver_todas = st.checkbox("Ver recetas de todas las personas", key=f"ver_todas_{tiempo}")
    # No se filtra estrictamente por tiempo -- se ordena con las recetas de este tiempo primero
    # (alfabético) y luego el resto del banco (también alfabético, con su primer tiempo típico
    # como referencia), porque nada impide usar un platillo típico de otro tiempo si conviene.
    todas_recetas = cargar_recetas()
    if not ver_todas:
        todas_recetas = [r for r in todas_recetas if dia["persona"] in r.get("personas_vistas", [])]
    coinciden = sorted(
        (r for r in todas_recetas if tiempo in r.get("tiempo_tipico", [])), key=lambda r: r["nombre"]
    )
    otras = sorted(
        (r for r in todas_recetas if tiempo not in r.get("tiempo_tipico", [])), key=lambda r: r["nombre"]
    )
    ids_coinciden = {r["receta_id"] for r in coinciden}
    opciones = {r["receta_id"]: r for r in coinciden + otras}

    def _etiqueta_opcion(rid: str) -> str:
        receta = opciones[rid]
        if rid in ids_coinciden:
            return receta["nombre"]
        primer_tiempo = next(iter(receta.get("tiempo_tipico", [])), None)
        etiqueta_tiempo = TIEMPO_LABEL_PLAIN.get(primer_tiempo, primer_tiempo)
        return f"{receta['nombre']}  ·  {etiqueta_tiempo}" if etiqueta_tiempo else receta["nombre"]

    col1, col2 = st.columns([3, 1])
    with col1:
        receta_id_elegida = _selectbox_seguro(
            "Selecciona una receta",
            list(opciones.keys()),
            key=f"receta_sel_{tiempo}",
            format_func=_etiqueta_opcion,
        )
    if receta_id_elegida:
        receta_elegida = opciones[receta_id_elegida]
        preview = receta_elegida["vector_equivalentes"]
        chips_vector = "Vector: " + " ".join(
            chip_html(g, f"{GRUPO_ETIQUETA.get(g, g)} {c}") for g, c in sorted(preview.items())
        )
        if receta_id_elegida in ids_coinciden:
            st.markdown(chips_vector, unsafe_allow_html=True)
        else:
            primer_tiempo = next(iter(receta_elegida.get("tiempo_tipico", [])), None)
            etiqueta_tiempo = TIEMPO_LABEL_PLAIN.get(primer_tiempo, primer_tiempo) or "sin tiempo típico"
            st.markdown(
                '<div style="display:flex; justify-content:space-between; align-items:center; '
                f'gap:.6rem; flex-wrap:wrap;"><div>{chips_vector}</div>'
                f"{chip_muted_html('Normalmente: ' + etiqueta_tiempo)}</div>",
                unsafe_allow_html=True,
            )
    with col2:
        st.write("")
        st.write("")
        if st.button("+ Agregar", key=f"agregar_{tiempo}", disabled=receta_id_elegida is None):
            dia["tiempos"][tiempo].append(_nueva_instancia(opciones[receta_id_elegida]))
            st.rerun()

    seleccion = dia["tiempos"][tiempo]
    for instancia in list(seleccion):
        with st.container(border=True, key=f"receta_card_{instancia['instancia_id']}"):
            top_l, top_r = st.columns([4, 1])
            top_l.markdown(f"**{instancia['nombre']}**")
            if top_r.button("quitar", key=f"quitar_{tiempo}_{instancia['instancia_id']}"):
                seleccion.remove(instancia)
                st.rerun()

            for i, ing in enumerate(instancia["ingredientes"]):
                if i > 0:
                    st.markdown(
                        '<hr style="margin:.5rem 0;opacity:.35;">', unsafe_allow_html=True
                    )

                # Fila 1: etiqueta (+ checkbox "Incluir" si es opcional) -- en pantallas angostas
                # cada `st.columns(...)` se apila completo, así que separar la etiqueta del
                # stepper en dos filas cortas se ve mejor en un teléfono que un solo renglón de
                # 4-5 columnas apilándose una por una.
                opcional = ing.get("opcional", False)
                if opcional:
                    c_incl, c_etq = st.columns([1, 6])
                    ing["incluido"] = c_incl.checkbox(
                        "Incluir",
                        value=ing.get("incluido", True),
                        key=f"incluir_{tiempo}_{instancia['instancia_id']}_{ing['alimento']}",
                        label_visibility="collapsed",
                        help="Ingrediente opcional de esta receta",
                    )
                    c_etq.markdown(f"{ing['alimento']} *(opcional)*")
                else:
                    st.markdown(ing["alimento"])

                if opcional and not ing.get("incluido", True):
                    st.caption("No incluido en este platillo.")
                    continue

                paso = paso_equivalente(ing["alimento"], catalogo)
                ajustable = paso is not None and not ing.get("bloqueado", False)
                if not ajustable:
                    motivo = "bloqueado" if ing.get("bloqueado") else "no ajustable"
                    st.caption(f"({motivo})")
                    continue

                # Fila 2: stepper -/cantidad/+ en 3 columnas (antes eran 4-5) -- menos bloques
                # cuando se apilan en móvil, y visualmente quedan agrupados con la etiqueta de
                # arriba en vez de mezclados con la del ingrediente siguiente.
                c_menos, c_cant, c_mas = st.columns([1, 3, 1])
                if c_menos.button(
                    "-", key=f"menos_{tiempo}_{instancia['instancia_id']}_{ing['alimento']}",
                    disabled=ing["equivalentes"] <= 1,
                ):
                    ing["equivalentes"] -= 1
                    st.rerun()
                c_cant.write(f"{escalar_cantidad(paso, ing['equivalentes'])} ({ing['equivalentes']} equivalentes)")
                if c_mas.button("+", key=f"mas_{tiempo}_{instancia['instancia_id']}_{ing['alimento']}"):
                    ing["equivalentes"] += 1
                    st.rerun()

    with st.container(border=True, key=f"status_{tiempo}"):
        st.markdown("**Estado de este tiempo** (contra lo que queda del presupuesto diario)")
        actual_tiempo = _actual_de(seleccion)
        delta_tiempo = delta_objetivo(restante, actual_tiempo)
        estado = estado_por_grupo(delta_tiempo)
        grupos = sorted(set(restante) | set(actual_tiempo))
        if not grupos:
            st.caption("Sin actividad todavía en este tiempo.")
        for grupo in grupos:
            icono = ICONO_POR_ESTADO[estado[grupo]]
            st.markdown(
                chip_html(grupo, GRUPO_ETIQUETA.get(grupo, grupo))
                + f" &nbsp; {icono} presupuesto {restante.get(grupo, 0)} · "
                f"usado aquí {actual_tiempo.get(grupo, 0)} · delta {delta_tiempo[grupo]:+d}",
                unsafe_allow_html=True,
            )


def render() -> None:
    st.title("🥗 EquiVale — Menú del día")
    st.caption("Arma tu día completo, guarda un plan por fecha, y revisa tu historial.")

    # Un botón "Abrir" del historial (más abajo, en un render anterior) puede haber pedido
    # cambiar la fecha/nombre -- aplicarlo ANTES de instanciar esos widgets en este run (después
    # ya no se puede tocar su session_state).
    if "_fecha_pendiente" in st.session_state:
        st.session_state["fecha_input"] = st.session_state.pop("_fecha_pendiente")
    if "_nombre_pendiente" in st.session_state:
        st.session_state["nombre_input"] = st.session_state.pop("_nombre_pendiente")

    personas = cargar_personas()
    persona = st.selectbox("Persona", personas)

    if st.session_state.get("_persona_actual") != persona:
        st.session_state["_persona_actual"] = persona
        st.session_state["dia"] = _dia_vacio(persona)
        st.session_state["fecha_input"] = date.today()
        st.session_state["nombre_input"] = ""

    dia = st.session_state["dia"]
    objetivo_diario = cargar_objetivo(persona)
    catalogo = cargar_catalogo()

    st.subheader(f"Presupuesto diario de {persona}")
    st.markdown(
        " ".join(chip_html(g, f"{GRUPO_ETIQUETA.get(g, g)} {c}") for g, c in sorted(objetivo_diario.items())),
        unsafe_allow_html=True,
    )

    c_fecha, c_nombre = st.columns([1, 2])
    dia["fecha"] = c_fecha.date_input("Fecha de este plan", key="fecha_input")
    dia["nombre"] = c_nombre.text_input(
        "Nombre (opcional)", key="nombre_input",
        placeholder="ej. Menú 1 -- para reutilizarlo en Menú semanal",
        help="Dale un nombre si quieres poder asignar este día a días de la semana en "
             "\"Menú semanal\" más adelante. Sin nombre, este plan solo queda guardado para "
             "esta fecha.",
    )

    st.divider()

    tabs = st.tabs([TIEMPO_LABEL[t] for t in TIEMPOS])
    for tab, tiempo in zip(tabs, TIEMPOS):
        with tab:
            _renderizar_tiempo(tiempo, dia, objetivo_diario, catalogo)

    st.divider()
    st.subheader("Resumen del día")
    actual_diario = _sumar_dicts([_actual_de(instancias) for instancias in dia["tiempos"].values()])
    delta_diario = delta_objetivo(objetivo_diario, actual_diario)
    estado_diario = estado_por_grupo(delta_diario)
    with st.container(border=True, key="status_dia"):
        for grupo in sorted(set(objetivo_diario) | set(actual_diario)):
            icono = ICONO_POR_ESTADO[estado_diario[grupo]]
            st.markdown(
                chip_html(grupo, GRUPO_ETIQUETA.get(grupo, grupo))
                + f" &nbsp; {icono} objetivo {objetivo_diario.get(grupo, 0)} · "
                f"actual {actual_diario.get(grupo, 0)} · delta {delta_diario[grupo]:+d}",
                unsafe_allow_html=True,
            )

    dia_completo = bool(delta_diario) and all(v == 0 for v in delta_diario.values())
    if not dia_completo and any(v != 0 for v in delta_diario.values()):
        faltantes = ", ".join(
            f"{GRUPO_ETIQUETA.get(g, g)} {v:+d}" for g, v in sorted(delta_diario.items()) if v != 0
        )
        st.warning(f"Todavía sin cuadrar: {faltantes}. Se puede guardar en progreso de todas formas.")

    if st.button("💾 Guardar menú del día", type="primary"):
        fecha_iso = dia["fecha"].isoformat()
        nombre_final = dia["nombre"].strip()
        fecha_en_conflicto = (
            _nombre_en_uso_por_otra_fecha(persona, nombre_final, fecha_iso) if nombre_final else None
        )
        if fecha_en_conflicto:
            st.error(
                f"Ya hay un plan de {persona} llamado '{nombre_final}' guardado para "
                f"{fecha_en_conflicto} -- cambia el nombre o abre ese plan desde el historial "
                "para editarlo en vez de crear otro con el mismo nombre."
            )
            st.stop()
        documento = {
            "persona": persona,
            "fecha": fecha_iso,
            "nombre": nombre_final or None,
            "estado": "completo" if dia_completo else "en_progreso",
            "objetivo_diario": objetivo_diario,
            "actual_diario": actual_diario,
            "delta_diario": delta_diario,
            "tiempos": {
                t: {
                    "seleccion": [
                        {
                            "receta_id": inst["receta_id"],
                            "nombre": inst["nombre"],
                            "ingredientes": inst["ingredientes"],
                        }
                        for inst in instancias
                    ],
                    "actual": _actual_de(instancias),
                }
                for t, instancias in dia["tiempos"].items()
                if instancias
            },
        }
        db().menus_construidos.create_index([("persona", 1), ("fecha", 1)], unique=True)
        db().menus_construidos.replace_one({"persona": persona, "fecha": fecha_iso}, documento, upsert=True)
        mensaje = f"Guardado: plan de {persona} para {fecha_iso} ({documento['estado']})."
        if nombre_final:
            mensaje += f" Guardado también como '{nombre_final}' -- ya se puede asignar en \"Menú semanal\"."
        st.success(mensaje)

    st.divider()
    with st.expander("📜 Historial de planes guardados"):
        historial = _cargar_historial(persona)
        if not historial:
            st.caption("Todavía no hay planes guardados para esta persona.")
        for doc in historial:
            c1, c2, c3 = st.columns([2, 2, 1])
            etiqueta_fecha = doc["fecha"] + (f" · **{doc['nombre']}**" if doc.get("nombre") else "")
            c1.markdown(etiqueta_fecha)
            c2.write("✅ completo" if doc["estado"] == "completo" else "🔺 en progreso")
            if c3.button("Abrir", key=f"abrir_{doc['fecha']}"):
                plan = _cargar_plan_guardado(doc)
                st.session_state["dia"] = plan
                st.session_state["_fecha_pendiente"] = date.fromisoformat(doc["fecha"])
                st.session_state["_nombre_pendiente"] = plan["nombre"]
                st.rerun()


render()
