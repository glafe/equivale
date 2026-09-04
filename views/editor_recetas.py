"""EquiVale Chef — editor de recetas (Fase 3.5).

Ver UI-BUILD-YOUR-MENU.md -> "Editor de recetas" para la especificación completa.
"""

import re
import uuid

import streamlit as st

from nutriguia import db as bd
from nutriguia.cantidades import escalar_cantidad
from nutriguia.colores import GRUPO_ETIQUETA, chip_html
from nutriguia.streamlit_data import (
    cargar_nombres_alimentos,
    cargar_personas,
    cargar_recetas,
    db,
    invalidar_cache_recetas,
)
from nutriguia.validation import paso_equivalente, sumar_por_grupo

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
        "opcional": False,
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
            "opcional": ing.get("opcional", False),
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
    st.caption("Crea, corrige o elimina recetas del banco. Los cambios se guardan al instante.")

    recetas = cargar_recetas()
    personas = cargar_personas()
    alimentos_catalogo = cargar_nombres_alimentos()
    catalogo_por_nombre = {d["alimento"]: d for d in bd.listar_catalogo(db())}

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
        with st.container(border=True, key=f"ingrediente_card_{fila['fila_id']}"):
            # Dos filas en vez de una sola de 7 columnas: en un teléfono cada `st.columns(...)`
            # se apila completo, así que 7 columnas serían 7 bloques sueltos uno debajo del
            # otro -- agrupar "qué alimento" en su propia fila y "cómo se mide" en la siguiente
            # se lee mejor apilado (y no cambia nada en escritorio, sigue viéndose en línea).
            c1, c5 = st.columns([5, 1])
            c2, c_cant, c3, c4, c_opc = st.columns([2, 2, 1, 1, 1])

            alimento_anterior = fila["alimento"]
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
                cambio_de_alimento = sel != alimento_anterior
                fila["alimento"] = sel
                if sel in catalogo_por_nombre:
                    entrada = catalogo_por_nombre[sel]
                    fila["grupo_smae"] = entrada["grupo"]
                    if cambio_de_alimento:
                        # Alimento recién elegido -> resetear a 1 equivalente en vez de dejar lo
                        # que hubiera quedado del alimento anterior en esta fila (evita
                        # inconsistencias tipo "Pollo, 5 equivalentes" recién puesto). La cantidad
                        # se deriva más abajo de equivalentes × cantidad_por_equivalente, no hace
                        # falta fijarla aquí. El selectbox de Grupo y el number_input de
                        # equivalentes ya tienen su propio key desde que la fila se creó -> hay que
                        # empujar el nuevo valor a session_state también, porque Streamlit ignora
                        # el `index`/`value` de un widget con key una vez que ya tiene una entrada
                        # guardada.
                        fila["equivalentes"] = 1
                        st.session_state[f"grupo_{fila['fila_id']}"] = entrada["grupo"]
                        st.session_state[f"equiv_{fila['fila_id']}"] = 1

            grupo_actual = fila["grupo_smae"] if fila["grupo_smae"] in GRUPOS_CANONICOS else LIBRE
            grupo_sel = c2.selectbox(
                "Grupo",
                options=opciones_grupo,
                index=opciones_grupo.index(grupo_actual),
                key=f"grupo_{fila['fila_id']}",
                label_visibility="collapsed",
            )
            fila["grupo_smae"] = None if grupo_sel == LIBRE else grupo_sel

            # Un ingrediente "libre" (grupo_smae None, ej. "Canela", "Salsa casera al gusto")
            # legítimamente no cuenta ningún equivalente -> 0. sumar_por_grupo() los ignora de
            # todas formas (ver VALIDATION.md), así que min_value=1 aquí solo aplicaba a
            # ingredientes con grupo real; forzarlo siempre tronaba el editor en cuanto cargaba
            # una receta con un ingrediente libre ya guardado en equivalentes=0.
            min_equivalentes = 0 if fila["grupo_smae"] is None else 1
            equiv_key = f"equiv_{fila['fila_id']}"
            # Si el usuario acaba de cambiar el Grupo de "libre" a uno real en esta misma sesión,
            # el valor ya guardado en session_state para este widget puede seguir en 0 -> subirlo
            # ANTES de instanciar el widget (después de instanciarlo ya no se puede tocar).
            if equiv_key in st.session_state and st.session_state[equiv_key] < min_equivalentes:
                st.session_state[equiv_key] = min_equivalentes
            # equivalentes se renderiza antes que cantidad porque, para alimentos del catálogo,
            # cantidad se DERIVA de equivalentes (ver abajo) -- necesitamos el valor ya resuelto.
            fila["equivalentes"] = c3.number_input(
                "Equiv.", min_value=min_equivalentes, step=1,
                value=max(fila["equivalentes"], min_equivalentes),
                key=equiv_key, label_visibility="collapsed",
            )

            paso = paso_equivalente(fila["alimento"], catalogo_por_nombre)
            if paso is not None:
                # Alimento reconocido en el catálogo -> cantidad se calcula sola
                # (equivalentes × cantidad_por_equivalente), no editable a mano, para que nunca
                # queden desincronizadas (ej. "3 equivalentes" con "30 g" de cuando eran 1).
                fila["cantidad"] = escalar_cantidad(paso, fila["equivalentes"])
                c_cant.text_input(
                    "Cantidad",
                    value=fila["cantidad"],
                    disabled=True,
                    # key incluye equivalentes a propósito: al cambiar equivalentes esto es un
                    # widget "nuevo" para Streamlit, así que el `value` recién calculado sí se ve
                    # -- si el key fuera fijo, Streamlit ignoraría el `value` en reruns siguientes.
                    key=f"cantidad_ro_{fila['fila_id']}_{fila['equivalentes']}",
                    label_visibility="collapsed",
                )
            else:
                # Alimento libre o no catalogado -> cantidad es texto libre, como siempre.
                fila["cantidad"] = c_cant.text_input(
                    "Cantidad",
                    value=fila["cantidad"],
                    key=f"cantidad_{fila['fila_id']}",
                    label_visibility="collapsed",
                    placeholder="ej. 1/2 taza, 150 g",
                )
            fila["bloqueado"] = c4.checkbox(
                "🔒", value=fila["bloqueado"], key=f"bloqueado_{fila['fila_id']}",
                help="Bloquear: no ajustable con +/- en Menú del día",
            )
            fila["opcional"] = c_opc.checkbox(
                "Opc.", value=fila["opcional"], key=f"opcional_{fila['fila_id']}",
                help="Opcional: en Menú del día se puede incluir o excluir con un checkbox, "
                     "sin necesidad de quitarlo de la receta ni crear una receta aparte.",
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
                        **({"opcional": True} if i["opcional"] else {}),
                    }
                    for i in ingredientes_validos
                ],
                "veces_visto": draft["veces_visto"],
                "origen": draft["origen"],
            }
            bd.guardar_receta(db(), documento)
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
                bd.eliminar_receta(db(), draft["receta_id"])
                invalidar_cache_recetas()
                st.session_state["_seleccionar_tras_guardar"] = NUEVA_RECETA
                st.session_state["_editor_actual"] = NUEVA_RECETA
                st.session_state["_flash"] = "Receta eliminada."
                st.rerun()


render()
