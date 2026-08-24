"""EquiVale Chef — editor de recetas (Fase 3.5).

Ver UI-BUILD-YOUR-MENU.md -> "Editor de recetas" para la especificación completa.
"""

import re
import uuid

import streamlit as st

from nutriguia.colores import GRUPO_ETIQUETA, chip_html
from nutriguia.streamlit_data import (
    cargar_nombres_alimentos,
    cargar_personas,
    cargar_recetas,
    db,
    invalidar_cache_recetas,
)
from nutriguia.validation import sumar_por_grupo

GRUPOS_CANONICOS = ["AOA", "Cereal", "Verdura", "Fruta", "Aceite s/p", "Aceite c/p", "Leguminosa"]
TIEMPOS_CANONICOS = ["al_despertar", "desayuno", "colacion", "comida", "cena"]
OTRO_ALIMENTO = "(otro / alimento nuevo)"
LIBRE = "(libre, sin grupo)"

NUEVA_RECETA = "— Nueva receta —"


def _slug(nombre: str) -> str:
    texto = nombre.strip().lower()
    reemplazos = str.maketrans("áéíóúñ", "aeioun")
    texto = texto.translate(reemplazos)
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    return texto or "receta"


def _receta_id_disponible(slug_base: str, receta_id_actual: str | None, ids_existentes: set[str]) -> str:
    if slug_base == receta_id_actual:
        return slug_base
    if slug_base not in ids_existentes:
        return slug_base
    n = 2
    while f"{slug_base}-v{n}" in ids_existentes and f"{slug_base}-v{n}" != receta_id_actual:
        n += 1
    return f"{slug_base}-v{n}"


def _fila_vacia() -> dict:
    return {
        "fila_id": str(uuid.uuid4()),
        "alimento": "",
        "grupo_smae": None,
        "cantidad": "",
        "equivalentes": 1,
        "bloqueado": False,
    }


def _draft_desde_receta(receta: dict | None) -> dict:
    if receta is None:
        return {
            "receta_id": None,
            "nombre": "",
            "tiempo_tipico": [],
            "personas_vistas": [],
            "ingredientes": [_fila_vacia()],
            "veces_visto": 0,
            "origen": [],
        }
    ingredientes = [
        {
            "fila_id": str(uuid.uuid4()),
            "alimento": ing["alimento"],
            "grupo_smae": ing.get("grupo_smae"),
            "cantidad": ing.get("cantidad", ""),
            "equivalentes": ing["equivalentes"],
            "bloqueado": ing.get("bloqueado", False),
        }
        for ing in receta["ingredientes"]
    ]
    return {
        "receta_id": receta["receta_id"],
        "nombre": receta["nombre"],
        "tiempo_tipico": receta.get("tiempo_tipico", []),
        "personas_vistas": receta.get("personas_vistas", []),
        "ingredientes": ingredientes or [_fila_vacia()],
        "veces_visto": receta.get("veces_visto", 0),
        "origen": receta.get("origen", []),
    }


def render() -> None:
    st.title("🧑‍🍳 EquiVale Chef — Editor de recetas")
    st.caption("Crea, corrige o elimina recetas del banco. Los cambios se guardan directo a Mongo.")

    recetas = cargar_recetas()
    personas = cargar_personas()
    alimentos_catalogo = cargar_nombres_alimentos()
    catalogo_por_nombre = {d["alimento"]: d for d in db().catalogo_alimentos.find({}, {"_id": 0})}

    recetas_por_id = {r["receta_id"]: r for r in recetas}
    if "_flash" in st.session_state:
        st.success(st.session_state.pop("_flash"))
    # No se puede asignar a session_state["editor_receta_selector"] después de que el
    # selectbox ya se instanció en este mismo run -> se aplica acá, antes de crearlo.
    if "_seleccionar_tras_guardar" in st.session_state:
        st.session_state["editor_receta_selector"] = st.session_state.pop("_seleccionar_tras_guardar")

    opciones = [NUEVA_RECETA] + sorted(recetas_por_id, key=lambda rid: recetas_por_id[rid]["nombre"])
    elegido = st.selectbox(
        "Receta a editar",
        options=opciones,
        format_func=lambda rid: rid if rid == NUEVA_RECETA else recetas_por_id[rid]["nombre"],
        key="editor_receta_selector",
    )

    if st.session_state.get("_editor_actual") != elegido:
        st.session_state["_editor_actual"] = elegido
        receta = None if elegido == NUEVA_RECETA else recetas_por_id[elegido]
        st.session_state["editor_draft"] = _draft_desde_receta(receta)

    draft = st.session_state["editor_draft"]

    draft["nombre"] = st.text_input("Nombre del platillo", value=draft["nombre"])
    draft["tiempo_tipico"] = st.multiselect(
        "Tiempo(s) típico(s)", options=TIEMPOS_CANONICOS, default=draft["tiempo_tipico"]
    )
    draft["personas_vistas"] = st.multiselect(
        "Persona(s)", options=personas, default=[p for p in draft["personas_vistas"] if p in personas]
    )

    st.subheader("Ingredientes")
    opciones_alimento = [OTRO_ALIMENTO] + alimentos_catalogo
    opciones_grupo = [LIBRE] + GRUPOS_CANONICOS

    for fila in list(draft["ingredientes"]):
        with st.container(border=True):
            c1, c2, c_cant, c3, c4, c5 = st.columns([3, 2, 2, 1, 1, 1])

            en_catalogo = fila["alimento"] in alimentos_catalogo
            sel = c1.selectbox(
                "Alimento",
                options=opciones_alimento,
                index=opciones_alimento.index(fila["alimento"]) if en_catalogo else 0,
                key=f"alimento_sel_{fila['fila_id']}",
                label_visibility="collapsed",
            )
            if sel == OTRO_ALIMENTO:
                fila["alimento"] = c1.text_input(
                    "Nombre del alimento",
                    value="" if en_catalogo else fila["alimento"],
                    key=f"alimento_txt_{fila['fila_id']}",
                    label_visibility="collapsed",
                    placeholder="Nombre del alimento nuevo",
                )
            else:
                fila["alimento"] = sel
                if sel in catalogo_por_nombre:
                    fila["grupo_smae"] = catalogo_por_nombre[sel]["grupo"]

            grupo_actual = fila["grupo_smae"] if fila["grupo_smae"] in GRUPOS_CANONICOS else LIBRE
            grupo_sel = c2.selectbox(
                "Grupo",
                options=opciones_grupo,
                index=opciones_grupo.index(grupo_actual),
                key=f"grupo_{fila['fila_id']}",
                label_visibility="collapsed",
            )
            fila["grupo_smae"] = None if grupo_sel == LIBRE else grupo_sel

            fila["cantidad"] = c_cant.text_input(
                "Cantidad",
                value=fila["cantidad"],
                key=f"cantidad_{fila['fila_id']}",
                label_visibility="collapsed",
                placeholder="ej. 1/2 taza, 150 g",
            )

            fila["equivalentes"] = c3.number_input(
                "Equiv.", min_value=1, step=1, value=fila["equivalentes"],
                key=f"equiv_{fila['fila_id']}", label_visibility="collapsed",
            )
            fila["bloqueado"] = c4.checkbox(
                "🔒", value=fila["bloqueado"], key=f"bloqueado_{fila['fila_id']}",
                help="Bloquear: no ajustable con +/- en Build your menu",
            )
            if c5.button("quitar", key=f"quitar_ing_{fila['fila_id']}"):
                draft["ingredientes"].remove(fila)
                st.rerun()

    if st.button("+ Agregar ingrediente"):
        draft["ingredientes"].append(_fila_vacia())
        st.rerun()

    st.divider()
    st.subheader("Resumen de equivalentes")
    vector = sumar_por_grupo(draft["ingredientes"], "grupo_smae", "equivalentes")
    if vector:
        st.markdown(
            " ".join(chip_html(g, f"{GRUPO_ETIQUETA.get(g, g)} {c}") for g, c in sorted(vector.items())),
            unsafe_allow_html=True,
        )
    else:
        st.caption("Sin ingredientes con grupo todavía.")

    st.divider()
    col_guardar, col_eliminar = st.columns(2)

    with col_guardar:
        ingredientes_validos = [i for i in draft["ingredientes"] if i["alimento"].strip()]
        puede_guardar = bool(draft["nombre"].strip()) and bool(ingredientes_validos)
        if st.button("💾 Guardar receta", disabled=not puede_guardar, type="primary"):
            ids_existentes = set(recetas_por_id) - ({draft["receta_id"]} if draft["receta_id"] else set())
            slug_base = _slug(draft["nombre"])
            receta_id = draft["receta_id"] or _receta_id_disponible(slug_base, None, ids_existentes)
            documento = {
                "receta_id": receta_id,
                "nombre": draft["nombre"].strip(),
                "tiempo_tipico": draft["tiempo_tipico"],
                "personas_vistas": draft["personas_vistas"],
                "vector_equivalentes": sumar_por_grupo(ingredientes_validos, "grupo_smae", "equivalentes"),
                "ingredientes": [
                    {
                        "cantidad": i["cantidad"].strip(),
                        "alimento": i["alimento"].strip(),
                        "grupo_smae": i["grupo_smae"],
                        "equivalentes": i["equivalentes"],
                        **({"bloqueado": True} if i["bloqueado"] else {}),
                    }
                    for i in ingredientes_validos
                ],
                "veces_visto": draft["veces_visto"],
                "origen": draft["origen"],
            }
            db().recetas.replace_one({"receta_id": receta_id}, documento, upsert=True)
            invalidar_cache_recetas()
            draft["receta_id"] = receta_id
            if elegido == NUEVA_RECETA:
                # Necesita rerun para que el selectbox deje de mostrar "Nueva receta" y
                # apunte a la receta recién creada -> el mensaje debe sobrevivir ese rerun.
                # draft["receta_id"] ya quedó actualizado arriba, antes del rerun, para que el
                # mismo objeto en session_state["editor_draft"] llegue correcto al siguiente run.
                st.session_state["_flash"] = f"Receta '{documento['nombre']}' guardada como `{receta_id}`."
                st.session_state["_seleccionar_tras_guardar"] = receta_id
                st.session_state["_editor_actual"] = receta_id
                st.rerun()
            # Editando una receta existente: no hace falta rerun, se puede mostrar directo.
            st.success(f"Receta '{documento['nombre']}' guardada como `{receta_id}`.")

    with col_eliminar:
        if draft["receta_id"] is not None:
            confirmar = st.checkbox("Confirmo que quiero eliminar esta receta")
            if st.button("🗑️ Eliminar receta", disabled=not confirmar):
                db().recetas.delete_one({"receta_id": draft["receta_id"]})
                invalidar_cache_recetas()
                st.session_state["_seleccionar_tras_guardar"] = NUEVA_RECETA
                st.session_state["_editor_actual"] = NUEVA_RECETA
                st.session_state["_flash"] = "Receta eliminada."
                st.rerun()


render()
