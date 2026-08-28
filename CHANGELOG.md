# Changelog

Todos los cambios notables de este proyecto se documentan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto usa
[Versionado Semántico](https://semver.org/lang/es/) (`MAJOR.MINOR.PATCH`). Mientras estemos en
`0.x.x` los cambios que rompen compatibilidad se documentan igual pero no requieren un salto a
`1.0.0` — ese salto está reservado para cuando la Fase 5 (pulido, ver `BUILD-PLAN.md`) esté hecha
y el flujo se haya usado en la vida real sin sorpresas.

Convención de commits desde esta entrada en adelante: `feat:`, `fix:`, `docs:`, `refactor:`,
`test:`, `chore:` como prefijo del mensaje. Los commits previos a esta convención (ver `git log`)
no se reescriben.

Ver también `BUGS.md` para el detalle de bugs/caveats/features (este archivo solo referencia el ID
y un resumen de una línea).

## [Unreleased]

### Added
- (nada pendiente por ahora — próximo trabajo entra aquí)

## [0.4.1] - 2026-08-27

### Added
- Identidad visual "Barro": paleta y tipografía propias (`.streamlit/config.toml` +
  `nutriguia/estilo.py`), inspiradas en una referencia de diseño del usuario y aprobadas primero
  como maqueta interactiva antes de tocar código real. Los 7 colores de grupo SMAE no cambiaron.
  Ver `UI-BUILD-YOUR-MENU.md` → "Identidad visual Barro y responsividad".

### Changed
- `chip_html()` ahora es una pastilla con contraste de texto automático (antes: rectángulo con
  texto blanco fijo, ilegible sobre colores claros como Fruta).
- Filas de ingrediente en "Build your menu" y en el Editor de recetas reestructuradas de 4-7
  columnas en una sola fila a 2 filas más cortas y agrupadas — mismo aspecto en escritorio, mejor
  comportamiento al apilarse en pantallas de teléfono (Streamlit apila `st.columns` bajo ~640px).

## [0.4.0] - 2026-08-27

### Added
- Día completo en "Build your menu" — los 5 tiempos (al despertar, desayuno, colación, comida,
  cena) vía `st.tabs`, con presupuesto restante calculado contra el objetivo diario.
- Guardado de planes por `(persona, fecha)` en `menus_construidos`, con upsert (una persona no
  puede tener dos planes para la misma fecha).
- Historial de planes guardados por persona, con reapertura de cualquier plan anterior
  (round-trip verificado: reabrir reconstruye exactamente lo guardado, ingrediente por
  ingrediente).

### Changed
- `schema.md` → `menus_construidos` reescrito para reflejar la forma real implementada
  (`fecha` obligatoria, snapshots `objetivo_diario`/`actual_diario`/`delta_diario`,
  `RecetaInstancia` como snapshot completo de ingredientes en vez de deltas).

## [0.3.6] - 2026-08-27

### Added
- Página "Personas" (crear persona nueva + editar objetivo diario de una existente), upsert de
  `personas`/`objetivos`.

## [0.3.5] - 2026-08-24 a 2026-08-25

### Added
- Editor de recetas (`views/editor_recetas.py`): crear/editar/eliminar recetas, bloquear
  ingredientes como no ajustables (`Ingrediente.bloqueado`), marcar ingredientes opcionales
  (`Ingrediente.opcional`) para fusionar variantes casi idénticas sin perder datos.
- Convención de colores por grupo SMAE (`nutriguia/colores.py`), reutilizada en toda la app.
- App multipágina vía `st.navigation`/`st.Page` (barra lateral).
- Auto-llenado de grupo y cantidad al elegir un alimento ya catalogado; cantidad se vuelve
  derivada (no editable) para alimentos catalogados al ajustar equivalentes.

### Fixed
- Ver `BUGS.md` — **BUG-001** (crash con ingredientes libres), **BUG-002** (pérdida de datos del
  campo `cantidad`), **BUG-003** (botón "Eliminar" no aparecía tras crear receta), **BUG-004**
  (grupo no se auto-llenaba por `session_state` obsoleto).

### Changed
- Deduplicación del banco de recetas en dos pasadas: 159→97 por nombre exacto, luego 97→86 por
  nombres parecidos (ver `CLAUDE.md` regla 9 y `scripts/migraciones/`, ambos fuera de git por
  contener datos reales).

## [0.2.0] - 2026-08-24

### Added
- `nutriguia/validation.py` — aritmética de equivalentes SMAE (contrato en `VALIDATION.md`).
- `tests/test_validation.py` — 34/34 menús históricos validados en verde.
- `app.py` — MVP Streamlit de un solo tiempo (Fase 3), presupuesto diario restante.

## [0.1.0] - 2026-08-24

### Added
- Estructura inicial del proyecto, documentos de diseño (`ARCHITECTURE.md`, `SETUP.md`,
  `schema.md`, `VALIDATION.md`, `UI-BUILD-YOUR-MENU.md`, `BUILD-PLAN.md`).
- MongoDB + `nutriguia/import_data.py` (Fase 0-1): catálogo de alimentos, recetas, menús
  históricos, personas y objetivos importados.

## Seguridad / privacidad

**2026-08-27** — el repo se hizo público. Se reescribió toda la historia de git
(`git filter-repo`) para purgar datos reales de nutrición/personas de commits previos, se
blindó `.gitignore` contra reintroducirlos, y se removieron nombres reales de la documentación
(reemplazados por "Persona A"/"Persona B"). No es una versión de producto — no lleva número de
versión propio, pero se documenta aquí porque afecta a cualquiera que haya clonado el repo antes
de esa fecha (ese clon tiene el historial viejo con datos reales y debe descartarse).
