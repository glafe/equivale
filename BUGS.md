# BUGS — bugs, caveats y feature requests

Registro vivo del *por qué* y *cómo* de cada problema/idea. `CHANGELOG.md` es la versión corta
para quien solo quiere saber *qué* cambió y *cuándo*; este archivo tiene el detalle. Al cerrar un
bug o enviar un feature, `CHANGELOG.md` recibe una línea con el ID de acá.

IDs son secuenciales y nunca se reutilizan dentro de cada serie.

## Contents

### Bugs
- Resueltos: [BUG-001](#bug-001--status-rv), [BUG-002](#bug-002--status-rv),
  [BUG-003](#bug-003--status-rv), [BUG-004](#bug-004--status-rv)

### Known Caveats
- Abiertos: [KC-001](#kc-001), [KC-002](#kc-002)

### Feature Requests
- Propuestos: [FR-001](#fr-001), [FR-002](#fr-002), [FR-003](#fr-003)

## Severity guide

`Critical` (crash/pérdida de datos/falla total) · `High` (rotura mayor, sin workaround) ·
`Medium` (degradado, hay workaround) · `Low` (cosmético/menor/caso raro) · `Enh` (mejora menor).

## Status definitions

- Bugs: `O` Open · `IP` In Progress · `R` Resolved · `RV` Resolved & Verified · `C` Closed
- Caveats: `Active` · `Historical` · `Resolved <fecha>`
- Feature Requests: `Proposed` · `Planned` · `In Progress` · `Shipped` · `Declined`

---

## Bugs

### Detailed Entries

#### BUG-004 · [STATUS: RV]
**Title:** El grupo SMAE no se auto-llenaba al elegir un alimento del catálogo en el editor
**Severity:** Medium
**Reported Date:** 2026-08-25
**Release Fixed:** 0.3.5

##### Observable Problem
Al elegir un alimento ya catalogado en el editor de recetas, la variable interna sí se
actualizaba pero el `selectbox` de Grupo en pantalla seguía mostrando el valor anterior (o vacío).

##### Fix Details (Technical)
`st.selectbox` ignora un `value`/`index` nuevo si su `key` ya tiene una entrada en
`st.session_state` de un render anterior. Fix: escribir explícitamente
`st.session_state[f"grupo_{fila_id}"]` con el grupo del catálogo *antes* de que ese widget se
vuelva a instanciar en el mismo run. Ver `views/editor_recetas.py`.

#### BUG-003 · [STATUS: RV]
**Title:** Botón "Eliminar" no aparecía inmediatamente tras crear una receta nueva
**Severity:** Low
**Reported Date:** 2026-08-24
**Release Fixed:** 0.3.5

##### Observable Problem
Después de guardar una receta recién creada, el botón "Eliminar" (que solo debe verse para
recetas ya existentes) no aparecía hasta refrescar manualmente.

##### Fix Details (Technical)
`receta_id` se asignaba después del `st.rerun()` en vez de antes, así que el rerun repintaba con
el `receta_id` viejo (vacío). Fix: mover la asignación antes del `rerun()`.

#### BUG-002 · [STATUS: RV]
**Title:** El campo `cantidad` de un ingrediente se podía perder al editar una receta
**Severity:** High
**Reported Date:** 2026-08-24
**Release Fixed:** 0.3.5

##### Observable Problem
El editor de recetas no traía un campo para `cantidad` en el formulario de ingredientes; al
guardar una receta editada, ese campo se sobreescribía con `""`, borrando el dato real de
`cantidad_por_equivalente` histórico (afectó a `alambre-de-pollo-v2`: "150 g"/"½ tz" perdidos).

##### Fix Details (Technical)
Se agregó el campo `cantidad` al formulario de ingredientes en `views/editor_recetas.py`. El
documento corrupto en Mongo se restauró manualmente con los valores originales.

##### Prevention
Este es el caso concreto que motivó **BUG-002 (Enh) → auto-llenado de cantidad desde el
catálogo** (ver 5d7399e / 1aa2f83): si el alimento está catalogado, `cantidad` ahora se deriva de
`equivalentes` y deja de ser editable a mano, eliminando esta clase de error.

#### BUG-001 · [STATUS: RV]
**Title:** Crash del editor con ingredientes "libres" (`grupo_smae: null`, `equivalentes: 0`)
**Severity:** Critical
**Reported Date:** 2026-08-25
**Release Fixed:** 0.3.5

##### Observable Problem
Abrir cualquier receta con un ingrediente libre (ej. Canela, Salsa casera, Gelatina — 18 recetas
afectadas) tiraba `StreamlitValueBelowMinError` en el editor.

##### Steps to Reproduce
1. Abrir el editor de recetas.
2. Elegir una receta con un ingrediente sin grupo SMAE (ej. "Tinga de Pollo").
3. Esperado: el ingrediente se muestra con equivalentes=0. Actual: excepción, página rota.

##### Fix Explanation (Exec Level — No Code)
El stepper de equivalentes tenía un mínimo de 1 fijo para todos los ingredientes, pero los
ingredientes "libres" (sin grupo, cantidad al gusto) legítimamente valen 0 equivalentes.

##### Fix Details (Technical)
`number_input(min_value=1, ...)` aplicado incondicionalmente → cambiado a
`min_value = 0 if grupo_smae is None else 1`, más un clamp defensivo del `session_state` si el
usuario reasigna un grupo real a un ingrediente que era libre. Diagnosticado leyendo el
traceback embebido en un HAR de red (`Hars/192.168.68.59.har`, fuera de git) sin acceso directo a
logs del servidor.

---

## Known Caveats

### Detailed Entries

#### KC-002
**Title:** Kernels Linux 6.19–7.0.13 crashean MongoDB 8.0.x (bug de TCMalloc/rseq)
**Date Identified:** 2026-08-24
**Status:** Active (mientras el servidor corra un kernel en ese rango)

##### Exec Description
MongoDB no arrancaba en el servidor de producción hasta aplicar un workaround de compatibilidad
de kernel — no es un bug de este proyecto.

##### Eng Description
Bug conocido de glibc/TCMalloc con la syscall `rseq` en esa ventana de versiones de kernel.
Workaround: override de systemd con `Environment=GLIBC_TUNABLES=glibc.pthread.rseq=1` (ver
`SETUP.md`). No requiere cambios de código, solo de configuración del servicio.

##### Alternative Solutions
1. **Elegido** — override de systemd (`GLIBC_TUNABLES`), no invasivo, documentado en `SETUP.md`.
2. Downgrade de kernel — descartado, complica actualizaciones de seguridad del SO.
3. Downgrade de MongoDB — descartado, no atacaba la causa raíz.

#### KC-001
**Title:** Ingredientes con el mismo alimento real pero ortografía distinta quedan como
opcionales separados tras la fusión mecánica de recetas
**Date Identified:** 2026-08-25
**Status:** Active

##### Exec Description
Al fusionar recetas duplicadas por nombre exacto, si el mismo alimento aparecía escrito distinto
entre variantes (ej. "Atún" vs "Atún en agua", "Proteína" vs "Proteína en polvo"), el script de
fusión no los reconoció como el mismo ingrediente y quedaron como dos ingredientes opcionales
separados en la receta fusionada, en vez de uno solo.

##### Eng Description
`scripts/migraciones/2026-08-25-fusionar-recetas-por-nombre.py` compara nombres de ingrediente de
forma exacta (normalizado solo en mayúsculas/espacios) para decidir "está en todas las variantes"
vs. "solo en algunas" → opcional. No hay matching difuso. La pasada del 2026-08-25 (nombres
parecidos) corrigió ~16 casos detectados a mano, pero no se persiguió exhaustivamente en el resto
del banco (86 recetas).

##### Alternative Solutions
1. **Elegido (por ahora)** — corregir a mano desde el Editor de recetas si se nota al usar la
   app; bajo impacto (duplica un ingrediente opcional, no rompe la aritmética de equivalentes).
2. Matching difuso de nombres en el script de fusión — no implementado, riesgo de falsos
   positivos (fusionar alimentos que en realidad son distintos) mayor que el beneficio para un
   banco de 86 recetas.

---

## Feature Requests

### Detailed Entries

#### FR-003
**Title:** Fase 5 — pulido (semana completa, exportar imprimible, sugerencia automática de hueco)
**Date Requested:** 2026-08-24
**Status:** Proposed — bloqueado a propósito hasta usar la Fase 4 en la vida real unos días

##### Exec Description
Tres mejoras de pulido: repetir el flujo de día completo por semana (con aviso de repetición),
exportar un plan a formato imprimible, y sugerir automáticamente un ingrediente suelto del
catálogo cuando ningún combo del banco de recetas cuadra exacto con un objetivo.

##### Eng Description
Ver `BUILD-PLAN.md` → Fase 5 para el detalle de cada una. No empezar sin haber usado la Fase 4
en la vida real — puede cambiar qué vale la pena pulir primero.

##### Dependencies
Fase 4 (día completo + guardado + historial) — completa desde 2026-08-27.

#### FR-002
**Title:** "EquiVale Chef" — integración con `SMAE_CONSULTA.csv` para agregar alimentos nuevos al
catálogo desde el propio editor
**Date Requested:** 2026-08-24
**Status:** Proposed

##### Exec Description
Cuando un alimento nuevo no está en `catalogo_alimentos`, poder buscarlo en la tabla oficial SMAE
(`SMAE_CONSULTA.csv`) y fijar su equivalencia sin salir del editor de recetas.

##### Eng Description
Si el alimento tampoco está en `SMAE_CONSULTA.csv`, marcar `asuncion: true` y pedir confirmación
del criterio usado — mismo criterio que la regla 5 de `CLAUDE.md`. Ver `BUILD-PLAN.md` → "Ideas
para más adelante" para el detalle completo.

##### Dependencies
Editor de recetas (Fase 3.5) — ya construido, esto es la extensión pendiente.

#### FR-001
**Title:** Historial de versiones del objetivo por persona
**Date Requested:** 2026-08-27
**Status:** Proposed

##### Exec Description
Poder ver qué objetivo diario tenía una persona en una fecha pasada, no solo el vigente.

##### Eng Description
La página "Personas" (Fase 3.6) solo mantiene UN documento `objetivos` vigente por persona
(upsert in-place). El schema ya deja `vigente_desde` listo para esto, pero no se guarda
histórico de valores anteriores al hacer un nuevo upsert. Retomar solo si hace falta consultar
"qué objetivo tenía tal persona en tal fecha".

##### Dependencies
Ninguna — se puede implementar en cualquier momento cambiando el upsert por un insert +
`vigente_desde`/`vigente_hasta`.
