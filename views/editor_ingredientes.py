"""EquiVale Chef -- editor de ingredientes (catálogo de alimentos): tabla de todo el catálogo
con edición/eliminación, y "Agregar de SMAE" para sumar alimentos nuevos desde la tabla oficial
SMAE (SMAE_CONSULTA.csv).

Ver UI-BUILD-YOUR-MENU.md -> "Editor de ingredientes" para la especificación completa.
"""

import streamlit as st

from nutriguia.colores import GRUPO_ETIQUETA
from nutriguia.streamlit_data import (
    cargar_catalogo,
    cargar_filas_smae,
    cargar_recetas,
    db,
    invalidar_cache_catalogo,
    invalidar_cache_recetas,
)
from nutriguia.texto import normalizar_busqueda

GRUPOS_CANONICOS = ["AOA", "Cereal", "Verdura", "Fruta", "Aceite s/p", "Aceite c/p", "Leguminosa"]
LIBRE = "(libre, sin grupo)"
TODOS = "Todos"
SIN_SELECCION = "— Elige un alimento —"


def _etiqueta_grupo(grupo: str | None) -> str:
    return LIBRE if grupo is None else GRUPO_ETIQUETA.get(grupo, grupo)


def _conteo_uso_en_recetas() -> dict[str, int]:
    """Cuántas recetas DISTINTAS usan cada alimento -- para saber el impacto de renombrar o
    eliminar antes de hacerlo, no cuántas veces aparece en total."""
    conteo: dict[str, int] = {}
    for receta in cargar_recetas():
        vistos = {ing["alimento"] for ing in receta["ingredientes"]}
        for alimento in vistos:
            conteo[alimento] = conteo.get(alimento, 0) + 1
    return conteo


def _renombrar_en_recetas(nombre_viejo: str, nombre_nuevo: str) -> int:
    """Actualiza `ingredientes[].alimento` en todas las recetas que usaban `nombre_viejo`.
    Devuelve cuántas recetas se tocaron. Necesario porque las recetas referencian un alimento por
    nombre, no por id -- sin esto, renombrar en el catálogo dejaría esas recetas apuntando a un
    nombre que ya no existe (el ingrediente se volvería "no ajustable" silenciosamente)."""
    tocadas = 0
    for receta in db().recetas.find({"ingredientes.alimento": nombre_viejo}):
        ingredientes = receta["ingredientes"]
        cambio = False
        for ing in ingredientes:
            if ing["alimento"] == nombre_viejo:
                ing["alimento"] = nombre_nuevo
                cambio = True
        if cambio:
            db().recetas.update_one(
                {"receta_id": receta["receta_id"]}, {"$set": {"ingredientes": ingredientes}}
            )
            tocadas += 1
    if tocadas:
        invalidar_cache_recetas()
    return tocadas


def render() -> None:
    st.title("🥕 Editor de ingredientes")
    st.caption(
        "Catálogo de alimentos: cada uno define cuánto vale 1 equivalente. Edita o elimina los "
        "que estén mal antes de seguir agregando nuevos."
    )

    if "_flash_ingredientes" in st.session_state:
        st.success(st.session_state.pop("_flash_ingredientes"))
    # El selector de abajo puede quedar apuntando a un nombre que ya no existe tras guardar/
    # eliminar/fusionar (el alimento cambió de nombre o desapareció) -- reseteando ANTES de
    # instanciar el selectbox se evita que Streamlit reciba un valor fuera de `options`.
    if "_pendiente_ing_editar_selector" in st.session_state:
        st.session_state["ing_editar_selector"] = st.session_state.pop("_pendiente_ing_editar_selector")

    catalogo = cargar_catalogo()
    conteo_uso = _conteo_uso_en_recetas()

    st.subheader(f"Catálogo actual ({len(catalogo)})")
    c_buscar, c_grupo = st.columns([2, 1])
    busqueda = c_buscar.text_input("Buscar por nombre", placeholder="ej. pollo", key="ing_busqueda")
    grupo_filtro = c_grupo.selectbox("Grupo", [TODOS] + GRUPOS_CANONICOS + [LIBRE], key="ing_grupo_filtro")

    busqueda_norm = normalizar_busqueda(busqueda)
    nombres_filtrados = []
    filas_tabla = []
    for alimento, datos in sorted(catalogo.items()):
        if busqueda_norm and busqueda_norm not in normalizar_busqueda(alimento):
            continue
        grupo = datos.get("grupo")
        if grupo_filtro == LIBRE and grupo is not None:
            continue
        if grupo_filtro not in (TODOS, LIBRE) and grupo != grupo_filtro:
            continue
        nombres_filtrados.append(alimento)
        filas_tabla.append(
            {
                "Alimento": alimento,
                "Grupo": _etiqueta_grupo(grupo),
                "Cantidad por equivalente": datos.get("cantidad_por_equivalente", ""),
                "Asunción": "Sí" if datos.get("asuncion") else "",
                "Usado en recetas": conteo_uso.get(alimento, 0),
            }
        )

    st.dataframe(filas_tabla, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Editar o eliminar un alimento")
    elegido = st.selectbox(
        "Alimento", [SIN_SELECCION] + nombres_filtrados, key="ing_editar_selector"
    )

    if elegido != SIN_SELECCION:
        datos = catalogo[elegido]
        usos = conteo_uso.get(elegido, 0)
        if usos:
            st.caption(f"Usado en {usos} receta(s) -- ver notas abajo antes de renombrar/eliminar.")

        # Widgets sueltos, no un st.form: un st.form solo reenvía sus valores al hacer submit, así
        # que un checkbox "confirmar" adentro de un form no puede des-habilitar su propio botón de
        # submit en la misma interacción (el botón queda deshabilitado sin forma de re-renderizar
        # antes de hacer click). Mismo patrón ya usado en editor_recetas.py para eliminar receta.
        nuevo_nombre = st.text_input("Nombre", value=elegido, key=f"nombre_{elegido}")
        opciones_grupo = GRUPOS_CANONICOS + [LIBRE]
        grupo_actual = datos.get("grupo")
        grupo_sel = st.selectbox(
            "Grupo",
            opciones_grupo,
            index=opciones_grupo.index(grupo_actual) if grupo_actual in opciones_grupo else len(opciones_grupo) - 1,
            key=f"grupo_editar_{elegido}",
        )
        nueva_cantidad = st.text_input(
            "Cantidad por equivalente",
            value=datos.get("cantidad_por_equivalente", ""),
            key=f"cantidad_editar_{elegido}",
        )
        c_guardar, c_eliminar = st.columns(2)
        guardar = c_guardar.button("💾 Guardar cambios", type="primary", key=f"guardar_{elegido}")
        confirmar_eliminar = c_eliminar.checkbox("Confirmo eliminar", key=f"confirmar_{elegido}")
        eliminar = c_eliminar.button(
            "🗑️ Eliminar", disabled=not confirmar_eliminar, key=f"eliminar_{elegido}"
        )

        if guardar:
            nombre_final = nuevo_nombre.strip()
            grupo_final = None if grupo_sel == LIBRE else grupo_sel
            if not nombre_final:
                st.error("El nombre no puede quedar vacío.")
            elif nombre_final != elegido and nombre_final in catalogo:
                # El nuevo nombre ya existe en el catálogo -> tratar como fusión de duplicados
                # (ver CLAUDE.md regla 9 / BUGS.md KC-001): se mantiene el registro que YA tenía
                # ese nombre tal cual, se elimina el viejo, y las recetas que usaban el nombre
                # viejo pasan a usar el nombre que sobrevive -- así no quedan dos entradas del
                # mismo alimento real con distinta ortografía.
                db().catalogo_alimentos.delete_one({"alimento": elegido})
                tocadas = _renombrar_en_recetas(elegido, nombre_final)
                invalidar_cache_catalogo()
                st.session_state["_flash_ingredientes"] = (
                    f"'{elegido}' se fusionó con '{nombre_final}' (ya existía) -- "
                    f"{tocadas} receta(s) actualizada(s)."
                )
                st.session_state["_pendiente_ing_editar_selector"] = SIN_SELECCION
                st.rerun()
            else:
                db().catalogo_alimentos.update_one(
                    {"alimento": elegido},
                    {
                        "$set": {
                            "alimento": nombre_final,
                            "grupo": grupo_final,
                            "cantidad_por_equivalente": nueva_cantidad.strip(),
                        }
                    },
                )
                tocadas = 0
                if nombre_final != elegido:
                    tocadas = _renombrar_en_recetas(elegido, nombre_final)
                invalidar_cache_catalogo()
                mensaje = f"'{elegido}' actualizado."
                if tocadas:
                    mensaje += f" Se renombró en {tocadas} receta(s) que lo usaban."
                st.session_state["_flash_ingredientes"] = mensaje
                st.session_state["_pendiente_ing_editar_selector"] = SIN_SELECCION
                st.rerun()

        if eliminar:
            db().catalogo_alimentos.delete_one({"alimento": elegido})
            invalidar_cache_catalogo()
            st.session_state["_pendiente_ing_editar_selector"] = SIN_SELECCION
            st.session_state["_flash_ingredientes"] = (
                f"'{elegido}' eliminado del catálogo."
                + (f" Seguía usado en {usos} receta(s) -- esos ingredientes ahora son "
                   "'no ajustable' en vez de tener stepper, pero no se borraron de la receta."
                   if usos else "")
            )
            st.rerun()

    st.divider()
    with st.expander("➕ Agregar de SMAE"):
        st.caption(
            "Busca en la tabla oficial SMAE y agrega un alimento nuevo al catálogo. Si el mismo "
            "alimento aparece con más de una preparación/unidad (ej. crudo vs cocido), cada una "
            "sale como una opción separada -- elige la que corresponda."
        )
        busqueda_smae = st.text_input("Buscar en SMAE", placeholder="ej. atun", key="smae_busqueda")
        busqueda_smae_norm = normalizar_busqueda(busqueda_smae)
        if busqueda_smae_norm:
            filas_smae = cargar_filas_smae()
            coincidencias = [
                f for f in filas_smae if busqueda_smae_norm in normalizar_busqueda(f["alimento"])
            ][:40]
            if not coincidencias:
                st.caption("Sin resultados (o la categoría SMAE de ese alimento no está soportada -- ver nota abajo).")
            else:
                opciones = {
                    f"{f['alimento']} — {f['cantidad_por_equivalente']} ({_etiqueta_grupo(f['grupo_smae'])})": f
                    for f in coincidencias
                }
                etiqueta_elegida = st.selectbox("Resultados", list(opciones.keys()))
                fila = opciones[etiqueta_elegida]
                ya_existe = fila["alimento"] in catalogo
                if ya_existe:
                    st.warning(
                        f"'{fila['alimento']}' ya está en el catálogo -- edítalo arriba en vez de "
                        "duplicarlo."
                    )
                elif st.button("+ Agregar al catálogo", type="primary"):
                    db().catalogo_alimentos.insert_one(
                        {
                            "alimento": fila["alimento"],
                            "grupo": fila["grupo_smae"],
                            "cantidad_por_equivalente": fila["cantidad_por_equivalente"],
                        }
                    )
                    invalidar_cache_catalogo()
                    st.session_state["_flash_ingredientes"] = f"'{fila['alimento']}' agregado desde SMAE."
                    st.rerun()
        st.caption(
            "Azúcares, leche y bebidas alcohólicas de la tabla SMAE no aparecen aquí -- esos "
            "grupos no tienen equivalente entre los 7 canónicos de este proyecto (ver CLAUDE.md)."
        )


render()
