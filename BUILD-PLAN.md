# Plan de construcción — orden de ejecución para Claude Code

Seguir en orden. Cada fase tiene un criterio de "hecho" explícito — no avanzar a la siguiente fase
sin cumplirlo. Si algo en `ARCHITECTURE.md`, `schema.md`, `VALIDATION.md` o
`UI-BUILD-YOUR-MENU.md` no alcanza para decidir algo, preguntarle al usuario en vez de asumir —
son documentos de diseño, no exhaustivos al 100%.

## Fase 0 — Entorno

Seguir `SETUP.md` pasos 0-5 (detectar distro, instalar MongoDB, crear usuario de app, venv,
`.env`). **Hecho cuando**: `mongosh --eval "db.runCommand({ping:1})"` regresa `{ok:1}` y
`pip list` muestra pymongo/streamlit/pytest instalados.

## Fase 1 — Importar datos

Copiar `catalogo-alimentos.json`, `recetas.json` y los 17 archivos de menús históricos a `data/`
(pedírselos al usuario si no llegaron con el repo). Escribir `nutriguia/import_data.py` según
`schema.md`:
- `catalogo_alimentos`: aplanar el JSON anidado por grupo a un documento por alimento.
- `recetas`: importar tal cual desde `recetas.json` (ya vienen con `receta_id` único).
- `menus`: importar tal cual los 17 archivos (son de solo lectura/referencia histórica).
- `personas`: crear 2 documentos simples, `{persona: "Dan", ...}` y `{persona: "Pau", ...}` — usar
  como punto de extensión futuro, no hace falta más que el nombre por ahora.
- `objetivos`: **no hay un archivo fuente para esto** — confirmado con el usuario el 2026-08-24
  para el periodo Agosto-Septiembre 2026:
  - Dan: `equivalentes_diarios_indicados` de `Junio26-Dany.json` — AOA 15, Cereal 10, Verdura 5,
    Fruta 4, Aceite s/p 3, Aceite c/p 1.
  - Pau: no existe `equivalentes_diarios_indicados` en ningún archivo 2026 de Pau (ni siquiera los
    dos `menu_id` de un mismo periodo coinciden entre sí) — por decisión explícita del usuario, se
    usa `equivalentes_diarios` del `menu_id 1` de `PauJunio26.json` — AOA 13, Cereal 6,
    Leguminosa 1, Verdura 5, Aceite c/p 1, Aceite s/p 3, Fruta 3.
  - Ambos con `vigente_desde: "2026-08-24"`. No poblar `por_tiempo` — ver nota de diseño en
    `schema.md` → `objetivos` (el objetivo es diario, no por comida; no importa cómo se reparta
    entre tiempos).

**Hecho cuando**: `import_data.py` corre sin error e imprime conteos por colección (17 menús, 159
recetas, ~80 alimentos en catálogo, 2 personas, 2 objetivos).

## Fase 2 — Módulo de validación + tests de regresión

Implementar `nutriguia/validation.py` exactamente según el contrato de `VALIDATION.md`. Escribir
`tests/test_validation.py` que corra `validar_menu()` sobre los 17×2 = 34 menús importados.
**Hecho cuando**: `pytest tests/ -v` pasa 34/34 en verde. Si alguno falla, el bug está en
`validation.py`, no en los datos — no "corregir" un dato histórico para que pase el test.

## Fase 3 — Streamlit MVP: un solo tiempo

Construir `app.py` cubriendo SOLO el flujo de un tiempo (ej. Comida) para una persona, según
`UI-BUILD-YOUR-MENU.md` puntos 1-3. Sin guardar a Mongo todavía — validar que el picker + steppers
+ panel de estado en vivo funcionan correctamente en memoria (`st.session_state`).
**Hecho cuando**: se puede elegir una receta del banco, ajustar un ingrediente con +/-, y ver el
delta por grupo actualizarse correctamente contra el **presupuesto diario restante** (no contra un
objetivo fijo de ese tiempo — ver nota de diseño en `schema.md` → `objetivos`).

## Fase 4 — Día completo + guardar

Extender a los `st.tabs` de todos los tiempos (punto 2-3 completo de `UI-BUILD-YOUR-MENU.md`),
agregar el resumen del día (punto 4), y el guardado real a `menus_construidos` (punto 5).
**Hecho cuando**: se puede armar un día completo para Dan o Pau, guardarlo, y volver a abrirlo
mostrando lo mismo que se guardó (round-trip correcto).

## Fase 5 — Pulido (solo si el flujo básico ya se siente bien de usar)

- Semana completa (repetir el flujo por día, con aviso si un platillo se repite muy seguido).
- Exportar el menú de un día/semana a un formato imprimible (reusar el `pdf` skill si aplica, o
  simple HTML/print).
- Sugerencia automática: cuando ningún combo del banco cuadra exacto con un objetivo, usar el
  catálogo para armar un ingrediente suelto que complete el faltante (no un platillo nuevo
  completo — solo el hueco).

No empezar la Fase 5 sin haber usado la Fase 4 unos días en la vida real — puede cambiar qué vale
la pena pulir primero.

## Ideas para más adelante (no implementar todavía)

Notas del usuario para no perderlas de vista, pero fuera de alcance de las Fases 0-5 de arriba —
retomar solo después de que la Fase 4 (o 5) esté en uso real y se sienta bien.

- **Objetivos editables por persona, con perfiles** — hoy `objetivos` se siembra una sola vez en
  Fase 1 y solo se actualiza insertando un documento nuevo directamente en Mongo. El usuario quiere
  poder editar el objetivo diario de cada persona (Dan/Pau) desde la propia UI, como parte de un
  perfil por persona — no tener que tocar la base de datos a mano cada vez que cambie el objetivo
  con el nutriólogo. Ver nota de diseño en `schema.md` → `objetivos` (el objetivo ya es solo
  diario, no por tiempo, lo cual simplifica esta futura pantalla de edición).
- **"EquiVale Chef"** — una herramienta (dentro de `app.py` o un modo separado) para construir y
  actualizar `recetas` sin editar JSON a mano:
  - Al armar un platillo, sugerir alimentos primero desde `catalogo_alimentos` (autocompletar por
    nombre, mostrando su `grupo` y `cantidad_por_equivalente`).
  - Si el alimento no está en el catálogo, permitir agregarlo buscándolo en `SMAE_CONSULTA.csv`
    (la tabla oficial SMAE) y preguntar la unidad de medida a usar (ej. "taza", "g", "pieza") para
    fijar su `cantidad_por_equivalente` — mismo criterio que la regla 5 de `CLAUDE.md` (si tampoco
    está en `SMAE_CONSULTA.csv`, marcar `asuncion: true` y pedir confirmación antes de guardar).
  - Esto permite crecer `catalogo_alimentos` y el banco de `recetas` poco a poco, en vez de
    depender solo de lo ya extraído de los menús históricos — útil para cuando el banco no tiene
    ninguna combinación que cuadre con un objetivo (ver "Generar menús nuevos" en `CLAUDE.md`).

## Checklist rápido

- [x] Fase 0 — Mongo corriendo, venv listo
- [x] Fase 1 — datos importados, conteos correctos
- [x] Fase 2 — 34/34 tests de validación en verde
- [x] Fase 3 — MVP de un tiempo funcionando
- [ ] Fase 4 — día completo + guardado funcionando
- [ ] Fase 5 — pulido (solo tras uso real)
