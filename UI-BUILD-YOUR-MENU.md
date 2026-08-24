# UI — "Build your menu" (Streamlit)

Especificación de interacción de `app.py`. Confirmado con el usuario: **picker +/- en enteros de
equivalente, nunca slider libre**, y la UI debe mostrar en vivo si falta o sobra algún equivalente.

## Flujo principal

1. **Selector de persona**: Dan | Pau (dropdown arriba de todo, cambia el objetivo aplicable).
2. **Selector de tiempo**: al_despertar | desayuno | colación | comida | cena (tabs de Streamlit,
   `st.tabs`, uno por tiempo — así se ve el día completo sin perder contexto).
3. Dentro de cada tab de tiempo:
   a. Mostrar el **presupuesto diario restante** para la persona seleccionada (objetivo diario de
      `objetivos`, ver `schema.md`, menos lo ya guardado en otros tiempos de ese mismo día) como
      una fila de referencia fija arriba — no un objetivo fijo de este tiempo en particular. El
      reparto entre comidas es libre: no importa si la persona come todo en un solo tiempo o en
      seis, solo el total del día (decisión confirmada con el usuario, 2026-08-24).
   b. **Picker de receta**: `st.selectbox` filtrado por `tiempo_tipico` que incluya este tiempo Y
      (`personas_vistas` incluya la persona seleccionada, con opción de "ver todas" — un platillo
      probado para Dan puede servir de punto de partida para Pau). Mostrar nombre + su
      `vector_equivalentes` como preview antes de agregar.
   c. Botón "Agregar al tiempo" — permite agregar más de una receta al mismo tiempo (los tiempos
      históricos casi siempre tienen 2 platillos).
   d. Por cada receta agregada, listar sus ingredientes. Para cada ingrediente **ajustable**
      (`paso_equivalente()` no da `None`): un control +/- (`st.button("-")` / `st.button("+")` a
      los lados de un número, NO `st.slider`) que sube/baja de 1 en 1 equivalente. Mostrar junto
      la cantidad real resultante (ej. "150 g (5 equivalentes)") recalculada con
      `cantidad_por_equivalente` del catálogo. Ingredientes no ajustables (placeholders, items
      compuestos) se muestran fijos con un botón "quitar".
   e. **Panel de estado en vivo**, uno por grupo SMAE presente en el presupuesto diario restante o
      en lo seleccionado en este tiempo: barra o chip con presupuesto restante / actual de este
      tiempo / delta. Color:
      - verde = `estado_por_grupo` da "exacto"
      - amarillo = "falta" (delta > 0)
      - rojo = "excedido" (delta < 0)
      Recalcular en cada interacción (Streamlit lo hace solo al re-ejecutar el script — no
      necesita JS ni websockets).
   f. Botón "Guardar tiempo" — SIEMPRE habilitado (el usuario puede querer guardar en progreso),
      pero si no todo está en verde mostrar una advertencia inline ("2 equivalentes de Cereal sin
      cubrir") antes de confirmar, no bloquear silenciosamente.
4. **Resumen del día** (fuera de los tabs, siempre visible — `st.sidebar` o sección fija arriba):
   objetivo diario vs. suma de los tiempos guardados, mismo esquema de color.
5. Botón "Guardar menú del día" — persiste el documento completo en `menus_construidos` (ver
   `schema.md`).

## Qué NO hacer

- No usar `st.slider` para ajustar porciones — el usuario pidió explícitamente pasos +/- de
  equivalente entero, no un rango continuo.
- No bloquear el guardado por una validación incompleta — advertir, no impedir (el usuario puede
  estar armando el menú en varias sesiones).
- No recalcular la aritmética de equivalentes dentro de `app.py` — todo pasa por
  `nutriguia/validation.py` (ver `VALIDATION.md`).
- No dejar que el stepper de un ingrediente baje a 0 o negativo — el mínimo es 1 equivalente (si
  el usuario quiere 0, usa "quitar" en vez de bajar el stepper a cero).

## Wireframe en texto (una pestaña de tiempo, ej. "Comida")

```
┌─ Presupuesto restante del día (Dan) ──────────────────┐
│ Verdura 2   Cereal 2   AOA 4   Aceite s/p 1           │
└────────────────────────────────────────────────────────┘

  [ Selecciona una receta ▾ ]  [ + Agregar ]

┌─ Ceviche de atún (v2) ───────────────────────── [quitar] ┐
│  Atún en agua       1 lata           AOA  3   (fijo)     │
│  Queso panela   [-]  40 g (1)  [+]   AOA  1               │
│  Galleta Salma  [-]  3 pz (1)  [+]   Cereal 1              │
│  Pico de gallo  [-]  1/2 tza(1)[+]   Verdura 1              │
└────────────────────────────────────────────────────────────┘

┌─ Estado del tiempo ──────────────────────────────────┐
│ Verdura   objetivo 2  actual 1   🟡 falta 1            │
│ Cereal    objetivo 2  actual 1   🟡 falta 1            │
│ AOA       objetivo 4  actual 4   🟢 exacto              │
│ Aceite s/p objetivo 1 actual 0   🟡 falta 1              │
└────────────────────────────────────────────────────────┘

  [ Guardar tiempo (incompleto) ]
```

## Notas de implementación Streamlit

- Guardar el estado del menú en construcción en `st.session_state` (por persona+tiempo), no en
  Mongo hasta que el usuario presione "Guardar" — evita escribir en cada click.
- `st.rerun()` no es necesario para los steppers — Streamlit re-ejecuta el script completo en cada
  interacción de widget por diseño; usar `st.session_state` para que los valores no se reseteen.
- Para los +/- de cada ingrediente, usar una key única por ingrediente (`f"{receta_instancia_id}_{alimento}"`)
  para que Streamlit no confunda steppers de dos recetas distintas agregadas al mismo tiempo.
